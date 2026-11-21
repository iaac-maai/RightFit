// Tests for how a package's review is arranged on the page. Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { csv, groups, notAProblem, passed, placeOf, readingPages, why } from "./review.ts";
import type { CheckResult, PackageReview } from "./types.ts";

// A made-up package: one pump, one data sheet, a problem, a question, a finding marked not a problem, a pass
const result = (over: Partial<CheckResult>): CheckResult => ({
  key: "k", check: "V1", check_name: "Duty point", title: "Duty point", item: "pump", product: "Pump (X1)", doc: null,
  verdict: "pass", confirmed: false, reason: "", sources: [], rules: [], blocking: false, comment: null, delta: null,
  dismissed: null, evidence: [], ...over,
});
const view: PackageReview = {
  review: "2026-03-16", delivery: "2026-05-11", location: "RO", form: { form_no: "IS 015", revision: 0 },
  status: { letter: "B", label: "Approved as noted", reasons: [] },
  counts: { problems: 1, questions: 1, passed: 0, would_pass: 1, to_confirm: 3, readings: 3 },
  items: [{ id: "pump", name: "Pump", model: "X1", values: [
    { key: "flow", what: "Flow", value: 12, unit: "m3/h", source: "sheet.pdf", page: 2, quote: "12", status: "extracted" },
    { key: "used_for", what: "Used for (form)", value: "booster", unit: null, source: "form.xls", page: null, quote: null, status: "verified" },
    { key: "power", what: "Motor power", value: null, unit: null, source: "", page: null, quote: null, status: "unclear" },
  ] }],
  documents: [{ no: 1, file: "sheet.pdf", type: "data sheet", listed_as: "fisa", covers: [], pages: 4, status: "extracted",
    matches: [{ item: "pump", product: "Pump (X1)", kind: "names the model", page: 1, quote: "X1", status: "extracted" }] }],
  results: [
    result({ key: "q", verdict: "unclear", title: "Pressure rating", delta: 2 }),
    result({ key: "off", verdict: "flag", title: "Ecodesign", dismissed: "agreed on site" }),
    result({ key: "p", verdict: "flag", title: "Duty point", delta: 1, evidence: [
      { item: "pump", key: "flow", what: "Flow", value: 12, unit: "m3/h", source: "sheet.pdf", page: 2, quote: "12", status: "extracted" }] }),
    result({ key: "ok", verdict: "pass", item: null }),
  ],
  ai_findings: [{ id: "a1", title: "Noise", finding: "No noise level", suggested_comment: "State it", status: "suggested", note: null, evidence: [] }],
  notes: [], answer: { lines: [], text: "" }, decisions: {},
};

test("open results go under their product: problems, then questions, then those marked not a problem", () => {
  const g = groups(view);
  assert.deepEqual(g.map((x) => x.id), ["pump", "ai"]);   // the whole package has nothing open, so it is left out
  assert.deepEqual(g[0].rows.map((r) => r.id), ["p", "q", "off"]);
  assert.deepEqual(passed(view).map((r) => r.key), ["ok"]);
});

test("why the letter is B counts what is still open, never what was marked not a problem", () => {
  assert.deepEqual(why(view), ["Question: Pressure rating", "Problem: Duty point"]);   // in the order the checks ran
});

test("readings sit on their document's page; the form's own and the missing ones apart", () => {
  const { docs, form, missing } = readingPages(view);
  assert.deepEqual(docs[0].pages.map((p) => [p.page, p.values.length, p.matches.length]), [[1, 0, 1], [2, 1, 0]]);
  assert.deepEqual(form.map((x) => x.key), ["used_for"]);
  assert.deepEqual(missing.map((x) => x.key), ["power"]);
});

test("a problem opens the page its reading came from", () => {
  const row = groups(view)[0].rows[0];
  assert.deepEqual(placeOf(view, row), { file: "sheet.pdf", page: 2, quotes: [{ file: "sheet.pdf", page: 2, quote: "12", ok: false }] });
});

test("the downloads write what a spreadsheet reads back, commas and quotes included", () => {
  assert.equal(csv([["a", "b, c"], ['say "x"', null]]), 'a,"b, c"\n"say ""x""",\n');
  assert.equal(notAProblem(view), "check,about,why\nV1,Pump (X1),agreed on site\n");
});
