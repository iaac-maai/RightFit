// The BOQ register (spec/features/knowledge_graph.md, MAF-36c): for each line of a project's BOQ, the forms that reach
// it and where it stands: approved, submitted and waiting, returned, approved in an earlier project, perhaps covered,
// with no form, or of a kind RightFit does not match yet. Built from the project's knowledge graph (fixed rules, no AI),
// the BOQ line RightFit found for each product of a read package, and the answers the reviewers recorded. No route and
// nothing from Cloudflare here, so the tests run it as it is.
import type { Graph } from "./products";

export type Status = "approved" | "submitted" | "returned" | "approved_before" | "might" | "none" | "unread";
export interface Reach {
  form: string; code?: string;      // code: the package of this project that holds the form
  how: "covers" | "might" | "read"; // covers: every part agrees; might: a part is not given; read: RightFit matched it on a read package
  answer: string | null;            // A, B or C; null: not answered yet
  earlier?: boolean;                // a form of the earlier project, from its register
}
export interface Line { file: string; sheet: string; row: number }
export interface Link extends Line { code: string; form: string } // a read package's product and the BOQ line it was matched to
export interface Entry { status: Status; forms: Reach[] }

export const key = (l: Line) => `${l.file}|${l.sheet}|${l.row}`;
const OK = (a: string | null) => a === "A" || a === "B";

// earlier: whether the viewer may see the earlier project's register, which is the consultant's knowledge
export function register(lines: Line[], graph: Graph, answers: Record<string, string>, links: Link[], earlier: boolean): Record<string, Entry> {
  const out: Record<string, Entry> = {};
  const add = (k: string, r: Reach) => {
    const e = (out[k] ??= { status: "none", forms: [] });
    if (!e.forms.some((f) => f.form === r.form && f.how === r.how)) e.forms.push(r);
  };
  // a graph made before BOQ nodes carried their file: the sheet and row find the line when only one file has them
  const where = (n: { file?: string; sheet?: string; row?: number }) => {
    if (n.file) return key({ file: n.file, sheet: n.sheet ?? "", row: n.row ?? 0 });
    const hits = lines.filter((l) => l.sheet === n.sheet && l.row === n.row);
    return hits.length === 1 ? key(hits[0]) : null;
  };
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]));
  for (const b of graph.nodes) {
    if (b.type !== "boq_line") continue;
    const k = where(b);
    if (!k) continue;
    out[k] ??= { status: "none", forms: [] };   // a line of a kind RightFit reads: with no form, it shows as such
    for (const e of graph.edges) {
      if (e.to !== b.id || (e.type !== "covers" && e.type !== "near")) continue;
      for (const s of graph.edges) {
        const f = s.type === "submits" && s.to === e.from ? nodes.get(s.from) : undefined;
        if (!f || f.type !== "form") continue;
        const how = e.type === "covers" ? "covers" : "might";
        if (f.package) add(k, { form: f.label, code: f.package, how, answer: answers[f.package] ?? null });
        else if (earlier) add(k, { form: f.label, how, answer: f.answer ?? null, earlier: true });
      }
    }
  }
  for (const l of links) add(key(l), { form: l.form, code: l.code, how: "read", answer: answers[l.code] ?? null });
  for (const e of Object.values(out)) e.status = status(e.forms);
  return out;
}

// One form approved here is enough; otherwise a form still waiting; otherwise a form returned. Then what an earlier
// project approved, then a match a person has to decide.
function status(forms: Reach[]): Status {
  const here = forms.filter((f) => !f.earlier && f.how !== "might");
  if (here.some((f) => OK(f.answer))) return "approved";
  if (here.some((f) => f.answer === null)) return "submitted";
  if (here.length) return "returned";
  if (forms.some((f) => f.earlier && f.how === "covers" && OK(f.answer))) return "approved_before";
  return forms.length ? "might" : "none";
}
