// The Revit link (spec/features/revit_link.md): linking a computer with Revit to a person's account, what Revit asks
// and sends with that link's token, and the project's Fit check page. The rules are in revit_link.ts.
import { json, logged, membership, newId, now, readBody, sha256, text, type Env, type MemberRow, type User } from "./data";
import {
  LINK_MINUTES, LISTEN_SECONDS, MAX_DATA_BYTES, MAX_RUN_BYTES, POLL_SECONDS, TOKEN_PREFIX, bearer, checkData, cleanUserCode,
  commandFresh, commandText, computerName, mayAskRevit, mayChoose, maySeeFitCheck, maySendData, maySendRun, newSecret,
  newUserCode, pngBytes, setsView, summariseRun,
} from "./revit_link";
import { access } from "./project_data";
import { sameText, teamToken, teamUnlocked } from "./team";

const fitKeys = (projectId: string, run?: string) => ({
  data: `projects/${projectId}/fitcheck/data.json`,
  run: `projects/${projectId}/fitcheck/runs/${run}.json`,
  png: `projects/${projectId}/fitcheck/runs/${run}.png`,
});

interface TokenRow { id: string; user_id: string; computer: string; team_hash: string | null }

// ---- Before any session: Revit starts a link and asks whether it was approved ----------------------------------------

export async function revitOpenRoute(
  request: Request, env: Env, path: string, method: string, origin: string, termsAccepted: (userId: string) => Promise<boolean>,
): Promise<Response | null> {
  if (path === "/api/revit/link/start" && method === "POST") return startLink(request, env, origin);
  if (path === "/api/revit/link/poll" && method === "POST") return pollLink(request, env);
  if (path.startsWith("/api/revit/") && request.headers.get("Authorization")) return tokenRoute(request, env, path, method, termsAccepted);
  return null;
}

// POST /api/revit/link/start {computer}: a short code for the person, a long secret for Revit
async function startLink(request: Request, env: Env, origin: string) {
  const body = await readBody(request);
  const code = newUserCode();
  const secret = newSecret();
  const at = new Date();
  await env.DB.prepare(
    "INSERT INTO revit_link (user_code, device_hash, computer, created_at, expires_at, state) VALUES (?, ?, ?, ?, ?, 'pending')",
  ).bind(code, await sha256(secret), computerName(body.computer), at.toISOString(), new Date(at.getTime() + LINK_MINUTES * 60_000).toISOString()).run();
  return json({ userCode: code, deviceCode: secret, url: `${origin}/revit?code=${code}`, expiresIn: LINK_MINUTES * 60, interval: POLL_SECONDS }, 201);
}

// POST /api/revit/link/poll {deviceCode}: waiting, refused, expired, or the token, given once
async function pollLink(request: Request, env: Env) {
  const body = await readBody(request);
  const secret = text(body.deviceCode, 100);
  if (!secret) return json({ error: "Send the link's secret." }, 400);
  const link = await env.DB.prepare("SELECT * FROM revit_link WHERE device_hash = ?").bind(await sha256(secret))
    .first<{ user_code: string; computer: string; expires_at: string; state: string; user_id: string | null; team_hash: string | null }>();
  if (!link) return json({ error: "No such link." }, 404);
  if (link.state === "denied") return json({ error: "The link was refused on the site.", state: "denied" }, 403);
  if (link.state === "used") return json({ error: "This link was already used. Connect again.", state: "used" }, 410);
  if (link.expires_at <= now()) return json({ error: "The link expired. Connect again.", state: "expired" }, 410);
  if (link.state !== "approved" || !link.user_id) return json({ state: "pending", interval: POLL_SECONDS }, 202);
  const token = newSecret(TOKEN_PREFIX);
  const id = newId();
  const user = await env.DB.prepare('SELECT name, email FROM "user" WHERE id = ?').bind(link.user_id).first<{ name: string; email: string }>();
  await env.DB.batch([
    env.DB.prepare("UPDATE revit_link SET state = 'used' WHERE user_code = ? AND state = 'approved'").bind(link.user_code),
    env.DB.prepare("INSERT INTO revit_token (id, user_id, token_hash, computer, team_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(id, link.user_id, await sha256(token), link.computer, link.team_hash, now()),
    logged(env, link.user_id, "revit.linked", null, { link: id, computer: link.computer }),
  ]);
  return json({ state: "approved", token, user });
}

// ---- With the token: what Revit asks and sends ------------------------------------------------------------------------

async function tokenRoute(
  request: Request, env: Env, path: string, method: string, termsAccepted: (userId: string) => Promise<boolean>,
): Promise<Response> {
  const token = bearer(request.headers.get("Authorization"));
  const unlinked = () => json({ error: "This computer is not linked to RightFit online. Connect it again.", need: "link" }, 401);
  if (!token) return unlinked();
  const row = await env.DB.prepare("SELECT id, user_id, computer, team_hash FROM revit_token WHERE token_hash = ? AND revoked_at IS NULL")
    .bind(await sha256(token)).first<TokenRow>();
  if (!row) return unlinked();
  await env.DB.prepare("UPDATE revit_token SET last_used_at = ? WHERE id = ?").bind(now(), row.id).run();
  const user = await env.DB.prepare('SELECT id, name, email FROM "user" WHERE id = ?').bind(row.user_id).first<{ id: string; name: string; email: string }>();
  if (!user) return unlinked();
  if (!(await termsAccepted(user.id))) return json({ error: "Accept RightFit's new terms on the site first.", need: "terms" }, 403);

  if (path === "/api/revit/me" && method === "GET") return me(env, user);
  if (path === "/api/revit/commands" && method === "GET") return nextCommand(env, user.id, row);
  const done = path.match(/^\/api\/revit\/commands\/([\w-]+)$/);
  if (done && method === "POST") return answerCommand(request, env, user.id, row, done[1]);
  const m = path.match(/^\/api\/revit\/projects\/([\w-]+)\/(fitcheck|fitcheck\/data|runs)$/);
  if (!m) return json({ error: "No such endpoint." }, 404);
  const [, projectId, what] = m;
  const member = await tokenAccess(env, projectId, row);
  if (member instanceof Response) return member;
  if (what === "fitcheck" && method === "GET") return revitData(env, projectId);
  if (what === "fitcheck/data" && method === "POST") return sendData(request, env, projectId, member, user.id, row);
  if (what === "runs" && method === "POST") return sendRun(request, env, projectId, member, user.id, row);
  return json({ error: "No such endpoint." }, 404);
}

// A token opens a project its person is in and whose forms they see; a locked one only if the browser that approved the
// link had the team password, and that password is still the same
async function tokenAccess(env: Env, projectId: string, row: TokenRow): Promise<MemberRow | Response> {
  const member = await membership(env, projectId, row.user_id);
  if (!member || !maySeeFitCheck(member.role)) return json({ error: "No such project, or you are not in it." }, 404);
  const info = await env.DB.prepare("SELECT locked FROM project WHERE id = ?").bind(projectId).first<{ locked: number }>();
  if (info?.locked) {
    const ok = Boolean(env.TEAM_PASSWORD) && Boolean(row.team_hash) && sameText(row.team_hash!, await teamToken(env.TEAM_PASSWORD!));
    if (!ok) return json({ error: "This project is locked: approve the link again from a browser that has the team password.", need: "team" }, 403);
  }
  return member;
}

// GET /api/revit/me: who this computer acts for, and the projects whose fit check they see
async function me(env: Env, user: { id: string; name: string; email: string }) {
  const { results } = await env.DB.prepare(
    `SELECT p.id, p.name, p.country, p.locked, m.role FROM member m JOIN project p ON p.id = m.project_id
      WHERE m.user_id = ? ORDER BY p.created_at DESC`,
  ).bind(user.id).all<{ id: string; name: string; country: string; locked: number; role: MemberRow["role"] }>();
  return json({
    user: { name: user.name, email: user.email },
    projects: results.filter((p) => maySeeFitCheck(p.role)).map((p) => ({ ...p, locked: Boolean(p.locked), maySendData: maySendData(p.role) })),
  });
}

async function chosen(env: Env, projectId: string) {
  return env.DB.prepare(
    `SELECT c.set_id AS setId, c.set_label AS setLabel, c.note, c.chosen_at AS chosenAt, u.name AS chosenBy
       FROM fit_choice c LEFT JOIN "user" u ON u.id = c.chosen_by WHERE c.project_id = ?`,
  ).bind(projectId).first();
}

// GET /api/revit/projects/<id>/fitcheck: the project's pump sets and settings, and the reviewers' choice
async function revitData(env: Env, projectId: string) {
  const stored = await env.BUCKET.get(fitKeys(projectId).data);
  const data = stored ? await stored.json<{ candidates: unknown; project: unknown; sentAt: string; sentBy: string }>() : null;
  return json({ candidates: data?.candidates ?? null, project: data?.project ?? null, sentAt: data?.sentAt ?? null, chosen: await chosen(env, projectId) });
}

// POST /api/revit/projects/<id>/fitcheck/data {candidates, project}: the project folder's two files, online
async function sendData(request: Request, env: Env, projectId: string, member: MemberRow, userId: string, row: TokenRow) {
  if (!maySendData(member.role)) return json({ error: "Only a consultant or a designer sends the project's pump sets." }, 403);
  const raw = await request.text();
  if (raw.length > MAX_DATA_BYTES) return json({ error: "The project data is too large." }, 413);
  let body: Record<string, unknown>;
  try { body = JSON.parse(raw); } catch { return json({ error: "Send JSON." }, 400); }
  const data = checkData(body);
  if (typeof data === "string") return json({ error: data }, 400);
  const sentAt = now();
  await env.BUCKET.put(fitKeys(projectId).data, JSON.stringify({ ...data, sentAt, sentBy: userId }), { httpMetadata: { contentType: "application/json" } });
  await logged(env, userId, "fitcheck.data_sent", projectId, { sets: data.candidates.sets.length, computer: row.computer }).run();
  return json({ ok: true, sets: data.candidates.sets.length, sentAt });
}

// POST /api/revit/projects/<id>/runs {...check, image}: one check from Revit
async function sendRun(request: Request, env: Env, projectId: string, member: MemberRow, userId: string, row: TokenRow) {
  if (!maySendRun(member.role)) return json({ error: "Your role does not send checks in this project." }, 403);
  const raw = await request.text();
  if (raw.length > MAX_RUN_BYTES + Math.ceil((2 * 1024 * 1024 * 4) / 3) + 1024) return json({ error: "The check is too large." }, 413);
  let body: Record<string, unknown>;
  try { body = JSON.parse(raw); } catch { return json({ error: "Send JSON." }, 400); }
  const image = pngBytes(body.image);
  if (typeof image === "string") return json({ error: image }, 400);
  delete body.image;
  const check = JSON.stringify(body);
  if (check.length > MAX_RUN_BYTES) return json({ error: "The check is too large." }, 413);
  const summary = summariseRun(body);
  if (typeof summary === "string") return json({ error: summary }, 400);
  const id = newId();
  const at = now();
  const keys = fitKeys(projectId, id);
  await env.BUCKET.put(keys.run, check, { httpMetadata: { contentType: "application/json" } });
  if (image) await env.BUCKET.put(keys.png, image, { httpMetadata: { contentType: "image/png" } });
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO fit_run (id, project_id, user_id, at, action, set_id, set_label, submitted, verdict, confirmed, room, model_file,
                            ran_at, counts, computer, has_image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(id, projectId, userId, at, summary.action, summary.setId, summary.setLabel, summary.submitted ? 1 : 0, summary.verdict,
      summary.confirmed ? 1 : 0, summary.room, summary.model, summary.ranAt, JSON.stringify(summary.counts), row.computer, image ? 1 : 0),
    logged(env, userId, "fitcheck.run", projectId, { run: id, action: summary.action, verdict: summary.verdict }),
  ]);
  return json({ id, at, chosen: await chosen(env, projectId) }, 201);
}

// ---- With a session: approving a link, the linked computers, and the Fit check page -------------------------------------

export async function revitSessionRoute(request: Request, env: Env, user: User, path: string, method: string): Promise<Response | null> {
  let m = path.match(/^\/api\/revit\/link\/([\w-]+)(?:\/(approve|deny))?$/);
  if (m) {
    const code = cleanUserCode(m[1]);
    if (!code) return json({ error: "That is not a RightFit code." }, 404);
    if (!m[2] && method === "GET") return readLink(env, code);
    if (m[2] && method === "POST") return answerLink(request, env, user, code, m[2] as "approve" | "deny");
  }
  if (path === "/api/revit/links" && method === "GET") return links(env, user);
  m = path.match(/^\/api\/revit\/links\/([\w-]+)\/unlink$/);
  if (m && method === "POST") return unlink(env, user, m[1]);

  m = path.match(/^\/api\/projects\/([\w-]+)\/fitcheck(?:\/(choose)|\/runs\/([\w-]+?)(\.png)?|\/(revit)(?:\/([\w-]+))?)?$/);
  if (!m) return null;
  const [, projectId, choose, run, png, revit, command] = m;
  const me = await access(request, env, projectId, user);
  if (me instanceof Response) return me;
  if (!maySeeFitCheck(me.role)) return json({ error: "The fit check reaches subcontractors once forms have their branch." }, 404);
  if (revit && !command && method === "POST") return askRevit(request, env, projectId, me, user);
  if (revit && command && method === "GET") return commandState(env, projectId, user, command);
  if (choose && method === "POST") return choose_(request, env, projectId, me, user);
  if (run && method === "GET") return oneRun(env, projectId, run, Boolean(png));
  if (!choose && !run && !revit && method === "GET") return fitPage(env, projectId, me);
  return json({ error: "No such endpoint." }, 404);
}

async function linkRow(env: Env, code: string) {
  return env.DB.prepare("SELECT user_code, computer, created_at, expires_at, state FROM revit_link WHERE user_code = ?").bind(code)
    .first<{ user_code: string; computer: string; created_at: string; expires_at: string; state: string }>();
}

// GET /api/revit/link/<code>: what the approval page shows
async function readLink(env: Env, code: string) {
  const link = await linkRow(env, code);
  if (!link) return json({ error: "No link has this code. Check it in Revit, or connect again." }, 404);
  return json({ code: link.user_code, computer: link.computer, createdAt: link.created_at, expired: link.expires_at <= now(), state: link.state });
}

// POST /api/revit/link/<code>/approve or /deny. Approving from a browser that has the team password lets the token
// open locked projects too.
async function answerLink(request: Request, env: Env, user: User, code: string, answer: "approve" | "deny") {
  const link = await linkRow(env, code);
  if (!link) return json({ error: "No link has this code. Check it in Revit, or connect again." }, 404);
  if (link.state !== "pending") return json({ error: `This link was already ${link.state === "denied" ? "refused" : "approved"}.` }, 409);
  if (link.expires_at <= now()) return json({ error: "This link expired. Connect again in Revit." }, 410);
  if (answer === "deny") {
    await env.DB.prepare("UPDATE revit_link SET state = 'denied' WHERE user_code = ? AND state = 'pending'").bind(code).run();
    return json({ ok: true, state: "denied" });
  }
  const team = env.TEAM_PASSWORD && (await teamUnlocked(request.headers.get("Cookie"), env.TEAM_PASSWORD)) ? await teamToken(env.TEAM_PASSWORD) : null;
  await env.DB.prepare("UPDATE revit_link SET state = 'approved', user_id = ?, team_hash = ?, approved_at = ? WHERE user_code = ? AND state = 'pending'")
    .bind(user.id, team, now(), code).run();
  return json({ ok: true, state: "approved", lockedProjects: Boolean(team) });
}

// GET /api/revit/links: this person's linked computers
async function links(env: Env, user: User) {
  const { results } = await env.DB.prepare(
    `SELECT id, computer, created_at AS createdAt, last_used_at AS lastUsedAt, team_hash IS NOT NULL AS locked
       FROM revit_token WHERE user_id = ? AND revoked_at IS NULL ORDER BY created_at DESC`,
  ).bind(user.id).all();
  return json({ links: results });
}

// POST /api/revit/links/<id>/unlink: the computer's token stops at once
async function unlink(env: Env, user: User, id: string) {
  const done = await env.DB.prepare("UPDATE revit_token SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL")
    .bind(now(), id, user.id).run();
  if (!done.meta.changes) return json({ error: "No such linked computer." }, 404);
  await logged(env, user.id, "revit.unlinked", null, { link: id }).run();
  return json({ ok: true });
}

// GET /api/projects/<id>/fitcheck: the sets online, the latest checks, the chosen set
async function fitPage(env: Env, projectId: string, me: MemberRow) {
  const stored = await env.BUCKET.get(fitKeys(projectId).data);
  const data = stored ? await stored.json<{ candidates: { sets?: unknown[] }; sentAt: string; sentBy: string }>() : null;
  const sentBy = data ? await env.DB.prepare('SELECT name FROM "user" WHERE id = ?').bind(data.sentBy).first<{ name: string }>() : null;
  const { results: runs } = await env.DB.prepare(
    `SELECT r.id, r.at, r.action, r.set_id AS setId, r.set_label AS setLabel, r.submitted, r.verdict, r.confirmed, r.room,
            r.model_file AS model, r.counts, r.computer, r.has_image AS hasImage, u.name AS ranBy
       FROM fit_run r LEFT JOIN "user" u ON u.id = r.user_id WHERE r.project_id = ? ORDER BY r.at DESC LIMIT 50`,
  ).bind(projectId).all<Record<string, unknown> & { counts: string }>();
  return json({
    sets: setsView(data?.candidates ?? null), sentAt: data?.sentAt ?? null, sentBy: sentBy?.name ?? null,
    runs: runs.map((r) => ({ ...r, submitted: Boolean(r.submitted), confirmed: Boolean(r.confirmed), hasImage: Boolean(r.hasImage), counts: JSON.parse(r.counts || "{}") })),
    chosen: await chosen(env, projectId), mayChoose: mayChoose(me.role),
  });
}

// GET /api/projects/<id>/fitcheck/runs/<run> (and .png): one check in full, and its picture
async function oneRun(env: Env, projectId: string, run: string, png: boolean) {
  const row = await env.DB.prepare("SELECT id FROM fit_run WHERE id = ? AND project_id = ?").bind(run, projectId).first();
  if (!row) return json({ error: "No such check." }, 404);
  const object = await env.BUCKET.get(png ? fitKeys(projectId, run).png : fitKeys(projectId, run).run);
  if (!object) return json({ error: png ? "This check has no picture." : "No such check." }, 404);
  return new Response(object.body, {
    headers: { "Content-Type": png ? "image/png" : "application/json", "Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff" },
  });
}

// POST /api/projects/<id>/fitcheck/choose {setId, note}: a reviewer marks the set they choose, or clears it (setId "")
async function choose_(request: Request, env: Env, projectId: string, me: MemberRow, user: User) {
  if (!mayChoose(me.role)) return json({ error: "Only the reviewers choose the set." }, 403);
  const body = await readBody(request);
  const setId = text(body.setId, 200);
  if (!setId) {
    await env.DB.batch([
      env.DB.prepare("DELETE FROM fit_choice WHERE project_id = ?").bind(projectId),
      logged(env, user.id, "fitcheck.chosen", projectId, { set: null }),
    ]);
    return json({ chosen: null });
  }
  const stored = await env.BUCKET.get(fitKeys(projectId).data);
  const sets = setsView(stored ? (await stored.json<{ candidates: { sets?: unknown[] } }>()).candidates : null);
  const set = sets.find((s) => s.id === setId);
  if (!set) return json({ error: "No such pump set in this project's data." }, 404);
  const label = `${set.maker} ${set.model}`.trim();
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO fit_choice (project_id, set_id, set_label, note, chosen_by, chosen_at) VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT (project_id) DO UPDATE SET set_id = excluded.set_id, set_label = excluded.set_label, note = excluded.note,
         chosen_by = excluded.chosen_by, chosen_at = excluded.chosen_at`,
    ).bind(projectId, setId, label, text(body.note, 500), user.id, now()),
    logged(env, user.id, "fitcheck.chosen", projectId, { set: setId }),
  ]);
  return json({ chosen: await chosen(env, projectId) });
}

// ---- From the site to Revit (spec/features/revit_link.md §9) ----------------------------------------------------------

// POST /api/projects/<id>/fitcheck/revit {setId}: a message for this person's own linked Revit to preview that set
async function askRevit(request: Request, env: Env, projectId: string, me: MemberRow, user: User) {
  if (!mayAskRevit(me.role)) return json({ error: "Your role does not use the fit check." }, 403);
  const linked = await env.DB.prepare("SELECT COUNT(*) AS n FROM revit_token WHERE user_id = ? AND revoked_at IS NULL").bind(user.id).first<{ n: number }>();
  if (!linked?.n) return json({ error: "No computer with Revit is linked to your account yet: in Revit, RightFit › Online › Connect this computer.", need: "link" }, 409);
  const body = await readBody(request);
  const setId = text(body.setId, 200);
  const stored = await env.BUCKET.get(fitKeys(projectId).data);
  const set = setsView(stored ? (await stored.json<{ candidates: { sets?: unknown[] } }>()).candidates : null).find((s) => s.id === setId);
  if (!set) return json({ error: "No such pump set in this project's data." }, 404);
  const id = newId();
  const at = now();
  await env.DB.batch([
    // a newer message replaces the ones still waiting: only the last click counts
    env.DB.prepare("UPDATE revit_command SET state = 'expired' WHERE user_id = ? AND state = 'waiting'").bind(user.id),
    env.DB.prepare("INSERT INTO revit_command (id, user_id, project_id, kind, set_id, set_label, created_at) VALUES (?, ?, ?, 'preview', ?, ?, ?)")
      .bind(id, user.id, projectId, setId, `${set.maker} ${set.model}`.trim(), at),
  ]);
  return json({ id, state: "waiting", text: commandText("waiting", "") }, 201);
}

// GET /api/projects/<id>/fitcheck/revit/<message>: where the message stands, for the page
async function commandState(env: Env, projectId: string, user: User, id: string) {
  const c = await env.DB.prepare("SELECT state, created_at, message FROM revit_command WHERE id = ? AND project_id = ? AND user_id = ?")
    .bind(id, projectId, user.id).first<{ state: string; created_at: string; message: string }>();
  if (!c) return json({ error: "No such message." }, 404);
  let state = c.state;
  if (state === "waiting" && !commandFresh(c.created_at, now())) {
    await env.DB.prepare("UPDATE revit_command SET state = 'expired' WHERE id = ? AND state = 'waiting'").bind(id).run();
    state = "expired";
  }
  return json({ state, text: commandText(state, c.message), final: !["waiting", "taken"].includes(state) });
}

// GET /api/revit/commands: the oldest message still waiting for this computer's person, given to this computer once
async function nextCommand(env: Env, userId: string, row: TokenRow) {
  const at = now();
  const { results } = await env.DB.prepare(
    "SELECT id, project_id, kind, set_id, set_label, created_at FROM revit_command WHERE user_id = ? AND state = 'waiting' ORDER BY created_at LIMIT 5",
  ).bind(userId).all<{ id: string; project_id: string; kind: string; set_id: string; set_label: string; created_at: string }>();
  for (const c of results) {
    if (!commandFresh(c.created_at, at)) {
      await env.DB.prepare("UPDATE revit_command SET state = 'expired' WHERE id = ? AND state = 'waiting'").bind(c.id).run();
      continue;
    }
    // the project must still open for this token (membership, locked projects)
    const member = await tokenAccess(env, c.project_id, row);
    if (member instanceof Response) {
      await env.DB.prepare("UPDATE revit_command SET state = 'failed', message = ? WHERE id = ? AND state = 'waiting'")
        .bind("This computer can't open the project (locked, or not a member).", c.id).run();
      continue;
    }
    const took = await env.DB.prepare("UPDATE revit_command SET state = 'taken', taken_by = ?, taken_at = ? WHERE id = ? AND state = 'waiting'")
      .bind(row.id, at, c.id).run();
    if (!took.meta.changes) continue; // another of this person's computers took it first
    return json({ command: { id: c.id, projectId: c.project_id, kind: c.kind, setId: c.set_id, setLabel: c.set_label }, interval: LISTEN_SECONDS });
  }
  return json({ command: null, interval: LISTEN_SECONDS });
}

// POST /api/revit/commands/<message> {ok, message}: Revit's answer
async function answerCommand(request: Request, env: Env, userId: string, row: TokenRow, id: string) {
  const body = await readBody(request);
  const done = await env.DB.prepare(
    "UPDATE revit_command SET state = ?, message = ?, done_at = ? WHERE id = ? AND user_id = ? AND taken_by = ? AND state = 'taken'",
  ).bind(body.ok === true ? "done" : "failed", text(body.message, 300), now(), id, userId, row.id).run();
  if (!done.meta.changes) return json({ error: "No such message taken by this computer." }, 404);
  return json({ ok: true });
}
