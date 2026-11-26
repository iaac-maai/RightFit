// Tests for putting a consultant's knowledge graphs together (products.ts). Made-up projects, forms and producers.
import assert from "node:assert/strict";
import { test } from "node:test";
import { together, type Graph, type GraphNode } from "./products.ts";

const pipe: GraphNode = { id: "line:pipe|tubex|pp-r", type: "product_line", kind: "pipe", label: "PP-R PN20 · tubex", sizes: ["20", "25"] };
const here: Graph = {
  nodes: [
    { ...pipe },
    { id: "form:this project:P04", type: "form", project: "this project", package: "P04", label: "IS 004 rev 1" },
    { id: "form:earlier project:12:0", type: "form", project: "earlier project", label: "MAF 12 rev 0", answer: "B" },
    { id: "boq:1:Sanitare:40", type: "boq_line", kind: "pipe", label: "Teava PP-R PN20 apa rece", sizes: ["25"] },
  ],
  edges: [
    { from: "form:this project:P04", to: pipe.id, type: "submits" },
    { from: "form:earlier project:12:0", to: pipe.id, type: "submits" },
    { from: pipe.id, to: "boq:1:Sanitare:40", type: "covers" },
  ],
};
const there: Graph = {
  nodes: [
    { ...pipe, sizes: ["32", "110"] },
    { id: "form:this project:P04", type: "form", project: "this project", package: "P04", label: "IS 017 rev 0" },
    { id: "form:earlier project:12:0", type: "form", project: "earlier project", label: "MAF 12 rev 0", answer: "B" },
    { id: "boq:1:Sanitare:7", type: "boq_line", kind: "pipe", label: "Teava PP-R PN20 apa calda", sizes: ["32"] },
  ],
  edges: [
    { from: "form:this project:P04", to: pipe.id, type: "submits" },
    { from: "form:earlier project:12:0", to: pipe.id, type: "submits" },
    { from: pipe.id, to: "boq:1:Sanitare:7", type: "covers" },
  ],
};

test("a product line from two projects is one line, with the forms of both under their projects' names", () => {
  const g = together({ id: "a", name: "School", graph: here }, [{ id: "b", name: "Clinic", graph: there }]);
  const line = g.nodes.find((n) => n.id === pipe.id)!;
  assert.deepEqual(line.sizes, ["20", "25", "32", "110"]);
  assert.deepEqual(line.projects, ["Clinic", "School", "earlier project"]);
  const forms = g.nodes.filter((n) => n.type === "form").map((n) => `${n.label} · ${n.project}`).sort();
  assert.deepEqual(forms, ["IS 004 rev 1 · School", "IS 017 rev 0 · Clinic", "MAF 12 rev 0 · earlier project"]); // P04 twice, two forms
});

test("only this project's BOQ lines come along: a BOQ belongs to one project", () => {
  const g = together({ id: "a", name: "School", graph: here }, [{ id: "b", name: "Clinic", graph: there }]);
  assert.deepEqual(g.nodes.filter((n) => n.type === "boq_line").map((n) => n.label), ["Teava PP-R PN20 apa rece"]);
  assert.equal(g.edges.filter((e) => e.type === "covers").length, 1);
  assert.ok(g.edges.every((e) => g.nodes.some((n) => n.id === e.from) && g.nodes.some((n) => n.id === e.to)));
});

test("with no other project, this project's graph comes back as it is, its forms named", () => {
  const g = together({ id: "a", name: "School", graph: here }, []);
  assert.equal(g.nodes.length, here.nodes.length);
  assert.equal(g.edges.length, here.edges.length);
  assert.equal(g.nodes.find((n) => n.label === "IS 004 rev 1")?.project, "School");
});
