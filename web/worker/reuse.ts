// The same file in two packages (spec/features/knowledge_graph.md, MAF-36b): a reading a person confirmed on a file in
// one package is offered for the same file in another, recognised by its fingerprint (the first 16 characters of its
// SHA-256). Nothing is confirmed here: the offer goes to a reviewer, who confirms it with one click, and the reading
// keeps where it was confirmed first. No route and nothing from Cloudflare here, so the tests run it as it is.

export interface Entry {
  value?: unknown; unit?: string | null; source?: string; page?: number | string | null; status: string;
  checked_by?: string | null; verified_on?: string | null;
}
export interface Doc extends Entry {
  file: string; doc_type: string; issuer?: string | null; issue_date?: string | null; valid_until?: string | null; covers?: string[];
}
export interface Pkg {
  form: { form_no: string; revision: number }; documents: Doc[];
  items: { id: string; name: string; values: Record<string, Entry> }[];
}
// A package where the same file may sit: its project's name as the viewer reads it, and its files' fingerprints
export interface Elsewhere { where: string; code: string; pkg: Pkg; files: Record<string, string> }

export type Target = { kind: "value"; item: string; key: string; from: string } | { kind: "document"; file: string; from: string };
export interface Offer {
  file: string; there: string; where: string; code: string; form: string;
  targets: Target[];                                    // what a reviewer confirms here with one click
  differ: { what: string; here: string; there: string; item?: string; key?: string }[]; // read differently: a person looks
}

// What makes a document's reading: the same in both packages, or a person looks again
const DOC_PARTS = ["doc_type", "issuer", "issue_date", "valid_until", "covers"] as const;
const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const shown = (e: Entry) => `${e.value ?? "not found"}${e.unit ? ` ${e.unit}` : ""}`;
const confirmedBy = (e: Entry) => `confirmed by ${e.checked_by || "a reviewer"}${e.verified_on ? ` on ${e.verified_on}` : ""}`;

export function offers(here: Pkg, files: Record<string, string>, elsewhere: Elsewhere[]): Offer[] {
  const out: Offer[] = [];
  for (const d of here.documents) {
    const print = files[d.file];
    if (!print) continue;
    for (const e of elsewhere) {
      const there = Object.keys(e.files).find((name) => e.files[name] === print);
      const td = there ? e.pkg.documents.find((x) => x.file === there) : undefined;
      if (!there || !td) continue;
      const form = `MAF ${e.pkg.form.form_no} rev ${e.pkg.form.revision}`;
      const from = (x: Entry) => `${e.where}, ${e.code} (${form}), ${confirmedBy(x)}`;
      const offer: Offer = { file: d.file, there, where: e.where, code: e.code, form, targets: [], differ: [] };
      if (d.status !== "verified" && td.status === "verified") {
        const parts = DOC_PARTS.filter((p) => !same(d[p], td[p]));
        if (!parts.length) offer.targets.push({ kind: "document", file: d.file, from: from(td) });
        else for (const p of parts) offer.differ.push({ what: p.replace("_", " "), here: String(d[p] ?? "not found"), there: String(td[p] ?? "not found") });
      }
      // a value counts as the same reading when it was read on the same page of the same file, for the same thing
      const confirmed = e.pkg.items.flatMap((i) => Object.entries(i.values))
        .filter(([, x]) => x.source === there && x.status === "verified");
      for (const item of here.items) {
        for (const [key, x] of Object.entries(item.values)) {
          if (x.source !== d.file || x.status === "verified") continue;
          const twins = confirmed.filter(([k, y]) => k === key && same(y.page, x.page)).map(([, y]) => y);
          const twin = twins.find((y) => same(y.value, x.value) && same(y.unit, x.unit));
          if (twin) offer.targets.push({ kind: "value", item: item.id, key, from: from(twin) });
          else if (twins.length) offer.differ.push({ what: `${key.replace(/_/g, " ")}, ${item.name}`, here: shown(x), there: shown(twins[0]), item: item.id, key });
        }
      }
      if (offer.targets.length || offer.differ.length) out.push(offer);
    }
  }
  return out;
}
