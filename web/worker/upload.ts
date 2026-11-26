// A package added on the site (spec/features/rightfit_online.md, section 11): its files go into the private bucket,
// next to the packages imported from the laptop, and the package waits there until RightFit's reader has read it.
// The reviewers and the contractor add packages; an import from the laptop leaves a package added here as it is.
import { json, logged, now, readBody, type Env, type MemberRow, type User } from "./data";
import { access } from "./project_data";
import { mayAddPackage } from "./roles";

const MAX = 60 * 1024 * 1024; // the largest file, as on the laptop
const TYPES: Record<string, string> = {
  pdf: "application/pdf", xls: "application/vnd.ms-excel", xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  doc: "application/msword", docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png",
};

export async function uploadRoute(request: Request, env: Env, user: User, path: string, method: string): Promise<Response | null> {
  const add = path.match(/^\/api\/projects\/([\w-]+)\/packages\/new$/);
  const put = path.match(/^\/api\/projects\/([\w-]+)\/packages\/(P\d+)\/upload\/([^/]+)$/);
  if (!(add && method === "POST") && !(put && method === "PUT")) return null;
  const projectId = (add ?? put)![1];
  const me = await access(request, env, projectId, user);
  if (me instanceof Response) return me;
  if (!mayAddPackage(me.role)) return json({ error: "The reviewers and the contractor add packages." }, 403);
  return add ? newPackage(request, env, projectId, me, user) : putFile(request, env, projectId, put![2], put![3]);
}

// POST /api/projects/:id/packages/new {form}: a new package, numbered after the project's others (P52, P53 ...)
async function newPackage(request: Request, env: Env, projectId: string, me: MemberRow, user: User) {
  const form = String((await readBody(request)).form ?? "").replace(/\s+/g, " ").trim().slice(0, 40);
  const { results } = await env.DB.prepare("SELECT code FROM package WHERE project_id = ?").bind(projectId).all<{ code: string }>();
  const next = Math.max(0, ...results.map((r) => Number(r.code.slice(1)) || 0)) + 1;
  const code = `P${String(next).padStart(2, "0")}`;
  const at = now();
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO package (project_id, code, form_no, revision, discipline, items, files, imported_at, uploaded_by, uploaded_at)
       VALUES (?, ?, ?, 0, '', '[]', 0, ?, ?, ?)`,
    ).bind(projectId, code, form || "Not read yet", at, user.id, at),
    logged(env, user.id, "package.added", projectId, { code, role: me.role }),
  ]);
  return json({ code });
}

// PUT /api/projects/:id/packages/:code/upload/:name, the file as the body: one file of a package added on the site
async function putFile(request: Request, env: Env, projectId: string, code: string, encoded: string) {
  const row = await env.DB.prepare("SELECT uploaded_by AS byWhom, letter FROM package WHERE project_id = ? AND code = ?")
    .bind(projectId, code).first<{ byWhom: string | null; letter: string | null }>();
  if (!row) return json({ error: "No such package." }, 404);
  if (!row.byWhom) return json({ error: "This package came from the laptop: its files are added there." }, 403);
  if (row.letter) return json({ error: "RightFit has read this package already: a new revision is a new package." }, 409);
  let name: string;
  try {
    name = decodeURIComponent(encoded).trim();
  } catch {
    return json({ error: "That file name cannot be read." }, 400);
  }
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (!name || name.length > 200 || /[\\/]|\.\./.test(name) || name.startsWith(".") || !TYPES[ext]) {
    return json({ error: "A package holds the form and its attachments: PDF, Excel, Word or images." }, 400);
  }
  const body = await request.arrayBuffer();
  if (!body.byteLength) return json({ error: "That file is empty." }, 400);
  if (body.byteLength > MAX) return json({ error: "A file is at most 60 MB." }, 413);
  await env.BUCKET.put(`projects/${projectId}/packages/${code}/${name}`, body, { httpMetadata: { contentType: TYPES[ext] } });
  await env.DB.batch([
    env.DB.prepare("INSERT OR REPLACE INTO package_file (project_id, code, name, size, pages, sha) VALUES (?, ?, ?, ?, NULL, ?)")
      .bind(projectId, code, name, body.byteLength, await fingerprint(body)),
    env.DB.prepare("UPDATE package SET files = (SELECT COUNT(*) FROM package_file WHERE project_id = ? AND code = ?) WHERE project_id = ? AND code = ?")
      .bind(projectId, code, projectId, code),
  ]);
  return json({ name, size: body.byteLength });
}

// The first 16 characters of the file's SHA-256, as ingest/graph.py makes it on the laptop: the same file in two packages
const fingerprint = async (body: ArrayBuffer) =>
  [...new Uint8Array(await crypto.subtle.digest("SHA-256", body))].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
