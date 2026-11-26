// Tests for the BOQ register (register.ts). Made-up forms, producers and BOQ lines.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Graph } from "./products.ts";
import { key, register } from "./register.ts";

const file = "boq.xlsx";
const lines = [10, 11, 12, 13, 14].map((row) => ({ file, sheet: "Sanitare", row }));
const graph: Graph = {
  nodes: [
    { id: "line:pipe", type: "product_line", kind: "pipe", label: "PP-R PN20 · tubex" },
    { id: "line:valve", type: "product_line", kind: "valve", label: "ball valve · valvex" },
    { id: "form:this project:P04", type: "form", project: "this project", package: "P04", label: "IS 004 rev 0" },
    { id: "form:this project:P05", type: "form", project: "this project", package: "P05", label: "IS 004 rev 1" },
    { id: "form:earlier project:12:0", type: "form", project: "earlier project", label: "MAF 12 rev 0", answer: "A" },
    ...[10, 11, 12, 13].map((row) => ({ id: `boq:1:Sanitare:${row}`, type: "boq_line" as const, label: "", file, sheet: "Sanitare", row })),
  ],
  edges: [
    { from: "form:this project:P04", to: "line:pipe", type: "submits" },
    { from: "form:this project:P05", to: "line:pipe", type: "submits" },
    { from: "form:earlier project:12:0", to: "line:valve", type: "submits" },
    { from: "line:pipe", to: "boq:1:Sanitare:10", type: "covers" },
    { from: "line:valve", to: "boq:1:Sanitare:11", type: "covers" },
    { from: "line:pipe", to: "boq:1:Sanitare:12", type: "near" },
  ],
};
const at = (row: number) => key({ file, sheet: "Sanitare", row });

test("a line takes the best answer of the forms that cover it: rev 0 returned, rev 1 approved", () => {
  const r = register(lines, graph, { P04: "C", P05: "B" }, [], true);
  assert.equal(r[at(10)].status, "approved");
  assert.deepEqual(r[at(10)].forms.map((f) => `${f.form} ${f.answer}`), ["IS 004 rev 0 C", "IS 004 rev 1 B"]);
  assert.equal(register(lines, graph, { P04: "C" }, [], true)[at(10)].status, "submitted"); // rev 1 still waits
  assert.equal(register(lines, graph, { P04: "C", P05: "C" }, [], true)[at(10)].status, "returned");
});

test("an earlier project's approval shows only to those who may see the register, and a near match is a question", () => {
  assert.equal(register(lines, graph, {}, [], true)[at(11)].status, "approved_before");
  assert.equal(register(lines, graph, {}, [], false)[at(11)].status, "none"); // a contractor never sees the register
  assert.equal(register(lines, graph, {}, [], true)[at(12)].status, "might");
  assert.equal(register(lines, graph, {}, [], true)[at(13)].status, "none"); // a pipe line no form reaches
  assert.equal(register(lines, graph, {}, [], true)[at(14)], undefined);      // not of a kind RightFit reads: unread
});

test("a read package's own BOQ match counts as submitted, and a graph without files finds its line by sheet and row", () => {
  const r = register(lines, graph, { P01: "A" }, [{ file, sheet: "Sanitare", row: 14, code: "P01", form: "IS 015 rev 0" }], true);
  assert.equal(r[at(14)].status, "approved");
  const old: Graph = { nodes: graph.nodes.map(({ file: _f, ...n }) => n), edges: graph.edges };
  assert.equal(register(lines, old, { P04: "A" }, [], true)[at(10)].status, "approved");
});
