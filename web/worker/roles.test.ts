// Tests for who may invite whom and who sees whom. Run with `npm test` (Node's own test runner, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { ROLES, isRole, mayAddPackage, mayChangeReview, mayChangeRules, mayInvite, mayUseProducts, mayWithdraw, rolesInvitableBy, visibleInvitations, visiblePeople,
  type Person } from "./roles.ts";

// A made-up project: the consultant brings in a designer and the contractor; the contractor two subcontractor firms,
// HVAC (whose first person brings in a colleague, who brings in a third) and electrical
const team: Person[] = [
  { id: "cons", role: "consultant", invitedBy: null },
  { id: "des", role: "designer", invitedBy: "cons" },
  { id: "con", role: "contractor", invitedBy: "cons" },
  { id: "hvac", role: "subcontractor", invitedBy: "con" },
  { id: "hvac2", role: "subcontractor", invitedBy: "hvac" }, // colleagues at the HVAC firm
  { id: "hvac3", role: "subcontractor", invitedBy: "hvac2" },
  { id: "elec", role: "subcontractor", invitedBy: "con" },
];
const person = (id: string) => team.find((p) => p.id === id)!;
const seenBy = (id: string) => visiblePeople(team, person(id)).map((p) => p.id).sort();

test("the chain of invitations: down one step, or a colleague in the same role", () => {
  assert.ok(mayInvite("consultant", "contractor"));
  assert.ok(mayInvite("consultant", "site_supervisor"));
  assert.ok(mayInvite("contractor", "subcontractor"));
  assert.ok(mayInvite("subcontractor", "subcontractor"));
  assert.ok(!mayInvite("subcontractor", "contractor"));
  assert.ok(!mayInvite("contractor", "consultant"));
  assert.ok(!mayInvite("designer", "contractor"));
  assert.deepEqual(rolesInvitableBy("client"), ["client"]);
  assert.deepEqual(rolesInvitableBy("subcontractor"), ["subcontractor"]);
});

test("roles from outside are checked, and suppliers are left out for now", () => {
  assert.ok(isRole("subcontractor"));
  assert.ok(!isRole("supplier"));
  assert.ok(!isRole("admin"));
  assert.ok(!isRole(undefined));
});

test("reviewers and the contractor see the whole team", () => {
  assert.equal(seenBy("cons").length, team.length);
  assert.equal(seenBy("des").length, team.length);
  assert.equal(seenBy("con").length, team.length);
});

test("a subcontractor sees its own firm and the chain above it, never another firm", () => {
  const hvacFirm = ["con", "cons", "des", "hvac", "hvac2", "hvac3"];
  assert.deepEqual(seenBy("hvac"), hvacFirm);
  assert.deepEqual(seenBy("hvac2"), hvacFirm);
  assert.deepEqual(seenBy("hvac3"), hvacFirm); // the third colleague sees the first, who is not above them directly
  assert.deepEqual(seenBy("elec"), ["con", "cons", "des", "elec"]);
});

test("pending invitations follow the same branches", () => {
  const pending = [
    { id: "i1", invitedBy: "hvac2" }, // the HVAC firm invites another colleague
    { id: "i2", invitedBy: "con" }, // the contractor invites a third subcontractor firm
    { id: "i3", invitedBy: "elec" },
  ];
  const ids = (viewer: string) => visibleInvitations(pending, team, person(viewer)).map((i) => i.id);
  assert.deepEqual(ids("con"), ["i1", "i2", "i3"]);
  assert.deepEqual(ids("hvac"), ["i1"]);
  assert.deepEqual(ids("elec"), ["i3"]);
});

test("whoever sent an invitation, or a consultant, may withdraw it", () => {
  assert.ok(mayWithdraw(person("hvac2"), "hvac2"));
  assert.ok(mayWithdraw(person("cons"), "hvac2"));
  assert.ok(!mayWithdraw(person("hvac"), "hvac2"));
});

test("a broken chain does not loop", () => {
  const loop: Person[] = [
    { id: "a", role: "subcontractor", invitedBy: "b" },
    { id: "b", role: "subcontractor", invitedBy: "a" },
  ];
  assert.deepEqual(visiblePeople(loop, loop[0]).map((p) => p.id).sort(), ["a", "b"]);
});

test("only the reviewers change a review, and only the consultant changes the consultant's rules", () => {
  assert.deepEqual(ROLES.filter(mayChangeReview), ["consultant", "designer", "site_supervisor", "client"]);
  assert.deepEqual(ROLES.filter(mayChangeRules), ["consultant"]);
});

test("the reviewers and the contractor add packages; a subcontractor waits for its branch", () => {
  assert.deepEqual(ROLES.filter(mayAddPackage), ["consultant", "designer", "site_supervisor", "client", "contractor"]);
});

test("only the consultant sees the products that come back and accepts a new agreement for the organisation", () => {
  assert.deepEqual(ROLES.filter(mayUseProducts), ["consultant"]);
});
