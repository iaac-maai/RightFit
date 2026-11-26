// Tests for offering readings confirmed on the same file in another package (reuse.ts). Made-up packages and producers.
import assert from "node:assert/strict";
import { test } from "node:test";
import { offers, type Pkg } from "./reuse.ts";

const sheet = "Data sheet pump.pdf";
const pkg = (status: string, flow: string, issuer = "Pumpex"): Pkg => ({
  form: { form_no: "IS 015", revision: 0 },
  documents: [{ file: sheet, doc_type: "data_sheet", issuer, issue_date: null, valid_until: null, covers: ["X1"], status, checked_by: status === "verified" ? "Ana" : null, verified_on: status === "verified" ? "2026-11-11" : null }],
  items: [{ id: "P01-1", name: "Booster set", values: {
    flow: { value: flow, unit: "m3/h", source: sheet, page: 3, status, checked_by: status === "verified" ? "Ana" : null, verified_on: "2026-11-11" },
    head: { value: 50, unit: "m", source: sheet, page: 4, status: "extracted" },
  } }],
});

test("the same file, recognised by its fingerprint under another name, offers what a person confirmed there", () => {
  const [o, ...rest] = offers(pkg("extracted", "15"), { [sheet]: "abc" }, [
    { where: "this project", code: "P09", pkg: { ...pkg("verified", "15"), documents: pkg("verified", "15").documents.map((d) => ({ ...d, file: "renamed.pdf" })),
      items: pkg("verified", "15").items.map((i) => ({ ...i, values: { flow: { ...i.values.flow, source: "renamed.pdf" }, head: { ...i.values.head, source: "renamed.pdf" } } })) },
      files: { "renamed.pdf": "abc" } },
  ]);
  assert.equal(rest.length, 0);
  assert.equal(o.there, "renamed.pdf");
  assert.deepEqual(o.targets.map((t) => t.kind === "value" ? t.key : "document"), ["document", "flow"]); // head was never confirmed there
  assert.match(o.targets[1].from, /^this project, P09 \(MAF IS 015 rev 0\), confirmed by Ana on 2026-11-11$/);
  assert.equal(o.differ.length, 0);
});

test("a reading confirmed there with another value is shown as a difference, never offered", () => {
  const [o] = offers(pkg("extracted", "15", "Pumpex"), { [sheet]: "abc" }, [{ where: "Clinic", code: "P02", pkg: pkg("verified", "18", "Pumpex SA"), files: { [sheet]: "abc" } }]);
  assert.equal(o.targets.length, 0);
  assert.deepEqual(o.differ.map((d) => [d.what, d.here, d.there]), [["issuer", "Pumpex", "Pumpex SA"], ["flow, Booster set", "15 m3/h", "18 m3/h"]]);
});

test("another file, or nothing confirmed there, offers nothing", () => {
  assert.deepEqual(offers(pkg("extracted", "15"), { [sheet]: "abc" }, [{ where: "Clinic", code: "P02", pkg: pkg("verified", "15"), files: { [sheet]: "def" } }]), []);
  assert.deepEqual(offers(pkg("extracted", "15"), { [sheet]: "abc" }, [{ where: "Clinic", code: "P02", pkg: pkg("extracted", "15"), files: { [sheet]: "abc" } }]), []);
});
