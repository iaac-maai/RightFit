// The practice survey (spec/features/survey.md): its questions in one place, the check of an answer, and the sums for
// the results page. No imports, so survey_rules.test.ts runs it with Node's own test runner; worker/survey.ts uses it.

export const SURVEY_VERSION = "2026-11-26";
export const COMMENT_MAX = 500;

export type Question =
  | { id: string; kind: "one"; text: string; options: [string, string][]; optional?: boolean; showIf?: [string, string[]] }
  | { id: string; kind: "many"; text: string; options: [string, string][]; optional?: boolean }
  | { id: string; kind: "number"; text: string; min: number; max: number; optional?: boolean }
  | { id: string; kind: "scale"; text: string; min: number; max: number; labels: [string, string]; optional?: boolean }
  | { id: string; kind: "text"; text: string; optional: true; hint: string };

export const QUESTIONS: Question[] = [
  { id: "role", kind: "one", text: "Your role", options: [
    ["mep_reviewer", "MEP engineer who reviews submittals (consultant, supervisor)"], ["mep_designer", "MEP designer"],
    ["architect", "Architect"], ["contractor", "Main contractor"], ["subcontractor", "Subcontractor or supplier"],
    ["client", "Client or project manager"], ["other", "Other"]] },
  { id: "country", kind: "one", text: "Where you mostly work", options: [
    ["ES", "Spain"], ["RO", "Romania"], ["LB", "Lebanon"], ["FR", "France"], ["IT", "Italy"], ["UK", "United Kingdom"],
    ["europe", "Elsewhere in Europe"], ["middle_east", "Middle East"], ["elsewhere", "Elsewhere"]] },
  { id: "experience", kind: "one", text: "Years in the industry", options: [
    ["lt2", "Under 2"], ["2to5", "2 to 5"], ["5to10", "5 to 10"], ["gt10", "Over 10"]] },
  { id: "involvement", kind: "one", text: "With material approval forms (submittals), you…", options: [
    ["review", "Review them"], ["prepare", "Prepare them"], ["both", "Both"], ["neither", "Neither"]] },
  { id: "review_time", kind: "one", text: "How long does it take to review one equipment submittal, such as a pump set, from opening it to the answer?", options: [
    ["lt15", "Under 15 minutes"], ["15to30", "15 to 30 minutes"], ["30to60", "30 to 60 minutes"], ["1to2h", "1 to 2 hours"],
    ["2to4h", "2 to 4 hours"], ["gt4h", "Over 4 hours"], ["dont_know", "Don't know"]] },
  { id: "returned", kind: "number", text: "Out of 10 submittals, how many are returned for corrections or resubmission?", min: 0, max: 10, optional: true },
  { id: "delay", kind: "one", text: "When a submittal is returned, how long does it usually delay the item?", options: [
    ["lt3d", "Under 3 days"], ["3to7d", "3 to 7 days"], ["1to2w", "1 to 2 weeks"], ["2to4w", "2 to 4 weeks"],
    ["gt1m", "Over a month"], ["dont_know", "Don't know"]] },
  { id: "reasons", kind: "many", text: "The most common reasons a submittal is returned (choose any)", options: [
    ["missing_docs", "Missing documents or certificates"], ["spec", "Data does not meet the specification"],
    ["size_fit", "Wrong size, or does not fit the space"], ["code", "Does not meet the code or regulations"],
    ["coordination", "Clashes with other approved items or trades"], ["wrong_model", "Wrong model or variant"], ["other", "Other"]] },
  { id: "site_misfit", kind: "one", text: "Have you seen approved equipment that did not fit or work once it reached site?", options: [
    ["never", "Never"], ["once", "Once"], ["few", "A few times"], ["often", "Often"]] },
  { id: "misfit_cost", kind: "one", text: "If it happened: roughly what did fixing one such case cost?", optional: true,
    showIf: ["site_misfit", ["once", "few", "often"]], options: [
    ["lt1k", "Under €1,000"], ["1to5k", "€1,000 to €5,000"], ["5to20k", "€5,000 to €20,000"], ["20to100k", "€20,000 to €100,000"],
    ["gt100k", "Over €100,000"], ["dont_know", "Don't know"]] },
  { id: "useful", kind: "scale", text: "How useful would a tool be that checks a submittal before review and shows whether the equipment fits in the building model?",
    min: 1, max: 5, labels: ["Not useful", "Very useful"] },
  { id: "comment", kind: "text", text: "Anything else?", optional: true, hint: "Please don't write the names of people or companies." },
];

export const CONSENT = "I am 18 or older and agree that my anonymous answers are used for RightFit, a student project at IAAC, Barcelona. " +
  "No name, email, company or IP address is collected.";

export type Answers = Record<string, string | string[] | number>;

// An answer as the page sends it, checked against the questions: the cleaned answers, or the reason it can't be kept
export function checkAnswers(body: Record<string, unknown>): Answers | string {
  if (typeof body.website === "string" && body.website.trim()) return "Not kept."; // the hidden field only robots fill in
  if (body.consent !== true) return "Please tick the consent box to send your answers.";
  const given = (body.answers ?? {}) as Record<string, unknown>;
  if (typeof given !== "object" || Array.isArray(given)) return "Send the answers.";
  const out: Answers = {};
  for (const q of QUESTIONS) {
    const v = given[q.id];
    const empty = v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
    const shown = q.kind !== "one" || !q.showIf || (q.showIf[1] as string[]).includes(String(out[q.showIf[0]] ?? ""));
    if (!shown) continue; // a follow-up the person never saw
    if (empty) {
      if (q.optional) continue;
      return `Please answer: ${q.text}`;
    }
    if (q.kind === "one") {
      if (typeof v !== "string" || !q.options.some(([k]) => k === v)) return `That is not one of the answers to: ${q.text}`;
      out[q.id] = v;
    } else if (q.kind === "many") {
      if (!Array.isArray(v) || v.some((x) => typeof x !== "string" || !q.options.some(([k]) => k === x))) return `That is not one of the answers to: ${q.text}`;
      out[q.id] = [...new Set(v as string[])];
    } else if (q.kind === "number" || q.kind === "scale") {
      const n = typeof v === "number" ? v : Number(v);
      if (!Number.isInteger(n) || n < q.min || n > q.max) return `${q.text}: a whole number from ${q.min} to ${q.max}.`;
      out[q.id] = n;
    } else {
      if (typeof v !== "string") return `${q.text}: text only.`;
      const t = v.replace(/\s+/g, " ").trim().slice(0, COMMENT_MAX);
      if (t) out[q.id] = t;
    }
  }
  return out;
}

// The median and the middle half of a list of numbers (nearest rank), or nulls when there are none
export function spread(values: number[]) {
  const s = [...values].sort((a, b) => a - b);
  if (!s.length) return { median: null, low: null, high: null };
  const at = (p: number) => s[Math.min(s.length - 1, Math.max(0, Math.ceil(p * s.length) - 1))];
  const mid = s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
  return { median: mid, low: at(0.25), high: at(0.75) };
}

export interface QuestionResult {
  id: string; text: string; kind: Question["kind"]; answered: number;
  counts?: { key: string; label: string; n: number }[]; spread?: ReturnType<typeof spread>;
}

// The results: for each question, how many answered it and how they answered. Comments are left out here.
export function summarise(rows: Answers[]): QuestionResult[] {
  return QUESTIONS.filter((q) => q.kind !== "text").map((q) => {
    const given = rows.map((r) => r[q.id]).filter((v) => v !== undefined);
    const base = { id: q.id, text: q.text, kind: q.kind, answered: given.length };
    if (q.kind === "one" || q.kind === "many") {
      const flat = given.flatMap((v) => (Array.isArray(v) ? v : [v]));
      return { ...base, counts: q.options.map(([key, label]) => ({ key, label, n: flat.filter((x) => x === key).length })) };
    }
    if (q.kind === "scale" || q.kind === "number") {
      const nums = given.filter((v): v is number => typeof v === "number");
      const counts = [];
      for (let i = q.min; i <= q.max; i++) counts.push({ key: String(i), label: String(i), n: nums.filter((x) => x === i).length });
      return { ...base, counts, spread: spread(nums) };
    }
    return base;
  });
}

// Every answer as CSV, one row per person, for the admins
export function toCsv(rows: { day: string; answers: Answers }[]) {
  const ids = QUESTIONS.map((q) => q.id);
  const cell = (v: unknown) => {
    const s = Array.isArray(v) ? v.join("; ") : v === undefined ? "" : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [["day", ...ids].join(","), ...rows.map((r) => [r.day, ...ids.map((id) => cell(r.answers[id]))].join(","))].join("\n") + "\n";
}
