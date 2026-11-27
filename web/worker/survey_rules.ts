// The practice survey (spec/features/survey.md): its questions in one place, the check of an answer, and the sums for
// the results page. No imports, so survey_rules.test.ts runs it with Node's own test runner; worker/survey.ts uses it.

export const SURVEY_VERSION = "2026-11-27";
export const COMMENT_MAX = 500;

export type Question =
  | { id: string; kind: "one"; text: string; options: [string, string][]; optional?: boolean; showIf?: [string, string[]] }
  | { id: string; kind: "many"; text: string; options: [string, string][]; optional?: boolean; max?: number }
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
  { id: "volume", kind: "one", text: "How many equipment submittals do you review or prepare in a typical month?",
    showIf: ["involvement", ["review", "prepare", "both"]], options: [
    ["1to5", "1 to 5"], ["6to15", "6 to 15"], ["16to40", "16 to 40"], ["gt40", "Over 40"], ["dont_know", "Don't know"]] },
  { id: "review_time", kind: "one", text: "How much of your own working time does reviewing one equipment submittal, such as a pump set, take? Count only the time you work on it, not the days it waits.",
    showIf: ["involvement", ["review", "both"]], options: [
    ["lt15", "Under 15 minutes"], ["15to30", "15 to 30 minutes"], ["30to60", "30 to 60 minutes"], ["1to2h", "1 to 2 hours"],
    ["2to4h", "2 to 4 hours"], ["gt4h", "Over 4 hours"], ["dont_know", "Don't know"]] },
  { id: "prepare_time", kind: "one", text: "How much of your own working time does preparing one equipment submittal, such as a pump set, take? Count only the time you work on it.",
    showIf: ["involvement", ["prepare", "both"]], options: [
    ["lt30", "Under 30 minutes"], ["30to60", "30 to 60 minutes"], ["1to2h", "1 to 2 hours"], ["2to4h", "2 to 4 hours"],
    ["4to8h", "Half a day to a day"], ["gt1d", "Over a day"], ["dont_know", "Don't know"]] },
  { id: "returned", kind: "number", text: "At the first submission, out of 10 submittals, how many get C (revise and resubmit)?", min: 0, max: 10, optional: true },
  { id: "rounds", kind: "one", text: "How many rounds does a submittal usually need until it is approved?", options: [
    ["1", "1 (approved the first time)"], ["2", "2"], ["3", "3"], ["4plus", "4 or more"], ["dont_know", "Don't know"]] },
  { id: "delay", kind: "one", text: "When a submittal is returned, how long does it usually delay the item?", options: [
    ["lt3d", "Under 3 days"], ["3to7d", "3 to 7 days"], ["1to2w", "1 to 2 weeks"], ["2to4w", "2 to 4 weeks"],
    ["gt1m", "Over a month"], ["dont_know", "Don't know"]] },
  { id: "reasons", kind: "many", max: 3, text: "The most common reasons a submittal is returned (choose up to 3)", options: [
    ["missing_docs", "Missing documents or certificates"], ["expired", "Expired or wrong certificate or declaration"],
    ["range_sheet", "Data sheet covers a range, not the exact model"], ["spec", "Data does not meet the specification"],
    ["size_fit", "Wrong size, or does not fit the space"], ["code", "Does not meet the code or regulations"],
    ["coordination", "Clashes with other approved items or trades"], ["wrong_model", "Wrong model or variant"],
    ["not_asked", "Not the brand or model the client or design asked for"], ["other", "Other"]] },
  { id: "site_misfit", kind: "one", text: "In your last 3 projects, did approved equipment turn out not to fit once it reached site (space, access or connections)?", options: [
    ["never", "Never"], ["once", "Once"], ["few", "A few times"], ["often", "Often"], ["na", "Not applicable"]] },
  { id: "misfit_cost", kind: "one", text: "If it happened: roughly what did fixing one such case cost?", optional: true,
    showIf: ["site_misfit", ["once", "few", "often"]], options: [
    ["lt1k", "Under €1,000"], ["1to5k", "€1,000 to €5,000"], ["5to20k", "€5,000 to €20,000"], ["20to100k", "€20,000 to €100,000"],
    ["gt100k", "Over €100,000"], ["dont_know", "Don't know"]] },
  { id: "useful_check", kind: "scale", text: "How useful would it be to have a submittal's documents and data checked before you review it?",
    min: 1, max: 5, labels: ["Not useful", "Very useful"] },
  { id: "useful_fit", kind: "scale", text: "How useful would it be to see, before approval, whether the equipment fits in the building model?",
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
      const picked = [...new Set(v as string[])];
      if (q.max !== undefined && picked.length > q.max) return `${q.text}: choose at most ${q.max}.`;
      out[q.id] = picked;
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

// ---- The live numbers at the top of the survey page (spec/features/survey.md §4) ----
// An answer is a range ("30 to 60 minutes"). To give an average, each range counts at its middle, in one unit. An open
// range ("Over 4 hours") counts at its lower bound, so an average that includes one is marked "at least". "Don't know"
// counts nowhere. These middles only turn people's ranges into one number; they are not data about equipment.
export const MIDDLES: Record<string, { title: string; unit: "minutes" | "days" | "euros" | "rounds"; values: Record<string, [number, boolean]> }> = {
  review_time: { title: "Reviewing one equipment submittal", unit: "minutes", values: {
    lt15: [7.5, false], "15to30": [22.5, false], "30to60": [45, false], "1to2h": [90, false], "2to4h": [180, false], gt4h: [240, true] } },
  prepare_time: { title: "Preparing one equipment submittal", unit: "minutes", values: {
    lt30: [15, false], "30to60": [45, false], "1to2h": [90, false], "2to4h": [180, false], "4to8h": [360, false], gt1d: [480, true] } },
  rounds: { title: "Rounds until a submittal is approved", unit: "rounds", values: {
    "1": [1, false], "2": [2, false], "3": [3, false], "4plus": [4, true] } },
  delay: { title: "Delay each time a submittal is returned", unit: "days", values: {
    lt3d: [1.5, false], "3to7d": [5, false], "1to2w": [10.5, false], "2to4w": [21, false], gt1m: [30, true] } },
  misfit_cost: { title: "Fixing equipment that did not fit on site, one case", unit: "euros", values: {
    lt1k: [500, false], "1to5k": [3000, false], "5to20k": [12500, false], "20to100k": [60000, false], gt100k: [100000, true] } },
};

// scale: the answers in order (without "Don't know"); lowIndex and highIndex: the lowest and highest chosen on it;
// meanAt: where the average falls on the same scale, between two answers' middles (for the drawing on the page)
export interface LiveRange {
  id: string; title: string; unit: string; answered: number; mean: number | null; atLeast: boolean; lowest: string | null; highest: string | null;
  scale: string[]; lowIndex: number | null; highIndex: number | null; meanAt: number | null;
}
// The two headline numbers. Time lost: for each person who gave both, the extra rounds (rounds until approval, minus
// the first) times the delay each return causes, in days. Money lost: the cost of fixing one case of approved
// equipment that did not fit on site. Both are worked out from people's own answers, never added to.
export interface Lost { answered: number; mean: number | null; atLeast: boolean; low: number | null; high: number | null }
export interface Live {
  n: number; lastDay: string | null;
  timeLost: Lost; moneyLost: Lost & { lowest: string | null; highest: string | null };
  ranges: LiveRange[];
  returned: { answered: number; mean: number | null; min: number | null; max: number | null };
  misfit: { answered: number; atLeastOnce: number };
  useful: { id: string; title: string; answered: number; mean: number | null }[];
  reasons: { label: string; n: number }[];
  roles: { label: string; n: number }[];
  results: QuestionResult[]; // every question's answers, counted (the fold-out under the live numbers); never the comments
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
const optionsOf = (id: string) => {
  const q = QUESTIONS.find((x) => x.id === id);
  return q && (q.kind === "one" || q.kind === "many") ? q.options : [];
};

// What everyone answered so far, as a few numbers. Never the comments, never one person's answers.
export function live(rows: { day: string; answers: Answers }[]): Live {
  const all = rows.map((r) => r.answers);
  const ranges = Object.entries(MIDDLES).map(([id, m]): LiveRange => {
    const opts = optionsOf(id).filter(([key]) => key in m.values);
    const picked = all.map((a) => a[id]).filter((v): v is string => typeof v === "string" && v in m.values);
    const order = picked.map((k) => opts.findIndex(([key]) => key === k)).sort((a, b) => a - b);
    const avg = mean(picked.map((k) => m.values[k][0]));
    const mids = opts.map(([key]) => m.values[key][0]);
    let meanAt: number | null = null;
    if (avg !== null) {
      meanAt = mids.length - 1;
      for (let i = 0; i < mids.length - 1; i++) {
        if (avg <= mids[i + 1]) { meanAt = i + Math.max(0, (avg - mids[i]) / (mids[i + 1] - mids[i])); break; }
      }
    }
    return {
      scale: opts.map(([, label]) => label), lowIndex: order.length ? order[0] : null, highIndex: order.length ? order[order.length - 1] : null, meanAt,
      id, title: m.title, unit: m.unit, answered: picked.length,
      mean: avg,
      atLeast: picked.some((k) => m.values[k][1]),
      lowest: order.length ? opts[order[0]][1] : null,
      highest: order.length ? opts[order[order.length - 1]][1] : null,
    };
  });
  const returned = all.map((a) => a.returned).filter((v): v is number => typeof v === "number");
  const misfit = all.map((a) => a.site_misfit).filter((v) => typeof v === "string" && v !== "na");
  const count = (id: string, top?: number) => {
    const flat = all.flatMap((a) => (Array.isArray(a[id]) ? (a[id] as string[]) : typeof a[id] === "string" ? [a[id] as string] : []));
    const list = optionsOf(id).map(([key, label]) => ({ label, n: flat.filter((x) => x === key).length })).filter((c) => c.n > 0);
    list.sort((a, b) => b.n - a.n);
    return top ? list.slice(0, top) : list;
  };
  const perPerson: [number, boolean][] = [];
  for (const a of all) {
    const r = MIDDLES.rounds.values[a.rounds as string], d = MIDDLES.delay.values[a.delay as string];
    if (r && d) perPerson.push([(r[0] - 1) * d[0], (r[1] && r[0] > 1) || (d[1] && r[0] > 1)]);
  }
  const days = perPerson.map(([x]) => x);
  const cost = all.map((a) => MIDDLES.misfit_cost.values[a.misfit_cost as string]).filter(Boolean);
  const money = ranges.find((x) => x.id === "misfit_cost")!;
  return {
    n: rows.length, lastDay: rows.length ? rows.map((r) => r.day).sort().at(-1)! : null,
    timeLost: { answered: days.length, mean: mean(days), atLeast: perPerson.some(([, open]) => open),
      low: days.length ? Math.min(...days) : null, high: days.length ? Math.max(...days) : null },
    moneyLost: { answered: cost.length, mean: mean(cost.map(([x]) => x)), atLeast: cost.some(([, open]) => open),
      low: cost.length ? Math.min(...cost.map(([x]) => x)) : null, high: cost.length ? Math.max(...cost.map(([x]) => x)) : null,
      lowest: money.lowest, highest: money.highest },
    ranges,
    returned: { answered: returned.length, mean: mean(returned), min: returned.length ? Math.min(...returned) : null, max: returned.length ? Math.max(...returned) : null },
    misfit: { answered: misfit.length, atLeastOnce: misfit.filter((v) => v !== "never").length },
    useful: [["useful_check", "A check of the documents and data before review"], ["useful_fit", "Seeing whether it fits in the building model"]].map(([id, title]) => {
      const xs = all.map((a) => a[id]).filter((v): v is number => typeof v === "number");
      return { id, title, answered: xs.length, mean: mean(xs) };
    }),
    reasons: count("reasons", 3),
    roles: count("role"),
    results: summarise(all),
  };
}
