// Inside RightFit (spec/features/knowledge_graph.md, section 7): how RightFit and its tools work, shown with a project's
// own numbers, the way the hackathon app's Look inside showed its network with the network's own numbers. For admins
// only, and a project only for an admin who is a member of it, with the team password for a locked one: Management
// itself still never opens a project's data.
import { type CSSProperties, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../api";
import { plural } from "../format";
import type { HomeData, PackageData, PackageRow, PackageReview } from "../types";
import { TeamLock } from "./ProjectData";
import type { Graph as Drawn, GraphEdge as GEdge, GraphNode as GNode } from "../../worker/products";

type Who = "ai" | "rules" | "person";
interface Graph extends Drawn {
  summary: { product_lines: Record<string, number>; forms: number; documents: number; boq_lines: number; came_back: number; near: number };
}

const WHO: Record<Who, string> = { ai: "AI", rules: "Rules, no AI", person: "A person" };
const KINDS: [string, string][] = [["cable", "Cables"], ["pipe", "Pipes"], ["valve", "Valves"], ["boiler", "Boilers"]];
const CHECKS = ["D1 Required documents", "D2 Declaration matches the products", "D3 Certificate in date", "D4 Attachment is what the form says",
  "V1 Duty point", "V2 Pressure rating", "V3 Liquid temperature", "E1 Ecodesign", "H1 Drinking water approval", "C Reviewers' checklist",
  "P Consultant's rules", "Q BOQ line", "R Delivery reminder"]; // as in app/review_core.py, CHECK_NAMES

export function Inside() {
  const [home, setHome] = useState<HomeData | null>(null);
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    api<HomeData>("/api/home").then((h) => {
      setHome(h);
      setProjectId((h.projects.find((p) => p.locked) ?? h.projects[0])?.id ?? "");
    }, (e: Error) => setError(e.message));
  }, []);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!home) return <span className="spinner" aria-label="Loading" />;
  return (
    <div className="inside">
      <section className="inside-intro">
        <p>
          How RightFit works, shown on a project's own data: every number below comes from the project you pick, the way the
          hackathon app explained its network with the network's own numbers. Only RightFit's team sees this page, and only for
          projects they are members of.
        </p>
        {home.projects.length > 0 ? (
          <label className="field inline">
            <span className="lab">Project</span>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {home.projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        ) : <p className="fine">You are not a member of any project, so there is nothing of a project to show.</p>}
      </section>
      {projectId && <ProjectInside key={projectId} projectId={projectId} name={home.projects.find((p) => p.id === projectId)?.name ?? ""} />}
    </div>
  );
}

function ProjectInside({ projectId, name }: { projectId: string; name: string }) {
  const [packages, setPackages] = useState<PackageRow[] | null>(null);
  const [locked, setLocked] = useState(false);
  const [code, setCode] = useState("");
  const [data, setData] = useState<PackageData | null>(null);
  const [graph, setGraph] = useState<Graph | null | "none">(null);
  const [round, setRound] = useState(0);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ packages: PackageRow[] }>(`/api/projects/${projectId}/packages`).then((r) => {
      setPackages(r.packages);
      setCode(r.packages.find((p) => p.letter)?.code ?? "");
    }, (err: Error) => { if (err instanceof ApiError && err.data.need === "team") setLocked(true); else setError(err.message); });
    api<Graph>(`/api/projects/${projectId}/graph`).then(setGraph, () => setGraph("none"));
  }, [projectId, round]);
  useEffect(() => {
    if (code) api<PackageData>(`/api/projects/${projectId}/packages/${code}`).then(setData, () => setData(null));
  }, [projectId, code, round]);
  if (locked) return <TeamLock name={name} onUnlocked={() => { setLocked(false); setRound((n) => n + 1); }} />;
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!packages) return <span className="spinner" aria-label="Loading" />;
  const read = packages.filter((p) => p.letter);
  return (
    <>
      <section className="sheet" aria-labelledby="path-title">
        <div className="sheet-head">
          <span className="lab" id="path-title">The path of a package</span>
          {read.length > 0 && (
            <select className="small-select" aria-label="Package" value={code} onChange={(e) => setCode(e.target.value)}>
              {read.map((p) => <option key={p.code} value={p.code}>{p.code} · {p.formNo} rev {p.revision}</option>)}
            </select>
          )}
        </div>
        {data?.review ? <Path p={data.package} v={data.review} /> : (
          <p className="empty">{read.length ? "Loading the package…" : "No package of this project has been read yet, so the path has no numbers to show."}</p>
        )}
      </section>
      <Tools graph={graph !== "none" ? graph : null} packages={packages.length} read={read.length} />
      {graph === "none" ? <p className="band-note">The knowledge graph comes with the next import from the laptop.</p>
        : graph ? <GraphView g={graph} /> : <span className="spinner" aria-label="Loading" />}
    </>
  );
}

// ------------------------------------------------------------------ the path, step by step, with the package's own numbers
interface Step { name: string; who: Who; figure: string; caption: string; more: string; code: string }

function Path({ p, v }: { p: PackageRow; v: PackageReview }) {
  const c = v.counts;
  const used = new Map(v.results.flatMap((r) => r.rules).map((u) => [u.id, u.status]));
  const official = [...used.values()].filter((s) => s === "verified_official").length;
  const decided = Object.keys(v.decisions ?? {}).length;
  const steps: Step[] = [
    { name: "The package", who: "person", figure: `${p.files} files`, caption: `${p.pages ?? 0} pages`, code: "web/worker/upload.ts, web/scripts/import_project.py",
      more: "The form and its attachments, as the contractor sends them: added on the site or put online from the laptop, kept in the project's private storage." },
    { name: "The pages", who: "ai", figure: "62 %", caption: "of 184 locked pages", code: "model/page_classifier.py",
      more: "Our own model, trained by the team, says what each page is: a declaration, a data sheet, a certificate, a manual. On the locked test it gets 115 of 184 pages right, against 64 for a keyword search." },
    { name: "The readings", who: "ai", figure: `${c.readings}`, caption: `${c.readings - c.to_confirm} confirmed by a person`, code: "spec/features/maf_checker.md, section 3",
      more: "The AI reader writes every value with its file, its page and a short quote. A value stays violet and dashed until a person ticks it; a check passes only on confirmed values." },
    { name: "The checks", who: "rules", figure: `${c.problems + c.questions + c.passed + c.would_pass}`,
      caption: `${c.problems} problems, ${c.questions} questions, ${c.passed} passed, ${c.would_pass} pass once confirmed`, code: "checks/maf, app/review_core.py",
      more: `${CHECKS.length} checks in plain Python, with no AI: the same package always gets the same result, and every result names its rule. The same code runs on the laptop and in the engine on Cloudflare.` },
    { name: "The rules", who: "rules", figure: `${used.size}`, caption: `rules used, ${official} read in the official journal`, code: "data/maf/rules.csv, ingest/rule_watch.py",
      more: "Each rule keeps its article, the dates it is in force and where it stands. The rule watch asks the official journals whether the act behind a rule changed since it was read." },
    { name: "The draft", who: "rules", figure: v.status.letter, caption: `${v.status.label}, ${plural(v.answer.lines.length, "comment", "comments")}`, code: "checks/maf/status.py, checks/maf/comments.py",
      more: "The letter follows a fixed rule: C when a product has no data sheet that names it or a blocking item is missing, B when a problem or a question is open, A otherwise. Each comment is written from the result, never invented." },
    { name: "The reviewer", who: "person", figure: `${decided}`, caption: `${plural(decided, "decision", "decisions")} so far`, code: "web/worker/review_edit.ts, web/engine",
      more: "The reviewer ticks the readings, keeps or dismisses each finding with its reason and decides on the AI's suggestions. Each change runs the checks again in the engine, in about a tenth of a second." },
    { name: "The answer", who: "person", figure: "1", caption: "signature: the reviewer's, never RightFit's", code: "",
      more: "RightFit drafts; the reviewer decides and signs. The tool certifies nothing, and every answer says what was and was not checked." },
  ];
  const [open, setOpen] = useState(3);
  const s = steps[open];
  return (
    <div className="path">
      <ol className="stations">
        {steps.map((st, i) => (
          <li key={st.name} style={{ "--i": i } as CSSProperties}>
            <button type="button" className={`station ${st.who}`} aria-pressed={open === i} onClick={() => setOpen(i)}>
              <span className="station-n">{String(i + 1).padStart(2, "0")}</span>
              <span className="station-name">{st.name}</span>
              {st.name === "The draft" ? <i className={`letter sm ${st.figure}`}>{st.figure}</i>
                : <span className="typed station-figure">{st.figure}</span>}
              <span className="station-caption">{st.caption}</span>
            </button>
          </li>
        ))}
      </ol>
      <div className="travel" aria-hidden="true"><i style={{ width: `${((open + 1) / steps.length) * 100}%` }} /></div>
      <div key={open} className={`station-more ${s.who}`} role="region" aria-live="polite">
        <span className={`who-chip ${s.who}`}>{WHO[s.who]}</span>
        <h3>{s.name}</h3>
        <p>{s.more}</p>
        {s.code && <p className="fine">In the code: <code>{s.code}</code></p>}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ the tools
function Tools({ graph, packages, read }: { graph: Graph | null; packages: number; read: number }) {
  const lines = graph ? Object.values(graph.summary.product_lines).reduce((a, b) => a + b, 0) : 0;
  const cards: { name: string; who: Who; text: string; figure: string; code: string }[] = [
    { name: "The checks engine", who: "rules", text: "The laptop's own review code, in a Python Worker on Cloudflare that only the site can call. It keeps nothing.", figure: "≈ 0.1 s a review", code: "web/engine, app/engine.py" },
    { name: "The checks", who: "rules", text: CHECKS.join(" · "), figure: `${CHECKS.length} checks`, code: "checks/maf" },
    { name: "The AI reader", who: "ai", text: "Reads each value of a package with its page and a short quote. Run as an agent for now; a person confirms what it read.", figure: `${read} of ${packages} packages read`, code: "spec/features/maf_checker.md" },
    { name: "Our page classifier", who: "ai", text: "What kind of document each page is. Trained by the team on public and real pages.", figure: "62 % vs 35 % for keywords", code: "model/page_classifier.py" },
    { name: "Our family classifier", who: "ai", text: "A product's family from its form row. The family words still beat it, so the checks use the words.", figure: "28 vs 35 of 37 rows", code: "model/family_classifier.py" },
    { name: "Booster sizing", who: "rules", text: "A building's need by DIN 1988-300 and CTE HS4, the submitted set on its real curve, and the sets that fit.", figure: "289 catalogue sets", code: "app/booster.py" },
    { name: "Since the previous revision", who: "rules", text: "File by file: the same file, the closest by text, or by the look of the pages for a scan.", figure: "no AI", code: "ingest/revisions.py" },
    { name: "The rule watch", who: "rules", text: "Asks the EU Publications Office, Spain's BOE and Romania's Portal Legislativ whether an act changed.", figure: "no AI", code: "ingest/rule_watch.py" },
    { name: "Tools for agents", who: "rules", text: "The checks as MCP tools any agent can call, read only: no tool confirms or approves.", figure: "6 tools", code: "app/mcp_server.py" },
    { name: "The knowledge graph", who: "rules", text: "Product lines that come back from project to project, with their forms, answers, documents and BOQ lines.", figure: graph ? `${lines} product lines` : "after the import", code: "ingest/products.py, ingest/graph.py" },
  ];
  return (
    <section className="sheet" aria-labelledby="tools-title">
      <div className="sheet-head"><span className="lab" id="tools-title">The tools</span><span className="count">violet is AI, green is rules</span></div>
      <div className="tool-grid">
        {cards.map((t) => (
          <article key={t.name} className={`tool ${t.who}`}>
            <span className={`who-chip ${t.who}`}>{WHO[t.who]}</span>
            <h3>{t.name}</h3>
            <p>{t.text}</p>
            <span className="typed tool-figure">{t.figure}</span>
            <code className="tool-code">{t.code}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ the knowledge graph, drawn
const ROW = 24;
// where each column stands, how wide its boxes are and how many letters fit in them, in the drawing's 1000 units
const COL = { form: 105, product_line: 470, boq_line: 850, document: 0 };
const WIDE = { form: 200, product_line: 230, boq_line: 290, document: 0 };
const FITS = { form: 32, product_line: 34, boq_line: 46, document: 0 };
const curve = (x1: number, y1: number, x2: number, y2: number) =>
  `M${x1} ${y1} C${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`;

function GraphView({ g }: { g: Graph }) {
  const [kind, setKind] = useState("all");
  const [picked, setPicked] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null); // the product line whose BOQ lines are drawn one by one
  const byId = useMemo(() => new Map(g.nodes.map((n) => [n.id, n])), [g]);
  const lines = g.nodes.filter((n) => n.type === "product_line" && (kind === "all" || n.kind === kind))
    .sort((a, b) => KINDS.findIndex(([k]) => k === a.kind) - KINDS.findIndex(([k]) => k === b.kind) || a.label.localeCompare(b.label));
  const shown = new Set(lines.map((n) => n.id));
  const submits = g.edges.filter((e) => e.type === "submits" && shown.has(e.to));
  const toBoq = g.edges.filter((e) => (e.type === "covers" || e.type === "near") && shown.has(e.from) && byId.get(e.to)?.type === "boq_line");
  const focus = open && shown.has(open) ? open : null;
  const boqEdges = focus ? toBoq.filter((e) => e.from === focus) : [];
  const forms = [...new Set(submits.map((e) => e.from))].map((id) => byId.get(id)!)
    .sort((a, b) => (a.project ?? "").localeCompare(b.project ?? "") || a.label.localeCompare(b.label));
  const boqs = [...new Set(boqEdges.map((e) => e.to))].map((id) => byId.get(id)!)
    .sort((a, b) => a.label.localeCompare(b.label) || parseFloat(a.sizes?.[0] ?? "0") - parseFloat(b.sizes?.[0] ?? "0"));
  const y = new Map<string, number>();
  [forms, lines].forEach((col) => col.forEach((n, i) => y.set(n.id, 40 + i * ROW)));
  const top = Math.max(40, (focus ? y.get(focus)! : 40) - ((boqs.length - 1) * ROW) / 2); // the BOQ lines open around their product line
  boqs.forEach((n, i) => y.set(n.id, top + i * ROW));
  const height = Math.max(70, ...y.values()) + 30;
  const tally = (id: string, type: GEdge["type"]) => toBoq.filter((e) => e.from === id && e.type === type).length;
  const drawn = [...submits, ...boqEdges];
  const linked = new Set(drawn.filter((e) => e.from === picked || e.to === picked).flatMap((e) => [e.from, e.to]));
  const lit = (id: string) => !picked || id === picked || linked.has(id);
  const pick = (n: GNode) => {
    setPicked(picked === n.id ? null : n.id);
    if (n.type === "product_line") setOpen(open === n.id ? null : n.id);
  };
  const choose = (k: string) => { setKind(k); setPicked(null); setOpen(null); };
  const counts = g.summary.product_lines;
  return (
    <section className="sheet" aria-labelledby="graph-title">
      <div className="sheet-head">
        <span className="lab" id="graph-title">The knowledge graph</span>
        <span className="count">
          {Object.values(counts).reduce((a, b) => a + b, 0)} product lines · {g.summary.forms} forms · {g.summary.documents} documents ·
          {" "}{g.summary.came_back} came back from another project
        </span>
      </div>
      <div className="chapters" role="group" aria-label="Kind">
        <button type="button" className={`chapter${kind === "all" ? " on" : ""}`} onClick={() => choose("all")}>All</button>
        {KINDS.map(([k, label]) => (
          <button key={k} type="button" className={`chapter${kind === k ? " on" : ""}`} onClick={() => choose(k)}>
            {label}<span>{counts[k] ?? 0}</span>
          </button>
        ))}
      </div>
      <p className="sheet-note band">
        The forms on the left, the product lines they submitted in the middle, and on the right the BOQ lines each one covers, in
        green, or might cover, in dashed violet: a part is not given on one side, so a person decides. Pick a product line to open
        its BOQ lines and its documents.
      </p>
      {lines.length ? (
        <div className="graph-wrap">
          <svg viewBox={`0 0 1000 ${height}`} className="graph" role="img" aria-label="The knowledge graph of the project's product lines">
            <text x={COL.form} y="20" className="g-head" textAnchor="middle">Forms</text>
            <text x={COL.product_line} y="20" className="g-head" textAnchor="middle">Product lines</text>
            <text x={COL.boq_line} y="20" className="g-head" textAnchor="middle">BOQ lines</text>
            {drawn.map((e, i) => {
              const a = byId.get(e.from)!, b = byId.get(e.to)!;
              const on = !picked || e.from === picked || e.to === picked;
              return <path key={i} d={curve(COL[a.type] + WIDE[a.type] / 2, y.get(a.id)!, COL[b.type] - WIDE[b.type] / 2, y.get(b.id)!)}
                className={`g-edge ${e.type}${on ? "" : " dim"}`} />;
            })}
            {!focus && lines.map((n) => {
              const [c, m] = [tally(n.id, "covers"), tally(n.id, "near")];
              if (!c && !m) return null;
              const [x1, x2, at] = [COL.product_line + WIDE.product_line / 2, COL.boq_line - WIDE.boq_line / 2, y.get(n.id)!];
              return (
                <g key={`tally-${n.id}`} className={`g-tally${lit(n.id) ? "" : " dim"}`} onClick={() => pick(n)} aria-hidden="true">
                  <line x1={x1} y1={at} x2={x2} y2={at} className={`g-edge ${c ? "covers" : "near"}`} />
                  <text x={x2 + 6} y={at + 4}>
                    {c > 0 && <tspan className="g-covers">covers {c}</tspan>}{c > 0 && m > 0 && " · "}
                    {m > 0 && <tspan className="g-near">might cover {m}</tspan>}
                  </text>
                </g>
              );
            })}
            {[...forms, ...lines, ...boqs].map((n) => (
              <g key={n.id} className={`g-node ${n.type}${lit(n.id) ? "" : " dim"}${picked === n.id ? " picked" : ""}`} transform={`translate(${COL[n.type]} ${y.get(n.id)})`}
                onClick={() => pick(n)} role="button" tabIndex={0} aria-label={n.label} aria-pressed={picked === n.id}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(n); } }}>
                <rect x={-WIDE[n.type] / 2} y="-9" width={WIDE[n.type]} height="18" rx="2" />
                <text textAnchor="middle" y="4">{short(n)}</text>
              </g>
            ))}
          </svg>
        </div>
      ) : <p className="empty">No product line of this kind yet.</p>}
      {picked && byId.get(picked) && <Details n={byId.get(picked)!} g={g} byId={byId} />}
    </section>
  );
}

function short(n: GNode) {
  const text = n.type === "form" ? `${n.project === "this project" ? "" : "earlier · "}${n.label}${n.answer ? ` · ${n.answer}` : ""}`
    : n.type === "boq_line" && n.sizes?.length ? `${n.sizes.join(", ")} · ${n.label}` : n.label;   // the sizes tell similar BOQ lines apart
  const max = FITS[n.type];
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function Details({ n, g, byId }: { n: GNode; g: Graph; byId: Map<string, GNode> }) {
  const out = (type: GEdge["type"]) => g.edges.filter((e) => e.from === n.id && e.type === type).map((e) => byId.get(e.to)!);
  const into = (type: GEdge["type"]) => g.edges.filter((e) => e.to === n.id && e.type === type).map((e) => byId.get(e.from)!);
  if (n.type !== "product_line") {
    const lines = n.type === "form" ? out("submits") : into("covers").concat(into("near"));
    return (
      <div className="g-details">
        <span className="lab">{n.type === "form" ? `Form, ${n.project}` : `BOQ line, chapter ${n.sheet}`}</span>
        <h3>{n.label}{n.answer ? ` · answered ${n.answer}` : ""}</h3>
        <p className="fine">{plural(lines.length, "product line", "product lines")}: {lines.map((l) => l.label).join("; ") || "none"}</p>
      </div>
    );
  }
  const forms = into("submits");
  const docs = into("supports");
  const near = [...g.edges.filter((e) => e.type === "near" && (e.from === n.id || e.to === n.id) && byId.get(e.from)?.type === "product_line" && byId.get(e.to)?.type === "product_line")
    .map((e) => byId.get(e.from === n.id ? e.to : e.from)!)];
  return (
    <div className="g-details">
      <span className="lab">Product line · {n.kind}</span>
      <h3>{n.label}</h3>
      <dl className="g-parts">
        {Object.entries(n.parts ?? {}).map(([k, val]) => (<div key={k}><dt>{k}</dt><dd className={val ? "typed" : "unknown"}>{val ?? "not given"}</dd></div>))}
        <div><dt>sizes</dt><dd className="typed">{n.sizes?.join(", ") || "not given"}</dd></div>
      </dl>
      <p className="fine">In {n.projects?.join(" and ")}: {forms.map((f) => `${f.label}${f.answer ? ` (${f.answer})` : ""}`).join(", ")}.</p>
      {docs.length > 0 && <p className="fine">Documents: {docs.map((d) => `${d.label} (${d.kind})`).join("; ")}.</p>}
      <p className="fine">BOQ lines it covers: {out("covers").length}; it might cover: {out("near").length}.</p>
      {near.length > 0 && <p className="fine">Might be the same line as: {near.map((l) => l.label).join("; ")}. A person decides.</p>}
    </div>
  );
}
