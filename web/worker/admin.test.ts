// Who may open Management. Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { adminList, isAdmin } from "./roles.ts";

const LIST = " Lead@Example.test, second@example.test ,";

test("the list is read loosely: spaces, capitals and empty entries don't matter", () => {
  assert.deepEqual([...adminList(LIST)], ["lead@example.test", "second@example.test"]);
  assert.equal(adminList(undefined).size, 0);
});

test("an address on the list, verified by Google, opens Management", () => {
  assert.ok(isAdmin({ email: "lead@example.test", emailVerified: true }, LIST));
  assert.ok(isAdmin({ email: "SECOND@example.test", emailVerified: true }, LIST));
});

test("the same address typed with a password does not", () => {
  assert.ok(!isAdmin({ email: "lead@example.test", emailVerified: false }, LIST));
});

test("an address that is not on the list does not, and no list means no admin", () => {
  assert.ok(!isAdmin({ email: "someone@example.test", emailVerified: true }, LIST));
  assert.ok(!isAdmin({ email: "lead@example.test", emailVerified: true }, undefined));
});
