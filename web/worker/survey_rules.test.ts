// The practice survey's rules (survey_rules.ts). Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { COMMENT_MAX, QUESTIONS, checkAnswers, spread, summarise, toCsv } from "./survey_rules.ts";

const full = {
  role: "mep_reviewer", country: "RO", experience: "5to10", involvement: "review", volume: "6to15", review_time: "30to60",
  returned: 3, rounds: "2", delay: "1to2w", reasons: ["missing_docs", "size_fit"], site_misfit: "once", misfit_cost: "5to20k",
  useful_check: 4, useful_fit: 5, comment: "  Good   idea ",
};

test("a full answer is kept, cleaned", () => {
  const a = checkAnswers({ consent: true, answers: full });
  assert.ok(typeof a !== "string");
  assert.equal(a.comment, "Good idea");
  assert.deepEqual(a.reasons, ["missing_docs", "size_fit"]);
});

test("consent is required, and the robots' hidden field refuses the answer", () => {
  assert.equal(typeof checkAnswers({ answers: full }), "string");
  assert.equal(typeof checkAnswers({ consent: true, website: "spam.example", answers: full }), "string");
});

test("an answer outside the options, or a number out of range, is refused", () => {
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, role: "astronaut" } }), "string");
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, reasons: ["spec", "made_up"] } }), "string");
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, returned: 11 } }), "string");
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, useful_check: 2.5 } }), "string");
});

test("a required question can't be skipped, an optional one can", () => {
  const { role, ...noRole } = full;
  assert.ok(role);
  assert.equal(typeof checkAnswers({ consent: true, answers: noRole }), "string");
  const { returned, comment, ...noOptional } = full;
  assert.ok(returned !== undefined && comment);
  assert.equal(typeof checkAnswers({ consent: true, answers: noOptional }), "object");
});

test("the cost question is dropped for someone who never saw a misfit", () => {
  const a = checkAnswers({ consent: true, answers: { ...full, site_misfit: "never", misfit_cost: "gt100k" } });
  assert.ok(typeof a !== "string" && a.misfit_cost === undefined);
});

test("at most 3 reasons", () => {
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, reasons: ["spec", "code", "expired", "other"] } }), "string");
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, reasons: ["spec", "code", "expired"] } }), "object");
});

test("the time questions follow what the person does with submittals", () => {
  const reviewer = checkAnswers({ consent: true, answers: { ...full, prepare_time: "1to2h" } });
  assert.ok(typeof reviewer !== "string" && reviewer.prepare_time === undefined && reviewer.review_time === "30to60");
  assert.equal(typeof checkAnswers({ consent: true, answers: { ...full, involvement: "both" } }), "string"); // preparing time missing
  const both = checkAnswers({ consent: true, answers: { ...full, involvement: "both", prepare_time: "4to8h" } });
  assert.ok(typeof both !== "string" && both.prepare_time === "4to8h" && both.review_time === "30to60");
  const { volume, review_time, ...neither } = full;
  assert.ok(volume && review_time);
  const n = checkAnswers({ consent: true, answers: { ...neither, involvement: "neither" } });
  assert.ok(typeof n !== "string" && n.volume === undefined && n.review_time === undefined);
});

test("the comment is cut to 500 characters", () => {
  const a = checkAnswers({ consent: true, answers: { ...full, comment: "x".repeat(900) } });
  assert.ok(typeof a !== "string" && String(a.comment).length === COMMENT_MAX);
});

test("the median and the middle half", () => {
  assert.deepEqual(spread([]), { median: null, low: null, high: null });
  assert.deepEqual(spread([3]), { median: 3, low: 3, high: 3 });
  assert.equal(spread([1, 2, 3, 4]).median, 2.5);
  assert.deepEqual(spread([0, 1, 2, 3, 4, 5, 6, 7]), { median: 3.5, low: 1, high: 5 });
});

test("the results count each answer, and leave the comments out", () => {
  const a = checkAnswers({ consent: true, answers: full }) as Record<string, never>;
  const b = checkAnswers({ consent: true, answers: { ...full, role: "architect", returned: 5, reasons: ["size_fit"] } }) as Record<string, never>;
  const res = summarise([a, b]);
  const role = res.find((r) => r.id === "role")!;
  assert.equal(role.answered, 2);
  assert.equal(role.counts!.find((c) => c.key === "architect")!.n, 1);
  assert.equal(res.find((r) => r.id === "reasons")!.counts!.find((c) => c.key === "size_fit")!.n, 2);
  assert.equal(res.find((r) => r.id === "returned")!.spread!.median, 4);
  assert.ok(!res.some((r) => r.id === "comment"));
  assert.equal(res.length, QUESTIONS.length - 1);
});

test("the CSV has one row per answer, with quotes where needed", () => {
  const csv = toCsv([{ day: "2026-11-26", answers: { role: "architect", reasons: ["spec", "code"], comment: 'He said "no"' } }]);
  const [head, row] = csv.trim().split("\n");
  assert.ok(head.startsWith("day,role,country"));
  assert.ok(row.includes('"spec; code"') && row.includes('"He said ""no"""'));
});
