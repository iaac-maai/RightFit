// The team password's cookie. Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { sameText, teamCookie, teamToken, teamUnlocked } from "./team.ts";

test("the cookie holds a hash of the password, never the password", async () => {
  const cookie = await teamCookie("a team password", true);
  assert.ok(!cookie.includes("a team password"));
  assert.match(cookie, /^rf_team=[a-f0-9]{64}; Path=\/; HttpOnly; SameSite=Lax; Max-Age=604800; Secure$/);
  assert.equal(await teamToken("a team password"), await teamToken("a team password"));
  assert.notEqual(await teamToken("a team password"), await teamToken("another one"));
});

test("only the cookie of the right password unlocks", async () => {
  const good = `session=x; rf_team=${await teamToken("right")}`;
  assert.ok(await teamUnlocked(good, "right"));
  assert.ok(!(await teamUnlocked(good, "changed since")));
  assert.ok(!(await teamUnlocked(`rf_team=${await teamToken("wrong")}`, "right")));
  assert.ok(!(await teamUnlocked(null, "right")));
});

test("with no team password set, nothing unlocks", async () => {
  assert.ok(!(await teamUnlocked(`rf_team=${await teamToken("")}`, undefined)));
  assert.ok(!(await teamUnlocked(`rf_team=${await teamToken("")}`, "")));
});

test("texts compare in full", () => {
  assert.ok(sameText("abc", "abc"));
  assert.ok(!sameText("abc", "abd"));
  assert.ok(!sameText("abc", "abcd"));
});
