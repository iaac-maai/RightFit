// The products that come back (spec/features/knowledge_graph.md, MAF-36a), for the consultant's people: the product
// lines of cables, pipes, valves and boilers, with the forms that submitted them, the answers they got, the documents
// that came with them and the lines of this project's BOQ they cover. Read by fixed rules on the laptop, no AI
// (ingest/products.py, ingest/graph.py); the Worker adds the consultant's other projects (worker/products.ts).
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, go, post } from "../api";
import { day, plural } from "../format";
import type { Graph, GraphEdge, GraphNode } from "../../worker/products";

interface ProductsData {
  graph: Graph; imported: boolean; waiting: number; projects: { id: string; name: string; here: boolean }[];
  dpa: { accepted: string; current: string; across: boolean };
}

const KINDS: [string, string][] = [["cable", "Cables"], ["pipe", "Pipes"], ["valve", "Valves"], ["boiler", "Boilers"]];
const PART: Record<string, string> = {
  producer: "producer", material: "material", pressure: "pressure class", standard: "standard", use: "use", designation: "type",
  fire: "fire behaviour", cpr: "CPR class", type: "type", connection: "connection", series: "series", fuel: "fuel",
};

export function Products({ projectId }: { projectId: string }) {
  const [data, setData] = useState<ProductsData | null>(null);
  const [error, setError] = useState("");
  const [kind, setKind] = useState("all");
  const load = useCallback(() => api<ProductsData>(`/api/projects/${projectId}/products`).then(setData, (e: Error) => setError(e.message)), [projectId]);
  useEffect(() => { void load(); }, [load]);
  const byId = useMemo(() => new Map((data?.graph.nodes ?? []).map((n) => [n.id, n])), [data]);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;

  const all = data.graph.nodes.filter((n) => n.type === "product_line")
    .sort((a, b) => KINDS.findIndex(([k]) => k === a.kind) - KINDS.findIndex(([k]) => k === b.kind) || a.label.localeCompare(b.label));
  const lines = all.filter((n) => kind === "all" || n.kind === kind);
  const earlier = data.graph.nodes.some((n) => n.type === "form" && n.project === "earlier project");
  const sources = [...data.projects.map((p) => (p.here ? "this project" : p.name)), ...(earlier ? ["the register of your earlier project"] : [])];
  return (
    <>
      {!data.dpa.across && <Agreement projectId={projectId} dpa={data.dpa} onAccepted={() => void load()} />}
      <section className="sheet" aria-labelledby="products-title">
        <div className="sheet-head">
          <span className="lab" id="products-title">Products that come back</span>
          <span className="count">{plural(all.length, "product line", "product lines")} from {words(sources)}</span>
        </div>
        <p className="sheet-note band">
          Cables, pipes, valves and boilers come back from one project to the next. RightFit reads each product line out of the
          forms, the register of your earlier project and this project's BOQ, with fixed rules and no AI. A BOQ line is covered when
          every part agrees, and might be covered when a part is not given on one side: then you decide. Open a line for its forms,
          documents and BOQ lines.
        </p>
        {!data.imported && <p className="sheet-note band">This project's own product lines come when the laptop imports it: RightFit reads them there.</p>}
        {data.waiting > 0 && (
          <p className="sheet-note band">
            {plural(data.waiting, "other project of yours shows", "other projects of yours show")} here once a consultant of it accepts
            the data processing agreement of {day(data.dpa.current)}.
          </p>
        )}
        <div className="chapters" role="group" aria-label="Kind">
          <button type="button" className={`chapter${kind === "all" ? " on" : ""}`} onClick={() => setKind("all")}>All<span>{all.length}</span></button>
          {KINDS.map(([k, label]) => (
            <button key={k} type="button" className={`chapter${kind === k ? " on" : ""}`} onClick={() => setKind(k)}>
              {label}<span>{all.filter((n) => n.kind === k).length}</span>
            </button>
          ))}
        </div>
        {lines.length ? (
          <>
            <div className="pl-row pl-head" aria-hidden="true">
              <span className="lab">Product line</span><span className="lab">Sizes</span><span className="lab">Forms and answers</span><span className="lab">This project's BOQ</span>
            </div>
            <ul className="product-lines">{lines.map((n) => <Line key={n.id} n={n} edges={data.graph.edges} byId={byId} projectId={projectId} />)}</ul>
          </>
        ) : <p className="empty">{all.length ? "No product line of this kind yet." : "No product line yet."}</p>}
      </section>
    </>
  );
}

function Line({ n, edges, byId, projectId }: { n: GraphNode; edges: GraphEdge[]; byId: Map<string, GraphNode>; projectId: string }) {
  const from = (f: GraphNode) => (f.projectId === projectId ? "this project" : f.project);
  const into = (type: GraphEdge["type"]) => edges.filter((e) => e.to === n.id && e.type === type).map((e) => byId.get(e.from)!);
  const out = (type: GraphEdge["type"]) => edges.filter((e) => e.from === n.id && e.type === type).map((e) => byId.get(e.to)!);
  const forms = into("submits").sort((a, b) => (a.project ?? "").localeCompare(b.project ?? "") || a.label.localeCompare(b.label));
  const covers = out("covers");
  const might = out("near").filter((b) => b.type === "boq_line");
  const docs = into("supports");
  const same = edges.filter((e) => e.type === "near" && (e.from === n.id || e.to === n.id))
    .map((e) => byId.get(e.from === n.id ? e.to : e.from)!).filter((x) => x.type === "product_line");
  const missing = Object.entries(n.parts ?? {}).filter(([, v]) => !v).map(([k]) => PART[k] ?? k);
  const boq = [...covers.map((b) => ({ b, how: "covers" })), ...might.map((b) => ({ b, how: "might" }))];
  // a document opens in the package it came in, for the members of that project
  const where = (d: GraphNode) => edges.filter((e) => e.from === d.id && e.type === "in").map((e) => byId.get(e.to)!).find((f) => f.projectId && f.package);
  return (
    <li>
      <details>
        <summary className="pl-row">
          <span className="pl-name">
            <span className="lab">{KINDS.find(([k]) => k === n.kind)?.[1].replace(/s$/, "") ?? n.kind}</span>
            <b className="typed">{n.label}</b>
            {missing.length > 0 && <span className="pl-missing">{missing.join(", ")} not given</span>}
          </span>
          <span className="pl-sizes typed">{range(n.sizes ?? [])}</span>
          <span className="pl-forms">
            {forms.map((f) => (
              <span key={f.id} className="pl-form">
                {f.label}{f.answer && <i className={`letter sm ${f.answer}`} aria-label={`answered ${f.answer}`}>{f.answer}</i>}
                <em>{from(f)}</em>
              </span>
            ))}
          </span>
          <span className="pl-boq">
            {covers.length > 0 && <span className="covers">covers {covers.length}</span>}
            {might.length > 0 && <span className="might">might cover {might.length}</span>}
            {!boq.length && <span className="meta">none found</span>}
          </span>
        </summary>
        <div className="pl-more">
          <div>
            <span className="lab">What RightFit read</span>
            <dl className="g-parts">
              {Object.entries(n.parts ?? {}).map(([k, v]) => <div key={k}><dt>{PART[k] ?? k}</dt><dd className={v ? "typed" : "unknown"}>{v ?? "not given"}</dd></div>)}
              <div><dt>sizes</dt><dd className="typed">{n.sizes?.join(", ") || "not given"}</dd></div>
            </dl>
          </div>
          <div>
            <span className="lab">Forms and answers</span>
            <ul>
              {forms.map((f) => (
                <li key={f.id}>
                  {f.projectId && f.package ? <a href={`/p/${f.projectId}/packages/${f.package}`} onClick={go(`/p/${f.projectId}/packages/${f.package}`)}>{f.label}</a> : f.label}
                  {" "}<span className="meta">{from(f)}{f.answer ? `, answered ${f.answer}` : ""}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <span className="lab">This project's BOQ lines</span>
            {boq.length ? (
              <ul>
                {boq.map(({ b, how }) => (
                  <li key={b.id} className={`pl-boq-line ${how}`}>
                    <span className="typed">{b.sizes?.join(", ") || "no size"}</span> {b.label}
                    <span className="meta"> · chapter {b.sheet} · {how === "covers" ? "covered" : "might be covered"}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="fine">None found.</p>}
          </div>
          {docs.length > 0 && (
            <div>
              <span className="lab">Documents that came with it</span>
              <ul>
                {docs.map((d) => {
                  const f = where(d);
                  const path = f ? `/p/${f.projectId}/packages/${f.package}` : "";
                  return (
                    <li key={d.id}>
                      {path ? <a href={path} onClick={go(path)}>{d.label}</a> : d.label}
                      {d.kind && d.kind !== "other" && <span className="meta"> · {d.kind}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {same.length > 0 && (
            <p className="fine pl-same">Might be the same line as {same.map((s) => s.label).join("; ")}: a part is not given on one side, so you decide.</p>
          )}
        </div>
      </details>
    </li>
  );
}

// "a", "a and b", "a, b and c"
const words = (items: string[]) => (items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`);

// "20, 25, 32" for a few sizes; the first and the last for many
const range = (sizes: string[]) => (!sizes.length ? "—" : sizes.length <= 3 ? sizes.join(", ") : `${sizes[0]} to ${sizes[sizes.length - 1]} (${sizes.length})`);

// The data processing agreement this project accepted, when it is older than the one with clause 1.4
function Agreement({ projectId, dpa, onAccepted }: { projectId: string; dpa: ProductsData["dpa"]; onAccepted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const accept = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(`/api/projects/${projectId}/dpa`, { version: dpa.current });
      onAccepted();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <section className="sheet" aria-labelledby="dpa-title">
      <div className="sheet-head"><span className="lab" id="dpa-title">Data processing agreement</span><span className="count">accepted {day(dpa.accepted)}</span></div>
      <form className="agreement" onSubmit={(e) => void accept(e)}>
        <p className="sheet-note">
          This project accepted the agreement of {day(dpa.accepted)}. The one of {day(dpa.current)} adds clause 1.4: RightFit keeps the
          record of the products that come back across your organisation's projects, and shows it to the people who act for it in its
          other projects. A document stays in its project. Until a consultant of this project accepts it, this project's product lines
          stay here.
        </p>
        <label className="tick">
          <input type="checkbox" required />
          <span>I am authorised to act for my organisation, and I accept the <a href="/data-processing" target="_blank" rel="noreferrer">Data Processing Agreement</a> of {day(dpa.current)} on its behalf.</span>
        </label>
        {error && <p className="err" role="alert">{error}</p>}
        <div className="actions"><button className="btn p" disabled={busy}>Accept for this project</button></div>
      </form>
    </section>
  );
}
