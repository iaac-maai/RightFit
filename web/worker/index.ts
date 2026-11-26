// The API of RightFit online (spec/features/rightfit_online.md). One Worker on Cloudflare answers every /api/...
// request; every other path is the React page. Each request is checked here, in this order: an account (Better
// Auth), the terms, membership of the project, then what the role allows (roles.ts). Every query names the person
// or the project, so nobody reads a project they are not in. Management lives in admin.ts.
import { adminRoute } from "./admin";
import { access, dataRoute } from "./project_data";
import { editRoute } from "./review_edit";
import { revitOpenRoute, revitSessionRoute } from "./revit";
import { surveyOpenRoute, surveyRoute } from "./survey";
import { uploadRoute } from "./upload";
import { googleOn, makeAuth } from "./auth";
import {
  DPA_VERSION, deleteAccount, json, logged, membership, newId, now, readBody, sha256, text, type Env, type MemberRow, type User,
} from "./data";
import {
  isAdmin, isRole, mayInvite, mayWithdraw, rolesInvitableBy, ROLE_LABEL, visibleInvitations, visiblePeople, type Person, type Role,
} from "./roles";

// The version of the terms a person accepts (web/legal/ carries the same date: change them together); the data
// processing agreement's is in data.ts
const TERMS_VERSION = "2026-11-26"; // the terms of service, read with the privacy policy
const INVITATION_DAYS = 14;

interface InvitationRow {
  id: string; project_id: string; email: string; role: Role; company: string; invited_by: string; created_at: string;
  expires_at: string; state: "pending" | "accepted" | "declined" | "withdrawn"; project: string;
  invited_by_name: string | null; inviter_company: string | null; inviter_role: Role | null;
}

export default {
  async fetch(request, env) {
    try {
      return await route(request, env);
    } catch (err) {
      console.error(err);
      return json({ error: "Something went wrong on our side. Try again." }, 500);
    }
  },
} satisfies ExportedHandler<Env>;

async function route(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  // Our own changes take no request from another site's page (Better Auth checks its own routes)
  if (method !== "GET" && !path.startsWith("/api/auth/") && !sameOrigin(request, url)) {
    return json({ error: "RightFit only answers its own page." }, 403);
  }

  const auth = makeAuth(env, url.origin);
  if (path.startsWith("/api/auth/")) return auth.handler(request);

  // Revit, with no session: starting a link, asking whether it was approved, and its token's own requests (revit.ts)
  const revit = await revitOpenRoute(request, env, path, method, url.origin, (userId) => accepted(env, userId));
  if (revit) return revit;

  // The practice survey is answered without an account (survey.ts)
  const survey = await surveyOpenRoute(request, env, path, method);
  if (survey) return survey;

  // An invitation can be read before signing in: the link itself is the secret
  const joinLink = path.match(/^\/api\/join\/([\w-]+)$/);
  if (joinLink && method === "GET") return readInvitation(env, joinLink[1]);

  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return json({ error: "Sign in to RightFit.", need: "account", google: googleOn(env) }, 401);
  const user = { ...session.user, emailVerified: Boolean(session.user.emailVerified) } as User;
  const termsAccepted = await accepted(env, user.id);
  const admin = isAdmin(user, env.ADMIN_EMAILS);

  if (path === "/api/session") {
    return json({
      user: { name: user.name, email: user.email, image: user.image ?? null, emailVerified: user.emailVerified },
      termsAccepted, termsVersion: TERMS_VERSION, dpaVersion: DPA_VERSION, admin,
    });
  }
  if (path === "/api/terms/accept" && method === "POST") return accept(env, user.id);
  if (path === "/api/account/delete" && method === "POST") return deleteMine(env, user.id);
  if (!termsAccepted) return json({ error: "Accept the terms first.", need: "terms" }, 403);

  if (path.startsWith("/api/admin/")) {
    // Management answers "not found" to everyone else, so it doesn't show it exists
    return admin ? adminRoute(request, env, user, path, method) : json({ error: "No such endpoint." }, 404);
  }
  const results = await surveyRoute(env, path, method, admin);
  if (results) return results;
  if (path === "/api/home" && method === "GET") return home(env, user);
  if (path === "/api/projects" && method === "POST") return createProject(request, env, user);
  if (joinLink && method === "POST") return joinByLink(env, joinLink[1], user);

  let m = path.match(/^\/api\/invitations\/([\w-]+)\/(accept|decline|withdraw)$/);
  if (m && method === "POST") return answerInvitation(env, m[1], m[2] as "accept" | "decline" | "withdraw", user);
  m = path.match(/^\/api\/projects\/([\w-]+)$/);
  if (m && method === "GET") return project(request, env, m[1], user);
  m = path.match(/^\/api\/projects\/([\w-]+)\/invitations$/);
  if (m && method === "POST") return invite(request, env, m[1], user, url.origin);
  m = path.match(/^\/api\/projects\/([\w-]+)\/members\/([\w-]+)\/remove$/);
  if (m && method === "POST") return removeMember(env, m[1], m[2], user);

  const linked = await revitSessionRoute(request, env, user, path, method);
  if (linked) return linked;
  const edit = await editRoute(request, env, user, path, method);
  if (edit) return edit;
  const upload = await uploadRoute(request, env, user, path, method);
  if (upload) return upload;
  const data = await dataRoute(request, env, user, path, method);
  if (data) return data;
  return json({ error: "No such endpoint." }, 404);
}

// ---- Small helpers ----------------------------------------------------------

const notFound = () => json({ error: "No such project, or you are not in it." }, 404);
const roleWord = (role: Role) => ROLE_LABEL[role].toLowerCase();
const person = (m: { id: string; role: Role; invited_by: string | null }): Person => ({ id: m.id, role: m.role, invitedBy: m.invited_by });
const emailOf = (value: unknown) => text(value, 254).toLowerCase();
const looksLikeEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

function sameOrigin(request: Request, url: URL) {
  const origin = request.headers.get("Origin");
  return !origin || origin === url.origin;
}

// The secret in an invitation link: 32 random bytes, written with the letters a URL allows
function newToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// ---- Terms and the account ----------------------------------------------------------

async function accepted(env: Env, userId: string) {
  const row = await env.DB.prepare('SELECT 1 AS yes FROM consent WHERE "userId" = ? AND "termsVersion" = ?').bind(userId, TERMS_VERSION).first();
  return Boolean(row);
}

// POST /api/terms/accept: the person accepted the terms and read the privacy policy; we keep which version and when
async function accept(env: Env, userId: string) {
  await env.DB.batch([
    env.DB.prepare('INSERT OR IGNORE INTO consent ("userId", "termsVersion", "acceptedAt") VALUES (?, ?, ?)').bind(userId, TERMS_VERSION, now()),
    logged(env, userId, "terms.accepted", null, { version: TERMS_VERSION }),
  ]);
  return json({ ok: true, termsVersion: TERMS_VERSION });
}

// POST /api/account/delete: everything of this person's goes (data.ts says what), and the browser forgets the session
async function deleteMine(env: Env, userId: string) {
  const handOver = await deleteAccount(env, userId, userId, "account.deleted");
  if (handOver) return json({ error: `First make someone else a consultant of ${handOver.join(", ")}.` }, 409);
  const headers = new Headers();
  for (const name of ["better-auth.session_token", "__Secure-better-auth.session_token"]) {
    headers.append("Set-Cookie", `${name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`);
  }
  return json({ deleted: true }, 200, headers);
}

// ---- Home and projects ----------------------------------------------------------

// GET /api/home: this person's projects, with their role and how many people they see there, and the invitations
// waiting for their address (only an address Google verified: anyone else joins through the link)
async function home(env: Env, user: User) {
  const { results: mine } = await env.DB.prepare(
    `SELECT p.id, p.name, p.country, p.locked, m.id AS member_id, m.role, m.company
       FROM member m JOIN project p ON p.id = m.project_id
      WHERE m.user_id = ? ORDER BY p.created_at DESC`,
  ).bind(user.id).all<{ id: string; name: string; country: string; locked: number; member_id: string; role: Role; company: string }>();
  const { results: everyone } = await env.DB.prepare(
    "SELECT id, project_id, role, invited_by FROM member WHERE project_id IN (SELECT project_id FROM member WHERE user_id = ?)",
  ).bind(user.id).all<{ id: string; project_id: string; role: Role; invited_by: string | null }>();
  const projects = mine.map((p) => {
    const team = everyone.filter((e) => e.project_id === p.id).map(person);
    const me = team.find((t) => t.id === p.member_id) ?? { id: p.member_id, role: p.role, invitedBy: null };
    return { id: p.id, name: p.name, country: p.country, locked: Boolean(p.locked), role: p.role, company: p.company, people: visiblePeople(team, me).length };
  });
  let invitations: unknown[] = [];
  if (user.emailVerified) {
    ({ results: invitations } = await env.DB.prepare(
      `SELECT i.id, i.role, i.company, i.created_at AS createdAt, i.expires_at AS expiresAt, p.name AS project,
              u.name AS invitedBy, im.company AS inviterCompany, im.role AS inviterRole
         FROM invitation i JOIN project p ON p.id = i.project_id
         LEFT JOIN member im ON im.id = i.invited_by LEFT JOIN "user" u ON u.id = im.user_id
        WHERE i.email = ? AND i.state = 'pending' AND i.expires_at > ?
          AND i.project_id NOT IN (SELECT project_id FROM member WHERE user_id = ?)
        ORDER BY i.created_at DESC`,
    ).bind(user.email.toLowerCase(), now(), user.id).all());
  }
  return json({ projects, invitations });
}

// POST /api/projects {name, country, company, dpa}: whoever opens a project is its first consultant, and accepts the
// data processing agreement for their organisation, because the forms and files of a project are its data
async function createProject(request: Request, env: Env, user: User) {
  const body = await readBody(request);
  const name = text(body.name, 120);
  if (!name) return json({ error: "Give the project a name." }, 400);
  if (body.dpa !== true) return json({ error: "Accept the data processing agreement for your organisation." }, 400);
  const country = body.country === "ES" ? "ES" : "RO";
  const id = newId();
  const at = now();
  await env.DB.batch([
    env.DB.prepare(
      "INSERT INTO project (id, name, country, created_by, created_at, dpa_version, dpa_accepted_by, dpa_accepted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    ).bind(id, name, country, user.id, at, DPA_VERSION, user.id, at),
    env.DB.prepare("INSERT INTO member (id, project_id, user_id, role, company, invited_by, joined_at) VALUES (?, ?, ?, 'consultant', ?, NULL, ?)")
      .bind(newId(), id, user.id, text(body.company, 120), at),
    logged(env, user.id, "project.opened", id, { dpa: DPA_VERSION }),
  ]);
  return json({ id }, 201);
}

// GET /api/projects/<id>: the project, the people this member may see, the pending invitations they may see,
// and what they may do here
async function project(request: Request, env: Env, projectId: string, user: User) {
  const me = await access(request, env, projectId, user); // a member, with the team password for a locked project
  if (me instanceof Response) return me;
  const info = await env.DB.prepare(
    `SELECT id, name, country, created_at AS createdAt, locked,
            (SELECT COUNT(*) FROM package k WHERE k.project_id = project.id) AS packages,
            (SELECT COUNT(*) FROM boq_line b WHERE b.project_id = project.id) AS boqLines
       FROM project WHERE id = ?`,
  ).bind(projectId).first();
  const { results: rows } = await env.DB.prepare(
    `SELECT m.id, m.role, m.company, m.invited_by, m.joined_at, u.name, u.email, u.image
       FROM member m JOIN "user" u ON u.id = m.user_id WHERE m.project_id = ? ORDER BY m.joined_at`,
  ).bind(projectId).all<MemberRow & { name: string; email: string; image: string | null }>();
  const team = rows.map((r) => ({
    ...person(r), name: r.name, email: r.email, image: r.image, company: r.company, joinedAt: r.joined_at,
  }));
  const { results: pending } = await env.DB.prepare(
    `SELECT id, email, role, company, invited_by AS invitedBy, created_at AS createdAt, expires_at AS expiresAt
       FROM invitation WHERE project_id = ? AND state = 'pending' ORDER BY created_at`,
  ).bind(projectId).all<{ id: string; email: string; role: Role; company: string; invitedBy: string; createdAt: string; expiresAt: string }>();
  const viewer = person(me);
  const at = now();
  return json({
    project: info,
    me: { id: me.id, role: me.role, company: me.company },
    people: visiblePeople(team, viewer),
    invitations: visibleInvitations(pending, team, viewer).map((i) => ({ ...i, expired: i.expiresAt <= at, mayWithdraw: mayWithdraw(viewer, i.invitedBy) })),
    mayInvite: rolesInvitableBy(me.role),
    mayRemove: me.role === "consultant",
  });
}

// ---- Invitations ----------------------------------------------------------

// POST /api/projects/<id>/invitations {email, role, company}: the link, shown once to whoever invites
async function invite(request: Request, env: Env, projectId: string, user: User, origin: string) {
  const me = await membership(env, projectId, user.id);
  if (!me) return notFound();
  const body = await readBody(request);
  const role = body.role;
  if (!isRole(role)) return json({ error: "Pick the role they will have." }, 400);
  if (!mayInvite(me.role, role)) return json({ error: `A ${roleWord(me.role)} can't invite a ${roleWord(role)}.` }, 403);
  const email = emailOf(body.email);
  if (!looksLikeEmail(email)) return json({ error: "Write their whole email address." }, 400);
  const member = await env.DB.prepare(
    `SELECT m.role FROM member m JOIN "user" u ON u.id = m.user_id WHERE m.project_id = ? AND lower(u.email) = ?`,
  ).bind(projectId, email).first<{ role: Role }>();
  if (member) return json({ error: `${email} is already in this project, as ${roleWord(member.role)}.` }, 409);
  const earlier = await env.DB.prepare(
    "SELECT id, invited_by FROM invitation WHERE project_id = ? AND email = ? AND state = 'pending' AND expires_at > ?",
  ).bind(projectId, email, now()).first<{ id: string; invited_by: string }>();
  if (earlier && !mayWithdraw(person(me), earlier.invited_by)) {
    return json({ error: `${email} already has an invitation to this project, from someone else.` }, 409);
  }
  const token = newToken();
  const id = newId();
  const created = new Date();
  const expires = new Date(created.getTime() + INVITATION_DAYS * 86_400_000);
  const company = text(body.company, 120) || (role === me.role ? me.company : "");
  await env.DB.batch([
    // a new invitation to the same address replaces the one before, so only the newest link works
    env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE project_id = ? AND email = ? AND state = 'pending'").bind(projectId, email),
    env.DB.prepare(
      `INSERT INTO invitation (id, project_id, email, role, company, invited_by, token_hash, created_at, expires_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(id, projectId, email, role, company, me.id, await sha256(token), created.toISOString(), expires.toISOString()),
    logged(env, user.id, "invitation.sent", projectId, { invitation: id, role: ROLE_LABEL[role] }),
  ]);
  return json({ id, link: `${origin}/join/${token}`, email, role, expiresAt: expires.toISOString() }, 201);
}

async function findInvitation(env: Env, where: "i.token_hash = ?" | "i.id = ?", value: string) {
  return env.DB.prepare(
    `SELECT i.*, p.name AS project, u.name AS invited_by_name, im.company AS inviter_company, im.role AS inviter_role
       FROM invitation i JOIN project p ON p.id = i.project_id
       LEFT JOIN member im ON im.id = i.invited_by LEFT JOIN "user" u ON u.id = im.user_id
      WHERE ${where}`,
  ).bind(value).first<InvitationRow>();
}

// GET /api/join/<token>, before signing in: what the invitation says, so the page can show it
async function readInvitation(env: Env, token: string) {
  const inv = await findInvitation(env, "i.token_hash = ?", await sha256(token));
  if (!inv) return json({ error: "This invitation link is not valid." }, 404);
  return json({
    project: inv.project, role: inv.role, company: inv.company, email: inv.email, invitedBy: inv.invited_by_name,
    inviterCompany: inv.inviter_company, inviterRole: inv.inviter_role, state: inv.state, expired: inv.expires_at <= now(),
    google: googleOn(env),
  });
}

// POST /api/join/<token>: the link and an account with the invited address
async function joinByLink(env: Env, token: string, user: User) {
  const inv = await findInvitation(env, "i.token_hash = ?", await sha256(token));
  if (!inv) return json({ error: "This invitation link is not valid." }, 404);
  return join(env, inv, user);
}

async function join(env: Env, inv: InvitationRow, user: User) {
  if (inv.state !== "pending") return json({ error: `This invitation was ${inv.state}.` }, 409);
  if (inv.expires_at <= now()) return json({ error: "This invitation has expired: ask for a new one." }, 410);
  if (user.email.toLowerCase() !== inv.email) {
    return json({ error: `This invitation is for ${inv.email}, and you are signed in as ${user.email}.`, need: "other-account" }, 403);
  }
  const already = await membership(env, inv.project_id, user.id);
  if (already) return json({ error: `You are already in this project, as ${roleWord(already.role)}.`, projectId: inv.project_id }, 409);
  await env.DB.batch([
    env.DB.prepare("INSERT INTO member (id, project_id, user_id, role, company, invited_by, joined_at) VALUES (?, ?, ?, ?, ?, ?, ?)")
      .bind(newId(), inv.project_id, user.id, inv.role, inv.company, inv.invited_by, now()),
    env.DB.prepare("UPDATE invitation SET state = 'accepted' WHERE id = ? AND state = 'pending'").bind(inv.id),
    logged(env, user.id, "member.joined", inv.project_id, { invitation: inv.id, role: ROLE_LABEL[inv.role] }),
  ]);
  return json({ projectId: inv.project_id });
}

// POST /api/invitations/<id>/accept or /decline, from the home screen (a Google-verified address), or /withdraw,
// by whoever sent it or a consultant
async function answerInvitation(env: Env, id: string, action: "accept" | "decline" | "withdraw", user: User) {
  const inv = await findInvitation(env, "i.id = ?", id);
  const missing = () => json({ error: "No such invitation." }, 404);
  if (!inv) return missing();
  if (action === "withdraw") {
    const me = await membership(env, inv.project_id, user.id);
    if (!me) return missing();
    if (!mayWithdraw(person(me), inv.invited_by)) return json({ error: "Only whoever sent it, or a consultant, can withdraw it." }, 403);
    await env.DB.batch([
      env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE id = ? AND state = 'pending'").bind(id),
      logged(env, user.id, "invitation.withdrawn", inv.project_id, { invitation: id }),
    ]);
    return json({ ok: true });
  }
  if (!user.emailVerified || user.email.toLowerCase() !== inv.email) return missing();
  if (action === "accept") return join(env, inv, user);
  await env.DB.batch([
    env.DB.prepare("UPDATE invitation SET state = 'declined' WHERE id = ? AND state = 'pending'").bind(id),
    logged(env, user.id, "invitation.declined", inv.project_id, { invitation: id }),
  ]);
  return json({ ok: true });
}

// POST /api/projects/<id>/members/<member>/remove: a consultant takes someone out; a project keeps one consultant
async function removeMember(env: Env, projectId: string, memberId: string, user: User) {
  const me = await membership(env, projectId, user.id);
  if (!me) return notFound();
  if (me.role !== "consultant") return json({ error: "Only a consultant can take someone out of the project." }, 403);
  const target = await env.DB.prepare("SELECT id, role FROM member WHERE id = ? AND project_id = ?").bind(memberId, projectId).first<{ id: string; role: Role }>();
  if (!target) return json({ error: "No such person in this project." }, 404);
  if (target.role === "consultant") {
    const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM member WHERE project_id = ? AND role = 'consultant'").bind(projectId).first<{ n: number }>();
    if ((row?.n ?? 0) <= 1) return json({ error: "A project keeps at least one consultant." }, 409);
  }
  await env.DB.batch([
    env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE invited_by = ? AND state = 'pending'").bind(memberId),
    env.DB.prepare("DELETE FROM member WHERE id = ?").bind(memberId),
    logged(env, user.id, "member.removed", projectId, { member: memberId, role: ROLE_LABEL[target.role] }),
  ]);
  return json({ ok: true });
}
