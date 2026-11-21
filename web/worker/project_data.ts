// The project's own data online (spec/features/rightfit_online.md, section 11): its MAF packages, their files,
// RightFit's draft review of the packages already read, and the BOQ lines, imported from the laptop by
// web/scripts/import_project.py. Members only, and for a locked project the team password as well.
import { json, logged, membership, now, readBody, type Env, type MemberRow, type User } from "./data";
import { REVIEWERS, mayChangeReview, mayChangeRules } from "./roles";
import { sameText, teamCookie, teamUnlocked } from "./team";

const TYPES: Record<string, string> = {
  pdf: "application/pdf", xls: "application/vnd.ms-excel", xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  doc: "application/msword", docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", txt: "text/plain; charset=utf-8",
};

// Where a project's data sits in the private bucket. state is a package's readings and the reviewer's decisions, which
// change online (review_edit.ts); reviews is the review the engine made from them, which the package's page reads.
export const keys = (projectId: string, code?: string) => ({
  tables: `projects/${projectId}/tables.json`,
  state: `projects/${projectId}/state/${code}.json`,
  view: `projects/${projectId}/reviews/${code}.json`,
});

// The rule tables the checks use, as the laptop's data/maf holds them, with the consultant's own rules of this project
type Row = Record<string, string>;
export interface Tables {
  rules: Row[]; family_documents: Row[]; checklist: Row[]; library: unknown; consultant: Row[];
  names: { doc_types: Record<string, string>; values: Record<string, string>; kinds: string[]; families: string[] };
}
const CHAINS: Record<string, string[]> = { RO: ["EU", "RO", "ANY"], ES: ["EU", "ES", "ANY"] }; // as in checks/maf/rules.py

// What the Rules page shows: the law and practice for the project's country, the checklist, the consultant's rules
export const rulesView = (t: Tables, location: string) => ({
  location,
  law: t.rules.filter((r) => (CHAINS[location] ?? CHAINS.RO).includes(r.jurisdiction)),
  checklist: t.checklist,
  mine: { rules: t.consultant, ...t.names },
});

// A member may open the project's data; a locked project also needs the team password's cookie
export async function access(request: Request, env: Env, projectId: string, user: User): Promise<MemberRow | Response> {
  const me = await membership(env, projectId, user.id);
  if (!me) return json({ error: "No such project, or you are not in it." }, 404);
  const info = await env.DB.prepare("SELECT name, locked FROM project WHERE id = ?").bind(projectId).first<{ name: string; locked: number }>();
  if (info?.locked && !(await teamUnlocked(request.headers.get("Cookie"), env.TEAM_PASSWORD))) {
    return json({ error: "This project opens with the team password.", need: "team", project: info.name }, 403);
  }
  return me;
}

export async function dataRoute(request: Request, env: Env, user: User, path: string, method: string): Promise<Response | null> {
  if (path === "/api/team/unlock" && method === "POST") return unlock(request, env, user);
  const m = path.match(/^\/api\/projects\/([\w-]+)\/(packages|boq|files|rules)(?:\/(P\d+))?(?:\/([^/]+))?$/);
  if (!m || method !== "GET") return null;
  const [, projectId, what, code, name] = m;
  const me = await access(request, env, projectId, user);
  if (me instanceof Response) return me;
  if (what === "packages" && !code) return packages(env, projectId, me);
  if (what === "packages" && code && !name) return onePackage(env, projectId, code, me);
  if (what === "files" && code && name) return file(env, projectId, code, name, me);
  if (what === "boq" && !code) return boq(env, projectId, me);
  if (what === "rules" && !code) return rules(env, projectId, me);
  return json({ error: "No such endpoint." }, 404);
}

// The rules the checks use for the project's country: the law's, the checklist, the consultant's own
async function rules(env: Env, projectId: string, me: MemberRow) {
  if (!seesForms(me)) return json({ error: "The rules reach subcontractors once forms have their branch." }, 404);
  const tables = await env.BUCKET.get(keys(projectId).tables);
  if (tables) {
    const project = await env.DB.prepare("SELECT country FROM project WHERE id = ?").bind(projectId).first<{ country: string }>();
    return json({ ...rulesView(await tables.json<Tables>(), project?.country ?? "RO"), mayEdit: mayChangeRules(me.role) });
  }
  const before = await env.BUCKET.get(`projects/${projectId}/rules.json`); // imported before the rules could change online
  return before ? json({ ...(await before.json<object>()), mayEdit: false }) : json({ error: "The rules come with the next import from the laptop." }, 404);
}

// Forms belong to a branch only from MAF-32; until then a subcontractor sees none of the imported ones
const seesForms = (me: MemberRow) => REVIEWERS.includes(me.role) || me.role === "contractor";

async function packages(env: Env, projectId: string, me: MemberRow) {
  if (!seesForms(me)) return json({ packages: [], note: "Forms reach subcontractors once each has its branch." });
  const { results } = await env.DB.prepare(
    `SELECT code, form_no AS formNo, revision, discipline, items, files, pages, letter, label, problems, questions,
            to_confirm AS toConfirm, readings, reviewed_at AS reviewedAt
       FROM package WHERE project_id = ? ORDER BY code`,
  ).bind(projectId).all<{ items: string }>();
  return json({ packages: results.map((p) => ({ ...p, items: JSON.parse(p.items || "[]") as string[] })) });
}

async function onePackage(env: Env, projectId: string, code: string, me: MemberRow) {
  if (!seesForms(me)) return json({ error: "No such package." }, 404);
  const row = await env.DB.prepare(
    `SELECT code, form_no AS formNo, revision, discipline, items, files, pages, letter, label, problems, questions,
            to_confirm AS toConfirm, readings, reviewed_at AS reviewedAt
       FROM package WHERE project_id = ? AND code = ?`,
  ).bind(projectId, code).first<{ items: string }>();
  if (!row) return json({ error: "No such package." }, 404);
  const { results: files } = await env.DB.prepare(
    "SELECT name, size, pages FROM package_file WHERE project_id = ? AND code = ? ORDER BY name",
  ).bind(projectId, code).all();
  const k = keys(projectId, code);
  const [stored, state] = await Promise.all([env.BUCKET.get(k.view), env.BUCKET.head(k.state)]);
  const review = stored ? await stored.json() : null;
  // the reviewers change a review once its readings are online (they come with an import from the laptop)
  const mayEdit = mayChangeReview(me.role) && Boolean(state);
  return json({ package: { ...row, items: JSON.parse(row.items || "[]") }, files, review, mayEdit });
}

// One original file, from the private bucket, shown in the browser
async function file(env: Env, projectId: string, code: string, encoded: string, me: MemberRow) {
  if (!seesForms(me)) return json({ error: "No such file." }, 404);
  let name: string;
  try {
    name = decodeURIComponent(encoded);
  } catch {
    return json({ error: "No such file." }, 404);
  }
  if (!name || name.length > 200 || /[\\/]|\.\./.test(name)) return json({ error: "No such file." }, 404);
  const listed = await env.DB.prepare("SELECT 1 AS yes FROM package_file WHERE project_id = ? AND code = ? AND name = ?").bind(projectId, code, name).first();
  const object = listed ? await env.BUCKET.get(`projects/${projectId}/packages/${code}/${name}`) : null;
  if (!object) return json({ error: "No such file." }, 404);
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return new Response(object.body, {
    headers: {
      "Content-Type": TYPES[ext] ?? "application/octet-stream",
      "Content-Disposition": `inline; filename*=UTF-8''${encodeURIComponent(name)}`,
      "Cache-Control": "private, max-age=300",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function boq(env: Env, projectId: string, me: MemberRow) {
  if (!seesForms(me)) return json({ lines: [], note: "The BOQ reaches subcontractors once forms have their branch." });
  const { results } = await env.DB.prepare(
    "SELECT file, sheet, row, nr, text, unit, qty, producer, standards FROM boq_line WHERE project_id = ? ORDER BY file, sheet, row",
  ).bind(projectId).all();
  return json({ lines: results });
}

// POST /api/team/unlock {password}: the team password, checked on the server; five wrong tries in 15 minutes wait
async function unlock(request: Request, env: Env, user: User) {
  if (!env.TEAM_PASSWORD) return json({ error: "No team password has been set yet." }, 503);
  const since = new Date(Date.now() - 15 * 60_000).toISOString();
  const tries = await env.DB.prepare("SELECT COUNT(*) AS n FROM event WHERE actor = ? AND action = 'team.unlock_failed' AND at > ?")
    .bind(user.id, since).first<{ n: number }>();
  if ((tries?.n ?? 0) >= 5) return json({ error: "Too many wrong tries: wait 15 minutes." }, 429);
  const password = (await readBody(request)).password;
  if (typeof password !== "string" || !sameText(password, env.TEAM_PASSWORD)) {
    await logged(env, user.id, "team.unlock_failed").run();
    return json({ error: "That is not the team password." }, 401);
  }
  await logged(env, user.id, "team.unlocked", null, { at: now() }).run();
  const secure = new URL(request.url).protocol === "https:";
  return json({ ok: true }, 200, { "Set-Cookie": await teamCookie(env.TEAM_PASSWORD, secure) });
}
