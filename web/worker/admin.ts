// Management (spec/features/rightfit_online.md, section 12): the people who run RightFit see every account and
// project and can put things right. Only the accounts named in the ADMIN_EMAILS secret, and only with an address
// Google has verified: an email typed next to a password proves nothing. Every change made here is logged.
import { deleteAccount, json, logged, now, readBody, type Env, type User } from "./data";
import { isRole, ROLE_LABEL, type Role } from "./roles";

const LOG_DAYS = 365; // the activity log is kept 12 months, as the privacy policy says

// Routes under /api/admin/; the caller has already checked the account, the terms and isAdmin
export async function adminRoute(request: Request, env: Env, admin: User, path: string, method: string): Promise<Response> {
  if (path === "/api/admin/overview" && method === "GET") return overview(env);
  if (path === "/api/admin/people" && method === "GET") return people(env);
  if (path === "/api/admin/projects" && method === "GET") return projects(env);
  let m = path.match(/^\/api\/admin\/projects\/([\w-]+)$/);
  if (m && method === "GET") return project(env, m[1]);
  m = path.match(/^\/api\/admin\/projects\/([\w-]+)\/members\/([\w-]+)\/(role|remove)$/);
  if (m && method === "POST") return m[3] === "role" ? changeRole(request, env, admin, m[1], m[2]) : removeMember(env, admin, m[1], m[2]);
  m = path.match(/^\/api\/admin\/projects\/([\w-]+)\/delete$/);
  if (m && method === "POST") return deleteProject(request, env, admin, m[1]);
  m = path.match(/^\/api\/admin\/invitations\/([\w-]+)\/withdraw$/);
  if (m && method === "POST") return withdraw(env, admin, m[1]);
  m = path.match(/^\/api\/admin\/people\/([\w-]+)\/(sign-out|delete)$/);
  if (m && method === "POST") return m[2] === "sign-out" ? signOutEverywhere(env, admin, m[1]) : removePerson(env, admin, m[1]);
  return json({ error: "No such endpoint." }, 404);
}

// The latest events, with the names of the people and projects they mention
async function events(env: Env, projectId: string | null, limit: number) {
  const { results } = await env.DB.prepare(
    `SELECT e.id, e.at, e.action, e.detail, e.project_id AS projectId, p.name AS project, u.name AS actor, u.email AS actorEmail
       FROM event e LEFT JOIN "user" u ON u.id = e.actor LEFT JOIN project p ON p.id = e.project_id
      ${projectId ? "WHERE e.project_id = ?" : ""} ORDER BY e.id DESC LIMIT ${limit}`,
  ).bind(...(projectId ? [projectId] : [])).all<{ detail: string }>();
  return results.map((r) => ({ ...r, detail: JSON.parse(r.detail || "{}") as Record<string, unknown> }));
}

async function overview(env: Env) {
  const since = new Date(Date.now() - LOG_DAYS * 86_400_000).toISOString();
  const week = new Date(Date.now() - 7 * 86_400_000).toISOString();
  await env.DB.prepare("DELETE FROM event WHERE at < ?").bind(since).run(); // the log keeps 12 months
  const count = (sql: string, ...values: unknown[]) => env.DB.prepare(sql).bind(...values).first<{ n: number }>().then((r) => r?.n ?? 0);
  const [people, projects, pending, newPeople, google] = await Promise.all([
    count('SELECT COUNT(*) AS n FROM "user"'),
    count("SELECT COUNT(*) AS n FROM project"),
    count("SELECT COUNT(*) AS n FROM invitation WHERE state = 'pending' AND expires_at > ?", now()),
    count('SELECT COUNT(*) AS n FROM "user" WHERE "createdAt" > ?', week),
    count("SELECT COUNT(DISTINCT \"userId\") AS n FROM account WHERE \"providerId\" = 'google'"),
  ]);
  return json({ counts: { people, projects, pending, newPeople, google }, events: await events(env, null, 80) });
}

async function people(env: Env) {
  const { results } = await env.DB.prepare(
    `SELECT u.id, u.name, u.email, u."emailVerified" AS verified, u."createdAt" AS createdAt,
            (SELECT GROUP_CONCAT(a."providerId") FROM account a WHERE a."userId" = u.id) AS methods,
            (SELECT COUNT(*) FROM member m WHERE m.user_id = u.id) AS projects,
            (SELECT COUNT(*) FROM session s WHERE s."userId" = u.id AND s."expiresAt" > ?) AS sessions
       FROM "user" u ORDER BY u."createdAt" DESC`,
  ).bind(now()).all<{ verified: number; methods: string | null; createdAt: string | number }>();
  return json(results.map((r) => ({
    ...r,
    verified: Boolean(r.verified),
    methods: (r.methods ?? "").split(",").filter(Boolean).map((m) => (m === "credential" ? "password" : m)),
    createdAt: new Date(r.createdAt).toISOString(),
  })));
}

async function projects(env: Env) {
  const { results } = await env.DB.prepare(
    `SELECT p.id, p.name, p.country, p.created_at AS createdAt,
            (SELECT GROUP_CONCAT(u.name, ', ') FROM member c JOIN "user" u ON u.id = c.user_id WHERE c.project_id = p.id AND c.role = 'consultant') AS consultants,
            (SELECT COUNT(*) FROM member m WHERE m.project_id = p.id) AS people,
            (SELECT COUNT(*) FROM invitation i WHERE i.project_id = p.id AND i.state = 'pending' AND i.expires_at > ?) AS pending
       FROM project p ORDER BY p.created_at DESC`,
  ).bind(now()).all();
  return json(results);
}

async function project(env: Env, projectId: string) {
  const info = await env.DB.prepare(
    "SELECT id, name, country, created_at AS createdAt, dpa_version AS dpaVersion, dpa_accepted_at AS dpaAcceptedAt FROM project WHERE id = ?",
  ).bind(projectId).first();
  if (!info) return json({ error: "No such project." }, 404);
  const { results: team } = await env.DB.prepare(
    `SELECT m.id, m.role, m.company, m.invited_by AS invitedBy, m.joined_at AS joinedAt, u.id AS userId, u.name, u.email, u.image
       FROM member m JOIN "user" u ON u.id = m.user_id WHERE m.project_id = ? ORDER BY m.joined_at`,
  ).bind(projectId).all();
  const { results: invitations } = await env.DB.prepare(
    `SELECT id, email, role, company, invited_by AS invitedBy, created_at AS createdAt, expires_at AS expiresAt
       FROM invitation WHERE project_id = ? AND state = 'pending' ORDER BY created_at`,
  ).bind(projectId).all<{ expiresAt: string }>();
  const at = now();
  return json({
    project: info,
    people: team,
    invitations: invitations.map((i) => ({ ...i, expired: i.expiresAt <= at, mayWithdraw: true })),
    events: await events(env, projectId, 80),
  });
}

async function consultantsLeft(env: Env, projectId: string) {
  const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM member WHERE project_id = ? AND role = 'consultant'").bind(projectId).first<{ n: number }>();
  return row?.n ?? 0;
}

// POST .../members/<member>/role {role}: for example, make someone else the consultant before the first one leaves
async function changeRole(request: Request, env: Env, admin: User, projectId: string, memberId: string) {
  const role = (await readBody(request)).role;
  if (!isRole(role)) return json({ error: "Pick a role." }, 400);
  const target = await env.DB.prepare("SELECT id, role FROM member WHERE id = ? AND project_id = ?").bind(memberId, projectId).first<{ id: string; role: Role }>();
  if (!target) return json({ error: "No such person in this project." }, 404);
  if (target.role === role) return json({ ok: true });
  if (target.role === "consultant" && (await consultantsLeft(env, projectId)) <= 1) {
    return json({ error: "A project keeps at least one consultant: make someone else consultant first." }, 409);
  }
  await env.DB.batch([
    env.DB.prepare("UPDATE member SET role = ? WHERE id = ?").bind(role, memberId),
    logged(env, admin.id, "admin.role_changed", projectId, { member: memberId, from: ROLE_LABEL[target.role], to: ROLE_LABEL[role] }),
  ]);
  return json({ ok: true });
}

async function removeMember(env: Env, admin: User, projectId: string, memberId: string) {
  const target = await env.DB.prepare("SELECT id, role FROM member WHERE id = ? AND project_id = ?").bind(memberId, projectId).first<{ id: string; role: Role }>();
  if (!target) return json({ error: "No such person in this project." }, 404);
  if (target.role === "consultant" && (await consultantsLeft(env, projectId)) <= 1) {
    return json({ error: "A project keeps at least one consultant." }, 409);
  }
  await env.DB.batch([
    env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE invited_by = ? AND state = 'pending'").bind(memberId),
    env.DB.prepare("DELETE FROM member WHERE id = ?").bind(memberId),
    logged(env, admin.id, "admin.member_removed", projectId, { member: memberId, role: ROLE_LABEL[target.role] }),
  ]);
  return json({ ok: true });
}

// POST .../delete {name}: the project's name typed again, so a project never goes by a slip of the mouse
async function deleteProject(request: Request, env: Env, admin: User, projectId: string) {
  const info = await env.DB.prepare("SELECT name FROM project WHERE id = ?").bind(projectId).first<{ name: string }>();
  if (!info) return json({ error: "No such project." }, 404);
  if ((await readBody(request)).name !== info.name) return json({ error: "Type the project's name exactly to delete it." }, 400);
  await env.DB.batch([
    env.DB.prepare("DELETE FROM invitation WHERE project_id = ?").bind(projectId),
    env.DB.prepare("DELETE FROM member WHERE project_id = ?").bind(projectId),
    env.DB.prepare("DELETE FROM fit_run WHERE project_id = ?").bind(projectId),
    env.DB.prepare("DELETE FROM fit_choice WHERE project_id = ?").bind(projectId),
    env.DB.prepare("DELETE FROM revit_command WHERE project_id = ?").bind(projectId),
    env.DB.prepare("DELETE FROM project WHERE id = ?").bind(projectId),
    logged(env, admin.id, "admin.project_deleted", null, { project: projectId, name: info.name }),
  ]);
  return json({ ok: true });
}

async function withdraw(env: Env, admin: User, invitationId: string) {
  const inv = await env.DB.prepare("SELECT project_id FROM invitation WHERE id = ? AND state = 'pending'").bind(invitationId).first<{ project_id: string }>();
  if (!inv) return json({ error: "No such pending invitation." }, 404);
  await env.DB.batch([
    env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE id = ?").bind(invitationId),
    logged(env, admin.id, "admin.invitation_withdrawn", inv.project_id, { invitation: invitationId }),
  ]);
  return json({ ok: true });
}

async function signOutEverywhere(env: Env, admin: User, userId: string) {
  await env.DB.batch([
    env.DB.prepare('DELETE FROM session WHERE "userId" = ?').bind(userId),
    logged(env, admin.id, "admin.signed_out", null, { user: userId }),
  ]);
  return json({ ok: true });
}

async function removePerson(env: Env, admin: User, userId: string) {
  const exists = await env.DB.prepare('SELECT 1 AS yes FROM "user" WHERE id = ?').bind(userId).first();
  if (!exists) return json({ error: "No such account." }, 404);
  const handOver = await deleteAccount(env, userId, admin.id, "admin.account_deleted");
  if (handOver) return json({ error: `First make someone else a consultant of ${handOver.join(", ")}.` }, 409);
  return json({ ok: true });
}
