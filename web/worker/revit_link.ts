// The Revit link's rules (spec/features/revit_link.md): the short code, the secrets, the bearer header, who may do
// what with the fit check, and what a check sent from Revit may hold. No imports, so revit_link.test.ts runs it with
// Node's own test runner; worker/revit.ts uses it with the database.

export const LINK_MINUTES = 10; // a link waits this long for its approval
export const POLL_SECONDS = 3; // how often Revit asks whether it was approved
export const TOKEN_PREFIX = "rfr_"; // a Revit token, so it is recognised wherever it is pasted
export const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
export const MAX_RUN_BYTES = 256 * 1024; // a check without its picture
export const MAX_DATA_BYTES = 512 * 1024; // candidates.json and project.json together

type Role = "consultant" | "designer" | "site_supervisor" | "client" | "contractor" | "subcontractor";
const REVIEWERS: readonly Role[] = ["consultant", "designer", "site_supervisor", "client"]; // as in roles.ts

// Who sees the fit check: those who see the forms (subcontractors wait for their branch, as for the forms)
export const maySeeFitCheck = (role: Role) => REVIEWERS.includes(role) || role === "contractor";
// Who sends a check from Revit: anyone who sees it (the architect, the MEP designer, the contractor's BIM people)
export const maySendRun = maySeeFitCheck;
// Who sends the project's pump sets and settings: the consultant (Luca confirms the values) and the designer
export const maySendData = (role: Role) => role === "consultant" || role === "designer";
// Who marks the chosen set: the reviewers, as they answer the forms
export const mayChoose = (role: Role) => REVIEWERS.includes(role);

// The code a person types or checks on the site: 8 letters and digits with none that look alike (no 0/O, 1/I/L, U/V)
const ALPHABET = "ABCDEFGHJKMNPQRSTWXYZ23456789";
export function newUserCode(random: Uint8Array = crypto.getRandomValues(new Uint8Array(8))) {
  let code = "";
  for (let i = 0; i < 8; i++) code += ALPHABET[random[i] % ALPHABET.length];
  return `${code.slice(0, 4)}-${code.slice(4)}`;
}

// A code as a person may type it (lower case, spaces, no dash) back to ABCD-EFGH, or "" when it can't be one
export function cleanUserCode(value: unknown) {
  if (typeof value !== "string") return "";
  const plain = value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (plain.length !== 8 || [...plain].some((c) => !ALPHABET.includes(c))) return "";
  return `${plain.slice(0, 4)}-${plain.slice(4)}`;
}

// A long secret, written with the letters a URL allows
export function newSecret(prefix = "") {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return prefix + btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// The token in "Authorization: Bearer rfr_...", or null
export function bearer(header: string | null) {
  const m = (header ?? "").match(/^Bearer\s+(rfr_[A-Za-z0-9_-]{40,60})\s*$/);
  return m ? m[1] : null;
}

// The computer's name as Revit sends it, kept short and plain
export function computerName(value: unknown) {
  const name = typeof value === "string" ? value.replace(/[^\p{L}\p{N} ._()-]/gu, "").trim().slice(0, 60) : "";
  return name || "A computer with Revit";
}

const ACTIONS = ["check", "preview", "swap"] as const;
const VERDICTS = ["pass", "would pass", "flag", "FAIL", "unclear"] as const;
const str = (v: unknown, max: number) => (typeof v === "string" ? v.slice(0, max) : "");
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);

export interface RunSummary {
  action: (typeof ACTIONS)[number]; setId: string; setLabel: string; submitted: boolean; verdict: string; confirmed: boolean;
  room: string; model: string; ranAt: string; counts: Record<string, number>;
}

// What a check from Revit must hold before the site keeps it: an action, a set, a verdict, a list of results. Returns
// the short summary that goes in D1 (the whole check goes to the private bucket as sent), or the reason it can't.
export function summariseRun(body: Record<string, unknown>): RunSummary | string {
  const action = body.action;
  if (!ACTIONS.includes(action as never)) return "A check says whether it is a check, a preview or a swap.";
  const set = (body.set ?? {}) as Record<string, unknown>;
  const setLabel = `${str(set.maker, 80)} ${str(set.model, 120)}`.trim();
  if (!setLabel) return "A check names its pump set.";
  const verdict = (body.verdict ?? {}) as Record<string, unknown>;
  if (!VERDICTS.includes(verdict.verdict as never)) return "A check has a verdict.";
  if (!Array.isArray(body.results)) return "A check lists its results.";
  const counts: Record<string, number> = {};
  for (const r of body.results.slice(0, 50) as Record<string, unknown>[]) {
    const key = str(r?.result, 20) || "unclear";
    counts[key] = (counts[key] ?? 0) + 1;
  }
  const room = (body.room ?? {}) as Record<string, unknown>;
  return {
    action: action as RunSummary["action"], setId: str(set.id, 120), setLabel, submitted: set.submitted === true,
    verdict: verdict.verdict as string, confirmed: verdict.confirmed === true, room: str(room.name, 80),
    model: str(body.model_file, 160), ranAt: str(body.ran_at, 40), counts,
  };
}

// A PNG sent as base64: its bytes, or a reason it can't be kept
export function pngBytes(value: unknown): Uint8Array | string | null {
  if (value === undefined || value === null || value === "") return null;
  if (typeof value !== "string" || value.length > Math.ceil((MAX_IMAGE_BYTES * 4) / 3) + 4) return "The picture is too large (2 MB at most).";
  let bytes: Uint8Array;
  try {
    bytes = Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
  } catch {
    return "The picture is not a PNG.";
  }
  const sign = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  if (bytes.length < 8 || sign.some((b, i) => bytes[i] !== b)) return "The picture is not a PNG.";
  return bytes;
}

// The project's pump sets and settings as Revit sends them: candidates.json must hold a list of sets with an id, a
// maker and a model; project.json is an object. Returns the cleaned pair, or the reason.
export function checkData(body: Record<string, unknown>): { candidates: { sets: unknown[] }; project: Record<string, unknown> } | string {
  const c = body.candidates as { sets?: unknown } | undefined;
  if (!c || typeof c !== "object" || !Array.isArray(c.sets)) return "Send candidates.json with its list of sets.";
  if (c.sets.length > 200) return "At most 200 pump sets.";
  for (const s of c.sets as Record<string, unknown>[]) {
    if (!s || typeof s !== "object" || !str(s.id, 200) || !str(s.model, 200)) return "Every set has an id and a model.";
  }
  const p = body.project ?? {};
  if (typeof p !== "object" || Array.isArray(p)) return "project.json is an object.";
  return { candidates: c as { sets: unknown[] }, project: p as Record<string, unknown> };
}

// The sets as the Fit check page lists them: who they are and the status of their values, nothing else
export function setsView(candidates: { sets?: unknown[] } | null) {
  return ((candidates?.sets ?? []) as Record<string, unknown>[]).map((s) => ({
    id: str(s.id, 200), maker: str(s.maker, 80), model: str(s.model, 200), submitted: s.submitted === true,
    status: str(s.status, 20) || "extracted", verifiedBy: str(s.verified_by, 80), verifiedOn: str(s.verified_on, 20),
    L: num(s.L), W: num(s.W), H: num(s.H), kg: num(s.kg), pumps: num(s.pumps),
  }));
}

// ---- From the site to Revit (spec/features/revit_link.md §9) ----------------------------------------------------------

export const COMMAND_SECONDS = 120; // a message waits this long for Revit
export const LISTEN_SECONDS = 4; // how often Revit asks for a message

// Whether a message sent at createdAt still waits at now (both ISO times)
export function commandFresh(createdAt: string, now: string) {
  return new Date(now).getTime() - new Date(createdAt).getTime() < COMMAND_SECONDS * 1000;
}

// Who may send a message to their own Revit: anyone who sees the fit check (it moves only their own Revit, and only
// draws a preview there)
export const mayAskRevit = maySeeFitCheck;

// What the page shows for a message's state
export function commandText(state: string, message: string) {
  if (state === "waiting") return "Waiting for your Revit…";
  if (state === "taken") return "Revit is drawing it…";
  if (state === "done") return message || "Shown in Revit.";
  if (state === "failed") return message || "Revit could not show it.";
  return "Revit did not answer: is it open, linked (RightFit › Online), with this project's folder linked?";
}
