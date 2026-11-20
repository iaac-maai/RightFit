// The team password of a locked project (spec/features/rightfit_online.md, section 11): the project's real data opens
// only for its members who also know it. The cookie holds a hash of the password, never the password itself.
// No imports, so team.test.ts runs it with Node's own test runner.

const TEAM_COOKIE = "rf_team";

export async function teamToken(password: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`rightfit-team:${password}`));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Compare every character, so the time taken does not tell how much of a guess was right
export function sameText(a: string, b: string) {
  let difference = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) difference |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return difference === 0;
}

export async function teamUnlocked(cookieHeader: string | null, password: string | undefined) {
  if (!password) return false; // no team password set: a locked project stays locked
  const sent = (cookieHeader ?? "").match(new RegExp(`(?:^|;\\s*)${TEAM_COOKIE}=([a-f0-9]{64})`))?.[1];
  return Boolean(sent) && sameText(sent!, await teamToken(password));
}

export async function teamCookie(password: string, secure: boolean) {
  // HttpOnly: the page's scripts can't read it; SameSite=Lax: other sites can't use it; 7 days, like the session
  return `${TEAM_COOKIE}=${await teamToken(password)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800${secure ? "; Secure" : ""}`;
}
