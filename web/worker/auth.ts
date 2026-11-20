// Accounts, with Better Auth inside the Worker: people, sessions and Google links live in D1, and the browser keeps
// only a session cookie. The same set-up as the app of the AI Methods hackathon.
import { betterAuth } from "better-auth";

export interface AuthEnv {
  DB: D1Database;
  BETTER_AUTH_SECRET: string; // signs the session cookie: npx wrangler secret put BETTER_AUTH_SECRET
  GOOGLE_CLIENT_ID?: string; // optional: "Continue with Google" shows only when both are set
  GOOGLE_CLIENT_SECRET?: string;
}

// Passwords: a random salt per person and PBKDF2-SHA256 from the Worker's Web Crypto (Argon2id, the first choice of
// OWASP, is not in Web Crypto). 100,000 rounds took 9.6 ms on a laptop, at the edge of the 10 ms of CPU a request
// gets on the free plan, so we use 50,000 (about 5 ms). Each hash keeps its rounds, so this can go up later.
// shortcut: 50,000 rounds is below the OWASP 600,000 for PBKDF2-SHA256, raise it on a paid plan
const ROUNDS = 50_000;
const encoder = new TextEncoder();
const toBase64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const fromBase64 = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

async function pbkdf2(password: string, salt: Uint8Array, rounds: number) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(password), "PBKDF2", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: rounds }, key, 256));
}

export async function hashPassword(password: string) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return `pbkdf2-sha256$${ROUNDS}$${toBase64(salt)}$${toBase64(await pbkdf2(password, salt, ROUNDS))}`;
}

export async function verifyPassword({ hash, password }: { hash: string; password: string }) {
  const [scheme, rounds, salt, stored] = hash.split("$");
  if (scheme !== "pbkdf2-sha256") return false;
  const expected = fromBase64(stored);
  const actual = await pbkdf2(password, fromBase64(salt), Number(rounds));
  let difference = expected.length ^ actual.length; // compare every byte, so the time does not tell how many matched
  for (let i = 0; i < actual.length; i++) difference |= actual[i] ^ (expected[i] ?? 0);
  return difference === 0;
}

export const googleOn = (env: AuthEnv) => Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET);

export function makeAuth(env: AuthEnv, origin: string) {
  return betterAuth({
    database: env.DB,
    secret: env.BETTER_AUTH_SECRET,
    baseURL: origin,
    basePath: "/api/auth",
    trustedOrigins: [origin],
    telemetry: { enabled: false },
    emailAndPassword: {
      enabled: true,
      minPasswordLength: 10,
      password: { hash: hashPassword, verify: verifyPassword },
    },
    socialProviders: googleOn(env)
      ? { google: { clientId: env.GOOGLE_CLIENT_ID!, clientSecret: env.GOOGLE_CLIENT_SECRET!, prompt: "select_account" as const } }
      : undefined,
    account: { encryptOAuthTokens: true }, // the tokens Google gives are kept encrypted; the app never uses them
    session: { expiresIn: 60 * 60 * 24 * 7, updateAge: 60 * 60 * 24 }, // 7 days, renewed once a day while used
    // shortcut: the limiter's memory lives in one Worker instance, a D1 table would hold it across instances
    rateLimit: { enabled: true, window: 60, max: 20 },
  });
}
