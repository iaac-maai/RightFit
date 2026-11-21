// The review of one package arranged the way the laptop's review page shows it (app/review/views/review.js):
// what is open product by product, what passed, and what the AI read, page by page. Plain functions, tested in
// review.test.ts. Every result and number comes from the laptop's checks; nothing here decides anything.
import type { AiFinding, CheckResult, Match, PackageReview, Reading, ReviewDoc, Value } from "./types";

export const STATUS_RULE: Record<string, string> = {
  A: "Every check passed or is only for information.",
  B: "Nothing sends the package back, but there is at least one problem or open question.",
  C: "A product has no data sheet that names it, or a blocking checklist item is missing.",
};

// What a rule rests on, in words (the same words as on the laptop)
export const RULE_STATUS: Record<string, string> = {
  verified_official: "read in the official journal",
  verified_secondary: "read in a copy of the text, still to check on the official one",
  to_confirm: "still to confirm on the official text",
  practice: "reviewers' practice",
  engineer_input: "a value set by the team's engineer",
  guidance: "a manufacturer's recommendation",
  checklist: "from past reviewers' comments",
  consultant: "the consultant's own rule, not the law",
};

export type Row = { kind: "result"; id: string; r: CheckResult } | { kind: "ai"; id: string; f: AiFinding };
export interface Group { id: string; name: string; model: string; rows: Row[] }

// Problems first, then questions, then what the reviewer marked not a problem; inside, in the answer's order
export function groups(v: PackageReview): Group[] {
  const rank = (r: CheckResult) => (r.dismissed ? 2 : r.verdict === "flag" ? 0 : 1);
  const open = v.results.filter((r) => r.dismissed || r.verdict === "flag" || r.verdict === "unclear")
    .sort((a, b) => rank(a) - rank(b) || (a.delta ?? 999) - (b.delta ?? 999));
  const of = (id: string) => open.filter((r) => (r.item ?? "package") === id).map((r): Row => ({ kind: "result", id: r.key, r }));
  return [
    ...v.items.map((i) => ({ id: i.id, name: i.name, model: i.model, rows: of(i.id) })),
    { id: "package", name: "Whole package", model: "", rows: of("package") },
    { id: "ai", name: "Suggested by the AI reviewer", model: "", rows: v.ai_findings.map((f): Row => ({ kind: "ai", id: `ai:${f.id}`, f })) },
  ].filter((g) => g.rows.length);
}

export const passed = (v: PackageReview) => v.results.filter((r) => !r.dismissed && (r.verdict === "pass" || r.verdict === "info"));

// Why the draft letter is what it is: each kind of problem or question once, with how many
export function why(v: PackageReview): string[] {
  if (v.status.letter === "C") return v.status.reasons;
  const counts = new Map<string, number>();
  for (const r of v.results) {
    if (r.dismissed || (r.verdict !== "flag" && r.verdict !== "unclear")) continue;
    const k = `${r.verdict === "flag" ? "Problem" : "Question"}: ${r.title}`;
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  const added = v.ai_findings.filter((f) => f.status === "accepted").length;
  if (added) counts.set("AI suggestion added to the answer", added);
  return [...counts].map(([k, n]) => (n > 1 ? `${k} (${n})` : k));
}

// Every reading, page by page of each document; the form's own values; and what was not found anywhere
export interface ReadingPage { page: number; values: Reading[]; matches: Match[] }
export function readingPages(v: PackageReview) {
  const has = (x: Reading) => x.value != null && x.value !== "";
  const values: Reading[] = v.items.flatMap((i) => i.values.map((x) => ({ ...x, item: i.id, product: i.name })));
  const files = new Set(v.documents.map((d) => d.file));
  const docs = v.documents.map((d: ReviewDoc) => {
    const here = values.filter((x) => x.source === d.file && has(x));
    const numbers = [...new Set([...here, ...d.matches].map((x) => Number(x.page)).filter((n) => n > 0))].sort((a, b) => a - b);
    return {
      d,
      pages: numbers.map((page): ReadingPage => ({
        page, values: here.filter((x) => Number(x.page) === page), matches: d.matches.filter((m) => Number(m.page) === page),
      })),
      loose: { values: here.filter((x) => !(Number(x.page) > 0)), matches: d.matches.filter((m) => !(Number(m.page) > 0)) },
    };
  });
  return { docs, form: values.filter((x) => has(x) && !files.has(x.source)), missing: values.filter((x) => !has(x)) };
}

// "file.pdf, p. 3" as a file and a page
export function parseSource(s: string) {
  const m = /^(.*), p\. (\S+)$/.exec(s);
  return m ? { file: m[1], page: Number(m[2]) || 1 } : { file: s, page: 1 };
}

// The page a problem points to: its first reading on a document, the document it is about, or its first source.
// A problem with no page of its own still opens a real page, the data sheet of its product, marked own: false.
export interface Place { file: string; page: number; own?: boolean }
export function placeOf(v: PackageReview, row: Row): Place | null {
  const isDoc = (file: string) => v.documents.some((d) => d.file === file);
  const e = (row.kind === "ai" ? row.f.evidence : row.r.evidence).find((x) => isDoc(x.source));
  if (e) return { file: e.source, page: Number(e.page) || 1 };
  if (row.kind === "result") {
    if (row.r.doc && isDoc(row.r.doc)) return { file: row.r.doc, page: 1 };
    const s = row.r.sources.map(parseSource).find((p) => isDoc(p.file));
    if (s) return s;
  }
  const item = row.kind === "result" ? row.r.item : null;
  const sheets = v.documents.filter((d) => d.type === "data sheet");
  const d = sheets.find((x) => x.matches.some((m) => m.item === item)) ?? sheets[0] ?? v.documents[0];
  return d ? { file: d.file, page: Number(d.matches.find((m) => m.item === item)?.page) || 1, own: false } : null;
}

export const shown = (value: Value, unit: string | null) =>
  value === true ? "yes" : value === false ? "no" : `${value}${unit ? ` ${unit}` : ""}`;

// A check's reason without the checklist's codes and register rows, and with words in place of field names
export const plainReason = (text: string) =>
  text.replace(/^CL-\d+\s+/, "").replace(/\s*\(register [^)]*\)/g, "").replace(/([a-z])_([a-z])/g, "$1 $2");
