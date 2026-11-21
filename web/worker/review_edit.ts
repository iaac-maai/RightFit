// Changes to a review made online (spec/features/rightfit_online.md, section 11): ticks on readings, decisions on
// findings and on AI suggestions, and the consultant's own rules. This Worker keeps the data in the private bucket; the
// engine (web/engine/, the laptop's own Python) applies each change and runs the checks again, so a review online and
// on the laptop come from the same code.
import { json, logged, now, readBody, type Env, type User } from "./data";
import { access, keys, rulesView, type Tables } from "./project_data";
import { mayChangeReview, mayChangeRules } from "./roles";

const PACKAGE_CHANGES = new Set(["confirm", "decide", "decisions"]);
const RULE_CHANGES = new Set(["new_rule", "rule_active"]);
const EVENT: Record<string, string> = {
  confirm: "review.confirmed", decide: "review.ai_decided", decisions: "review.decided", new_rule: "rules.added", rule_active: "rules.switched",
};
const TRIES = 3; // two people changing the same thing at once: the later one starts again from the other's change
const asJson = { httpMetadata: { contentType: "application/json" } };

interface State { pkg: unknown; boq: unknown; decisions: Record<string, unknown> }
interface View { status: { letter: string; label: string }; counts: Record<string, number> }
interface Answer { pkg?: unknown; decisions?: Record<string, unknown>; consultant?: Tables["consultant"]; view?: View; error?: string }
type Change = Record<string, unknown> & { op: string };

export async function editRoute(request: Request, env: Env, user: User, path: string, method: string): Promise<Response | null> {
  const m = path.match(/^\/api\/projects\/([\w-]+)\/(?:packages\/(P\d+)\/change|rules\/change)$/);
  if (!m || method !== "POST") return null;
  const [, projectId, code] = m;
  const me = await access(request, env, projectId, user);
  if (me instanceof Response) return me;
  const change = (await readBody(request)) as Change;
  if (!(code ? PACKAGE_CHANGES : RULE_CHANGES).has(String(change.op))) return json({ error: "No such change." }, 400);
  if (code ? !mayChangeReview(me.role) : !mayChangeRules(me.role)) {
    return json({ error: code ? "Only the reviewers change a review." : "Only the consultant changes the consultant's rules." }, 403);
  }
  if (!env.ENGINE) return json({ error: "The checks engine is not connected." }, 503);
  const project = await env.DB.prepare("SELECT country FROM project WHERE id = ?").bind(projectId).first<{ country: string }>();
  const location = project?.country ?? "RO";
  return code ? changePackage(env, projectId, code, change, user, location) : changeRules(env, projectId, change, user, location);
}

async function changePackage(env: Env, projectId: string, code: string, change: Change, user: User, location: string) {
  const k = keys(projectId, code);
  const tables = await env.BUCKET.get(k.tables);
  if (!tables) return json({ error: "The rules come with the next import from the laptop." }, 404);
  const data = await tables.json<Tables>();
  for (let attempt = 0; attempt < TRIES; attempt++) {
    const stored = await env.BUCKET.get(k.state);
    if (!stored) return json({ error: "This package can be changed online after the next import from the laptop." }, 404);
    const state = await stored.json<State>();
    const answer = await engine(env, { ...state, tables: data, location, reviewer: user.name, change });
    if (answer.error || !answer.view) return json({ error: answer.error ?? "The checks engine did not answer." }, 400);
    const saved = await env.BUCKET.put(k.state, JSON.stringify({ ...state, pkg: answer.pkg, decisions: answer.decisions }),
      { ...asJson, onlyIf: { etagMatches: stored.etag } });
    if (!saved) continue; // someone else changed this package meanwhile: start again from their change
    await publish(env, projectId, code, answer.view);
    await logged(env, user.id, EVENT[change.op], projectId, { code, ...detail(change) }).run();
    return json({ review: answer.view });
  }
  return json({ error: "Someone else is changing this package right now: try again." }, 409);
}

async function changeRules(env: Env, projectId: string, change: Change, user: User, location: string) {
  const k = keys(projectId);
  for (let attempt = 0; attempt < TRIES; attempt++) {
    const stored = await env.BUCKET.get(k.tables);
    if (!stored) return json({ error: "The rules come with the next import from the laptop." }, 404);
    const data = await stored.json<Tables>();
    const answer = await engine(env, { tables: data, reviewer: user.name, change });
    if (answer.error || !answer.consultant) return json({ error: answer.error ?? "The checks engine did not answer." }, 400);
    const tables = { ...data, consultant: answer.consultant };
    const saved = await env.BUCKET.put(k.tables, JSON.stringify(tables), { ...asJson, onlyIf: { etagMatches: stored.etag } });
    if (!saved) continue;
    // Every package already read is reviewed again with the new rules.
    // shortcut: one engine call per read package, one after the other; batch them once many packages are read online
    const { results } = await env.DB.prepare("SELECT code FROM package WHERE project_id = ? AND letter IS NOT NULL")
      .bind(projectId).all<{ code: string }>();
    for (const { code } of results) {
      const st = await env.BUCKET.get(keys(projectId, code).state);
      if (!st) continue;
      const again = await engine(env, { ...(await st.json<State>()), tables, location, reviewer: user.name });
      if (again.view) await publish(env, projectId, code, again.view);
    }
    await logged(env, user.id, EVENT[change.op], projectId, detail(change)).run();
    return json({ ...rulesView(tables, location), mayEdit: true });
  }
  return json({ error: "Someone else is changing the rules right now: try again." }, 409);
}

async function engine(env: Env, body: unknown): Promise<Answer> {
  const response = await env.ENGINE!.fetch("https://engine.internal/", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return response.json<Answer>().catch(() => ({ error: `The checks engine answered ${response.status}.` }));
}

// The new review goes where the package's page reads it, and its letter and counts to the list of packages
async function publish(env: Env, projectId: string, code: string, view: View) {
  const c = view.counts;
  await env.BUCKET.put(keys(projectId, code).view, JSON.stringify(view), asJson);
  await env.DB.prepare(
    `UPDATE package SET letter = ?, label = ?, problems = ?, questions = ?, to_confirm = ?, readings = ?, reviewed_at = ?
      WHERE project_id = ? AND code = ?`,
  ).bind(view.status.letter, view.status.label, c.problems, c.questions, c.to_confirm, c.readings, now(), projectId, code).run();
}

// What the activity log keeps of a change: what kind, and how many, never the values themselves
function detail(change: Change): Record<string, unknown> {
  if (change.op === "confirm") return { readings: Array.isArray(change.targets) ? change.targets.length : 0 };
  if (change.op === "decisions") return { findings: change.decisions && typeof change.decisions === "object" ? Object.keys(change.decisions).length : 0 };
  if (change.op === "decide") return { status: String(change.status) };
  if (change.op === "rule_active") return { rule: String(change.rule_id), active: Boolean(change.active) };
  return {};
}
