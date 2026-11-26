// The Revit link's rules (revit_link.ts). Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  bearer, checkData, cleanUserCode, computerName, mayChoose, maySeeFitCheck, maySendData, maySendRun, newSecret, newUserCode,
  pngBytes, setsView, summariseRun, TOKEN_PREFIX,
} from "./revit_link.ts";
import { REVIEWERS, ROLES } from "./roles.ts";

test("a code has 8 letters and digits that can't be mixed up, in two groups", () => {
  for (let i = 0; i < 200; i++) {
    const code = newUserCode();
    assert.match(code, /^[A-HJKMNP-TW-Z2-9]{4}-[A-HJKMNP-TW-Z2-9]{4}$/);
    assert.ok(!/[01ILOUV]/.test(code));
  }
});

test("a code typed loosely is read back, anything else is refused", () => {
  assert.equal(cleanUserCode("abcd efgh"), "ABCD-EFGH");
  assert.equal(cleanUserCode("ABCD-EFGH"), "ABCD-EFGH");
  assert.equal(cleanUserCode("abcdefg"), "");
  assert.equal(cleanUserCode("ABCD-EFG0"), ""); // 0 is never in a code
  assert.equal(cleanUserCode(42), "");
});

test("a token is long, random and marked, and only the bearer header carries it", () => {
  const a = newSecret(TOKEN_PREFIX);
  const b = newSecret(TOKEN_PREFIX);
  assert.ok(a.startsWith("rfr_") && a.length >= 44);
  assert.notEqual(a, b);
  assert.equal(bearer(`Bearer ${a}`), a);
  assert.equal(bearer(a), null);
  assert.equal(bearer("Bearer abc"), null);
  assert.equal(bearer(null), null);
});

test("the computer's name is kept short and plain", () => {
  assert.equal(computerName("JEK <script>"), "JEK script");
  assert.equal(computerName(""), "A computer with Revit");
  assert.equal(computerName("x".repeat(100)).length, 60);
});

test("who sees, sends and chooses follows the roles of the forms", () => {
  for (const role of ROLES) {
    assert.equal(maySeeFitCheck(role), REVIEWERS.includes(role) || role === "contractor", role);
    assert.equal(maySendRun(role), maySeeFitCheck(role), role);
    assert.equal(mayChoose(role), REVIEWERS.includes(role), role);
  }
  assert.deepEqual(ROLES.filter(maySendData), ["consultant", "designer"]);
});

const run = {
  action: "check", set: { id: "set-a", maker: "Maker", model: "Booster XB", submitted: true }, room: { name: "B-01" },
  verdict: { verdict: "flag", confirmed: true }, results: [{ result: "pass" }, { result: "pass" }, { result: "flag" }],
  model_file: "Project1.rvt", ran_at: "2026-11-26T13:00:00",
};

test("a check from Revit is summed up for the list", () => {
  const s = summariseRun(run);
  assert.ok(typeof s !== "string");
  assert.equal(s.setLabel, "Maker Booster XB");
  assert.deepEqual(s.counts, { pass: 2, flag: 1 });
  assert.equal(s.confirmed, true);
  assert.equal(s.room, "B-01");
});

test("a check without its action, set, verdict or results is refused", () => {
  assert.equal(typeof summariseRun({ ...run, action: "delete" }), "string");
  assert.equal(typeof summariseRun({ ...run, set: {} }), "string");
  assert.equal(typeof summariseRun({ ...run, verdict: { verdict: "great" } }), "string");
  assert.equal(typeof summariseRun({ ...run, results: "all fine" }), "string");
});

test("only a PNG under 2 MB is kept as the picture", () => {
  const png = btoa(String.fromCharCode(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3));
  assert.ok(pngBytes(png) instanceof Uint8Array);
  assert.equal(pngBytes(undefined), null);
  assert.equal(typeof pngBytes(btoa("GIF89a....")), "string");
  assert.equal(typeof pngBytes("not base64 !!"), "string");
  assert.equal(typeof pngBytes("A".repeat(3_000_000)), "string");
});

test("the project data needs a list of sets, each with an id and a model", () => {
  assert.equal(typeof checkData({ candidates: { sets: [{ id: "a", model: "M" }] }, project: {} }), "object");
  assert.equal(typeof checkData({ candidates: {} }), "string");
  assert.equal(typeof checkData({ candidates: { sets: [{ id: "a" }] } }), "string");
  assert.equal(typeof checkData({ candidates: { sets: [] }, project: [] }), "string");
});

test("the page lists each set with the status of its values, extracted when not given", () => {
  const sets = setsView({ sets: [{ id: "a", maker: "M", model: "X", status: "verified", verified_by: "Luca", L: 1000 }, { id: "b", model: "Y" }] });
  assert.equal(sets[0].status, "verified");
  assert.equal(sets[0].verifiedBy, "Luca");
  assert.equal(sets[0].L, 1000);
  assert.equal(sets[1].status, "extracted");
  assert.equal(sets[1].kg, null);
  assert.deepEqual(setsView(null), []);
});
