// The project's own data online (spec/features/rightfit_online.md, section 11): its MAF packages, their files,
// RightFit's draft review of the packages already read, and the BOQ lines, imported from the laptop by
// web/scripts/import_project.py. Members only, and for a locked project the team password as well.
import { DPA_VERSION, json, logged, membership, now, readBody, type Env, type MemberRow, type User } from "./data";
import { ACROSS_PROJECTS_FROM, together, type Graph } from "./products";
import { offers, type Elsewhere, type Pkg } from "./reuse";
import { REVIEWERS, isAdmin, mayAddPackage, mayChangeReview, mayChangeRules, mayUseProducts } from "./roles";
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
  extra: `projects/${projectId}/extra/${code}.json`, // what the laptop read from the PDFs: the revision comparison, the marks
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
  const dpa = path.match(/^\/api\/projects\/([\w-]+)\/dpa$/);
  if (dpa && method === "POST") return acceptDpa(request, env, dpa[1], user);
  const pg = path.match(/^\/api\/projects\/([\w-]+)\/pages\/(P\d+)\/(\d{1,3})\/(\d{1,4})\.png$/);
  if (pg && method === "GET") {
    const me = await access(request, env, pg[1], user);
    if (me instanceof Response) return me;
    return pageImage(env, pg[1], pg[2], pg[3], pg[4], me);
  }
  const m = path.match(/^\/api\/projects\/([\w-]+)\/(packages|boq|files|rules|graph|products)(?:\/(P\d+))?(?:\/([^/]+))?$/);
  if (!m || method !== "GET") return null;
  const [, projectId, what, code, name] = m;
  const me = await access(request, env, projectId, user);
  if (me instanceof Response) return me;
  if (what === "packages" && !code) return packages(env, projectId, me);
  if (what === "packages" && code && !name) return onePackage(env, projectId, code, me);
  if (what === "packages" && code && name === "reuse") return reuse(request, env, projectId, code, user, me);
  if (what === "files" && code && name) return file(env, projectId, code, name, me);
  if (what === "boq" && !code) return boq(env, projectId, me);
  if (what === "rules" && !code) return rules(env, projectId, me);
  if (what === "graph" && !code) return graph(env, projectId, user);
  if (what === "products" && !code) return products(request, env, projectId, user, me);
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
            to_confirm AS toConfirm, readings, reviewed_at AS reviewedAt, uploaded_at AS uploadedAt
       FROM package WHERE project_id = ? ORDER BY code`,
  ).bind(projectId).all<{ items: string }>();
  return json({ packages: results.map((p) => ({ ...p, items: JSON.parse(p.items || "[]") as string[] })), mayAdd: mayAddPackage(me.role) });
}

async function onePackage(env: Env, projectId: string, code: string, me: MemberRow) {
  if (!seesForms(me)) return json({ error: "No such package." }, 404);
  const row = await env.DB.prepare(
    `SELECT code, form_no AS formNo, revision, discipline, items, files, pages, letter, label, problems, questions,
            to_confirm AS toConfirm, readings, reviewed_at AS reviewedAt, uploaded_at AS uploadedAt
       FROM package WHERE project_id = ? AND code = ?`,
  ).bind(projectId, code).first<{ items: string }>();
  if (!row) return json({ error: "No such package." }, 404);
  const { results: files } = await env.DB.prepare(
    "SELECT name, size, pages FROM package_file WHERE project_id = ? AND code = ? ORDER BY name",
  ).bind(projectId, code).all();
  const k = keys(projectId, code);
  const [stored, state, more] = await Promise.all([env.BUCKET.get(k.view), env.BUCKET.head(k.state), env.BUCKET.get(k.extra)]);
  const review = stored ? await stored.json() : null;
  const extra = more ? await more.json() : null;
  // the reviewers change a review once its readings are online (they come with an import from the laptop)
  const mayEdit = mayChangeReview(me.role) && Boolean(state);
  const mayAdd = mayAddPackage(me.role) && Boolean((row as { uploadedAt?: string | null }).uploadedAt) && !review;
  return json({ package: { ...row, items: JSON.parse(row.items || "[]") }, files, review, mayEdit, extra, mayAdd });
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

// The knowledge graph of the project (spec/features/knowledge_graph.md): for the Inside RightFit page, which is for
// admins only; and like every other part of a project, only for an admin who is a member (access() above)
async function graph(env: Env, projectId: string, user: User) {
  if (!isAdmin(user, env.ADMIN_EMAILS)) return json({ error: "No such endpoint." }, 404);
  const stored = await env.BUCKET.get(`projects/${projectId}/graph.json`);
  return stored ? json(await stored.json()) : json({ error: "The graph comes with the next import from the laptop." }, 404);
}

// The products that come back, for the consultant's people (spec/features/knowledge_graph.md, sections 5 and 6): this
// project's knowledge graph, with the product lines, forms and answers of the viewer's other projects that accepted the
// data processing agreement with clause 1.4. Only projects the viewer is a consultant of, so nobody sees one they are
// not in; a locked one only with the team password, as everywhere else.
async function products(request: Request, env: Env, projectId: string, user: User, me: MemberRow) {
  if (!mayUseProducts(me.role)) return json({ error: "The products that come back are for the consultant's people." }, 403);
  const project = await env.DB.prepare("SELECT name, dpa_version FROM project WHERE id = ?").bind(projectId)
    .first<{ name: string; dpa_version: string }>();
  const { mine, open } = await across(request, env, user, projectId);
  const read = async (id: string) => (await env.BUCKET.get(`projects/${id}/graph.json`))?.json<Graph>() ?? null;
  const others = (await Promise.all(open.map(async (p) => ({ id: p.id, name: p.name, graph: await read(p.id) }))))
    .filter((p): p is { id: string; name: string; graph: Graph } => p.graph !== null);
  const own = await read(projectId);
  const name = project?.name ?? "This project";
  return json({
    graph: together({ id: projectId, name, graph: own ?? { nodes: [], edges: [] } }, others),
    imported: own !== null, // the graph is made on the laptop at an import; a project made only online has none yet
    projects: [{ id: projectId, name, here: true }, ...others.map((p) => ({ id: p.id, name: p.name, here: false }))],
    waiting: mine.filter((p) => p.dpa_version < ACROSS_PROJECTS_FROM).length,
    dpa: { accepted: project?.dpa_version ?? "", current: DPA_VERSION, across: (project?.dpa_version ?? "") >= ACROSS_PROJECTS_FROM },
  });
}

// The viewer's other projects as a consultant (mine), and those whose data counts across projects for them (open): a
// consultant of it accepted the agreement with clause 1.4, and a locked one only with the team password
async function across(request: Request, env: Env, user: User, projectId: string) {
  const { results: mine } = await env.DB.prepare(
    "SELECT p.id, p.name, p.locked, p.dpa_version FROM member m JOIN project p ON p.id = m.project_id WHERE m.user_id = ? AND m.role = 'consultant' AND p.id <> ?",
  ).bind(user.id, projectId).all<{ id: string; name: string; locked: number; dpa_version: string }>();
  const unlocked = await teamUnlocked(request.headers.get("Cookie"), env.TEAM_PASSWORD);
  return { mine, open: mine.filter((p) => p.dpa_version >= ACROSS_PROJECTS_FROM && (!p.locked || unlocked)) };
}

// GET /api/projects/:id/packages/:code/reuse: readings a person confirmed on the same file in another package of this
// project or, for the consultant's people, of their other projects (MAF-36b). Only offered: a reviewer confirms each.
async function reuse(request: Request, env: Env, projectId: string, code: string, user: User, me: MemberRow) {
  if (!mayChangeReview(me.role)) return json({ offers: [] });
  const state = await env.BUCKET.get(keys(projectId, code).state);
  const { results: mine } = await env.DB.prepare("SELECT name, sha FROM package_file WHERE project_id = ? AND code = ? AND sha IS NOT NULL")
    .bind(projectId, code).all<{ name: string; sha: string }>();
  if (!state || !mine.length) return json({ offers: [] });
  const projects = new Map([[projectId, "this project"]]);
  if (mayUseProducts(me.role)) for (const p of (await across(request, env, user, projectId)).open) projects.set(p.id, p.name);
  const shas = [...new Set(mine.map((f) => f.sha))];
  // shortcut: one query with every fingerprint of the package, fine for a package's few dozen files; batch when larger
  const { results: twins } = await env.DB.prepare(
    `SELECT project_id AS projectId, code, name, sha FROM package_file WHERE sha IN (${shas.map(() => "?").join(", ")})
       AND NOT (project_id = ? AND code = ?)`,
  ).bind(...shas, projectId, code).all<{ projectId: string; code: string; name: string; sha: string }>();
  const where = new Map<string, Record<string, string>>();
  for (const t of twins.filter((t) => projects.has(t.projectId))) {
    const k = `${t.projectId}|${t.code}`;
    where.set(k, { ...(where.get(k) ?? {}), [t.name]: t.sha });
  }
  const elsewhere = (await Promise.all([...where].map(async ([k, files]): Promise<Elsewhere | null> => {
    const [pid, pcode] = k.split("|");
    const stored = await env.BUCKET.get(keys(pid, pcode).state);
    return stored ? { where: projects.get(pid)!, code: pcode, pkg: (await stored.json<{ pkg: Pkg }>()).pkg, files } : null;
  }))).filter((e): e is Elsewhere => e !== null);
  const here = (await state.json<{ pkg: Pkg }>()).pkg;
  return json({ offers: offers(here, Object.fromEntries(mine.map((f) => [f.name, f.sha])), elsewhere) });
}

// POST /api/projects/:id/dpa {version}: a consultant accepts the current data processing agreement for the organisation
async function acceptDpa(request: Request, env: Env, projectId: string, user: User) {
  const me = await membership(env, projectId, user.id);
  if (!me || !mayUseProducts(me.role)) return json({ error: "Only a consultant of the project accepts the agreement for the organisation." }, 403);
  if ((await readBody(request)).version !== DPA_VERSION) return json({ error: "The agreement has changed: open it again before you accept it." }, 409);
  const at = now();
  await env.DB.batch([
    env.DB.prepare("UPDATE project SET dpa_version = ?, dpa_accepted_by = ?, dpa_accepted_at = ? WHERE id = ?").bind(DPA_VERSION, user.id, at, projectId),
    logged(env, user.id, "project.dpa_accepted", projectId, { version: DPA_VERSION }),
  ]);
  return json({ ok: true, version: DPA_VERSION });
}

// One page of an attachment as an image, drawn on the laptop at the import, for the marks on the quoted lines
async function pageImage(env: Env, projectId: string, code: string, no: string, page: string, me: MemberRow) {
  if (!seesForms(me)) return json({ error: "No such page." }, 404);
  const object = await env.BUCKET.get(`projects/${projectId}/pages/${code}/${no}/${page}.png`);
  if (!object) return json({ error: "No such page." }, 404);
  return new Response(object.body, {
    headers: { "Content-Type": "image/png", "Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff" },
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
