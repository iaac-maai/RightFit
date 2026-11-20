// What the API's routes share: answering, reading a request, the database's members, the activity log and
// deleting an account (asked by the person, or by the people who run RightFit)
import type { AuthEnv } from "./auth";
import type { Role } from "./roles";

export interface Env extends AuthEnv {
  DB: D1Database;
  ASSETS: Fetcher;
  ADMIN_EMAILS?: string; // the accounts that may open Management: npx wrangler secret put ADMIN_EMAILS
}

export interface User { id: string; name: string; email: string; emailVerified: boolean; image?: string | null }
export interface MemberRow { id: string; project_id: string; user_id: string; role: Role; company: string; invited_by: string | null; joined_at: string }

export const json = (body: unknown, status = 200, headers?: HeadersInit) => Response.json(body, { status, headers });
export const now = () => new Date().toISOString();
export const newId = () => crypto.randomUUID();
export const text = (value: unknown, max: number) => (typeof value === "string" ? value.trim().slice(0, max) : "");

export async function readBody(request: Request): Promise<Record<string, unknown>> {
  try {
    const value = await request.json();
    return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export async function sha256(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function membership(env: Env, projectId: string, userId: string) {
  return env.DB.prepare("SELECT * FROM member WHERE project_id = ? AND user_id = ?").bind(projectId, userId).first<MemberRow>();
}

// One line in the activity log, as a statement to run alone or inside a batch. It names people by user id only.
export function logged(env: Env, actor: string | null, action: string, projectId: string | null = null, detail: Record<string, unknown> = {}) {
  return env.DB.prepare("INSERT INTO event (at, actor, project_id, action, detail) VALUES (?, ?, ?, ?, ?)")
    .bind(now(), actor, projectId, action, JSON.stringify(detail));
}

// Delete an account: the person, their sessions, sign-in links, consent and memberships. A project they run alone with
// other people in it must go to another consultant first; a project with nobody else in it goes too.
// Returns the names of the projects to hand over first, or null once the account is gone.
export async function deleteAccount(env: Env, userId: string, by: string, action: string): Promise<string[] | null> {
  const { results: run } = await env.DB.prepare(
    `SELECT p.id, p.name,
            (SELECT COUNT(*) FROM member c WHERE c.project_id = p.id AND c.role = 'consultant') AS consultants,
            (SELECT COUNT(*) FROM member o WHERE o.project_id = p.id) AS people
       FROM member m JOIN project p ON p.id = m.project_id
      WHERE m.user_id = ? AND m.role = 'consultant'`,
  ).bind(userId).all<{ id: string; name: string; consultants: number; people: number }>();
  const handOver = run.filter((p) => p.consultants === 1 && p.people > 1);
  if (handOver.length) return handOver.map((p) => p.name);
  const alone = run.filter((p) => p.people === 1).map((p) => p.id);
  await env.DB.batch([
    ...alone.flatMap((id) => [
      env.DB.prepare("DELETE FROM invitation WHERE project_id = ?").bind(id),
      env.DB.prepare("DELETE FROM member WHERE project_id = ?").bind(id),
      env.DB.prepare("DELETE FROM project WHERE id = ?").bind(id),
    ]),
    env.DB.prepare("UPDATE invitation SET state = 'withdrawn' WHERE state = 'pending' AND invited_by IN (SELECT id FROM member WHERE user_id = ?)").bind(userId),
    env.DB.prepare("DELETE FROM member WHERE user_id = ?").bind(userId),
    env.DB.prepare('DELETE FROM consent WHERE "userId" = ?').bind(userId),
    env.DB.prepare('DELETE FROM session WHERE "userId" = ?').bind(userId),
    env.DB.prepare('DELETE FROM account WHERE "userId" = ?').bind(userId),
    env.DB.prepare('DELETE FROM "user" WHERE id = ?').bind(userId),
    logged(env, by, action, null, { user: userId, projectsDeleted: alone.length }),
  ]);
  return null;
}
