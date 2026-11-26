// The products that come back across a consultant's projects (spec/features/knowledge_graph.md, sections 5 and 6):
// the knowledge graph each import makes on the laptop (ingest/graph.py), put together for one consultant. No route
// and nothing from Cloudflare here, so the tests run it as it is (products.test.ts).

// The first version of the data processing agreement with clause 1.4: a project's product lines show in its
// consultant's other projects only once a consultant of it has accepted this version or a later one
export const ACROSS_PROJECTS_FROM = "2026-11-26";

export interface GraphNode {
  id: string; type: "product_line" | "form" | "document" | "boq_line"; label: string; kind?: string;
  project?: string; projectId?: string; package?: string; answer?: string | null;
  parts?: Record<string, string | null>; sizes?: string[]; projects?: string[]; sheet?: string; row?: number;
}
export interface GraphEdge { from: string; to: string; type: "submits" | "in" | "supports" | "covers" | "near"; sizes?: string[] }
export interface Graph { nodes: GraphNode[]; edges: GraphEdge[] }
export interface ProjectGraph { id: string; name: string; graph: Graph }

const THIS = "form:this project:";

// One consultant's products: this project's graph whole, and from each other project its product lines, forms,
// answers and documents. Every import calls its own forms "this project", so they take that project's name; the
// BOQ lines stay in their project, because a BOQ belongs to one project. The register of the earlier project is
// the same consultant's in every import, so its forms are one node wherever they come from.
export function together(here: ProjectGraph, others: ProjectGraph[]): Graph {
  const nodes = new Map<string, GraphNode>();
  const edges = new Map<string, GraphEdge>();
  [here, ...others].forEach((p, i) => {
    const id = (nid: string) => (nid.startsWith(THIS) ? `form:${p.id}:${nid.slice(THIS.length)}` : nid.startsWith("boq:") ? `boq:${p.id}:${nid.slice(4)}` : nid);
    for (const n of p.graph.nodes) {
      if (i > 0 && n.type === "boq_line") continue;
      const node: GraphNode = { ...n, id: id(n.id), ...(n.id.startsWith(THIS) ? { project: p.name, projectId: p.id } : {}) };
      const known = nodes.get(node.id);
      if (!known) nodes.set(node.id, node);
      else if (known.type === "product_line") known.sizes = [...new Set([...(known.sizes ?? []), ...(node.sizes ?? [])])].sort(bySize);
    }
    for (const e of p.graph.edges) {
      const [from, to] = [id(e.from), id(e.to)];
      if (nodes.has(from) && nodes.has(to)) edges.set(`${from}|${to}|${e.type}`, { ...e, from, to });
    }
  });
  // the projects a product line was submitted in, by name, now that every form carries its project's name
  for (const n of nodes.values()) {
    if (n.type !== "product_line") continue;
    const names = [...edges.values()].filter((e) => e.type === "submits" && e.to === n.id).map((e) => nodes.get(e.from)?.project ?? "");
    n.projects = [...new Set(names)].sort();
  }
  return { nodes: [...nodes.values()], edges: [...edges.values()] };
}

// Sizes such as "20", "3x1.5" or "26 kW": by how many numbers they hold, then by the numbers
function bySize(a: string, b: string) {
  const nums = (s: string) => (s.match(/\d+(?:\.\d+)?/g) ?? []).map(Number);
  const [x, y] = [nums(a), nums(b)];
  if (x.length !== y.length) return x.length - y.length;
  for (let k = 0; k < x.length; k++) if (x[k] !== y[k]) return x[k] - y[k];
  return a.localeCompare(b);
}
