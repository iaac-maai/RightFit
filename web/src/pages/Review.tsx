// One package's review online, in the laptop's three steps (app/review/views/review.js): the problems with what passed,
// what the AI read page by page, and the draft answer; the document opens beside them. Everything here comes from
// the laptop's checks and the reviewer's decisions taken there; online it is read, not changed, until the checks run
// online as well (spec/features/rightfit_online.md, section 11).
import { createContext, useContext, useState, type MouseEvent, type SyntheticEvent } from "react";
import { go } from "../api";
import { day, plural } from "../format";
import { RULE_STATUS, STATUS_RULE, groups, passed, placeOf, plainReason, readingPages, shown, why, type Place, type Row } from "../review";
import type { CheckResult, Match, PackageData, PackageFile, PackageReview, Reading, ReviewDoc } from "../types";
import { fileUrl, useData } from "./ProjectData";

export type Step = "problems" | "readings" | "answer";
const MAKER = "the manufacturer's copy";
const WIDE = "(min-width: 1180px)"; // the document opens beside the list only when both fit
const pad = (n: number) => String(n).padStart(2, "0");

// The open document, and how a page link opens one: beside the list on a wide screen, in a new tab otherwise
interface PaneApi {
  isDoc: (file: string) => boolean; url: (file: string, page?: number) => string;
  open: (place: Place) => void; show: (e: MouseEvent, place: Place) => void;
}
const Pane = createContext<PaneApi>({ isDoc: () => false, url: () => "", open: () => undefined, show: () => undefined });

function Linked({ text, name }: { text: string; name?: string }) {
  const parts = text.split(/(https?:\/\/[^\s)<]+)/g); // the links sit at the odd places
  return <>{parts.map((p, i) => (i % 2 ? <a key={i} href={p} target="_blank" rel="noreferrer">{name ?? p}</a> : p))}</>;
}

function PageLink({ file, page }: { file: string; page: number | string | null }) {
  const pane = useContext(Pane);
  if (!pane.isDoc(file)) return <span className="goto meta">form</span>;
  const n = Number(page) || 1;
  return <a className="goto" href={pane.url(file, n)} target="_blank" rel="noreferrer" onClick={(e) => pane.show(e, { file, page: n })}>p. {n}</a>;
}

// A value as the AI read it (violet, dashed) or as a person confirmed it (ink)
const Typed = ({ value, unit, ok }: { value: Reading["value"]; unit: string | null; ok: boolean }) =>
  value == null || value === "" ? <span className="typed none">not found</span>
    : <span className="typed"><span className={ok ? "co" : "un"}>{shown(value, unit)}</span></span>;

const Mark = ({ ok, by }: { ok: boolean; by?: string | null }) => (
  <span className={`mark${ok ? " y" : ""}`} title={ok ? `Confirmed${by ? ` by ${by}` : ""}` : "As the AI read it, not confirmed yet"}
    aria-label={ok ? "confirmed" : "not confirmed yet"}>{ok ? "✓" : ""}</span>
);

export function PackageView({ projectId, code, step }: { projectId: string; code: string; step: Step }) {
  const { data, error } = useData<PackageData>(`/api/projects/${projectId}/packages/${code}`);
  const [place, setPlace] = useState<Place | null>(null);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const { package: p, files, review: v } = data;
  const back = <a className="back" href={`/p/${projectId}/packages`} onClick={go(`/p/${projectId}/packages`)}>All packages</a>;
  if (!v || !v.results) {
    return (
      <>
        {back}
        <p className="band-note">{v ? "This draft is being updated from the laptop: open it again in a minute."
          : "RightFit has not read this package yet: its files are here, the draft comes once it is read."}</p>
        <Files projectId={projectId} code={code} files={files} docs={[]} />
      </>
    );
  }
  const docs = new Set(v.documents.map((d) => d.file));
  const url = (file: string, page?: number) => fileUrl(projectId, code, file, /\.pdf$/i.test(file) ? page : undefined);
  const pane: PaneApi = {
    isDoc: (file) => docs.has(file),
    url,
    open: setPlace, // the pane shows only on a wide screen (styles.css); on a narrow one the links open a tab
    show: (e, at) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || !window.matchMedia(WIDE).matches) return;
      e.preventDefault();
      setPlace(at);
    },
  };
  const open = place ?? (v.documents[0] ? { file: v.documents[0].file, page: 1 } : null);
  const base = `/p/${projectId}/packages/${code}`;
  const c = v.counts;
  const ai = v.ai_findings.length;
  const steps: [Step, string, string][] = [
    ["problems", "1 Problems", `${plural(c.problems, "problem", "problems")}, ${plural(c.questions, "question", "questions")}${ai ? `, ${ai} AI` : ""}`],
    ["readings", "2 Readings", c.to_confirm ? `${c.to_confirm} of ${c.readings} to confirm` : "all confirmed"],
    ["answer", "3 Answer", `${plural(v.answer.lines.length, "comment", "comments")}`],
  ];
  const pages = v.documents.reduce((n, d) => n + d.pages, 0);

  return (
    <Pane.Provider value={pane}>
      {back}
      <header className="project-head">
        <div className="fld title"><span className="lab">Form</span><h2 className="typed big-title">MAF {v.form.form_no} rev {v.form.revision}</h2></div>
        <div className="fld"><span className="lab">Package</span><span className="typed">{plural(v.items.length, "product", "products")}, {files.length} files, {pages} pages</span></div>
        <div className="fld"><span className="lab">Discipline</span><span className="typed">{p.discipline || "—"}</span></div>
      </header>

      <section className="sheet draft-sheet" aria-label="RightFit's draft answer">
        <div className="draft-answer">
          <i className={`letter ${v.status.letter}`}>{v.status.letter}</i>
          <div>
            <span className="lab">RightFit's draft answer, not an answer yet</span>
            <b>{v.status.label}</b>
            <span className="meta">
              Drafted on the laptop{p.reviewedAt ? ` on ${day(p.reviewedAt)}` : ""} for a review dated {day(v.review)}.
              {" "}Nobody has answered this form yet: the reviewer checks the draft, changes it and signs it.
            </span>
          </div>
        </div>
        <details className="why-b">
          <summary>Why {v.status.letter}?</summary>
          <p>{STATUS_RULE[v.status.letter]}</p>
          <ul>{why(v).map((line) => <li key={line}><Linked text={line} name={MAKER} /></li>)}</ul>
        </details>
      </section>
      <p className="hold">
        {c.to_confirm ? `${c.to_confirm} of ${c.readings} readings are still as the AI read them, so the results are what the checks would say once a person confirms them. ` : ""}
        Online you read the review; the ticks and decisions are made in RightFit on the laptop for now, and come here with the next import.
      </p>

      <nav className="steps" aria-label="Review steps">
        {steps.map(([key, label, sub]) => (
          <a key={key} href={`${base}/${key}`} onClick={go(`${base}/${key}`)} aria-current={step === key ? "page" : undefined}>
            {label}<small>{sub}</small>
          </a>
        ))}
      </nav>

      <div className="review-work">
        <div className="review-list">
          {step === "problems" && <Problems v={v} />}
          {step === "readings" && <Readings v={v} />}
          {step === "answer" && <Answer v={v} projectId={projectId} />}
        </div>
        {open && <Document doc={v.documents.find((d) => d.file === open.file)} place={open} url={url} />}
      </div>

      <Files projectId={projectId} code={code} files={files} docs={v.documents} />
    </Pane.Provider>
  );
}

// ------------------------------------------------------------------ step 1, the problems
function Problems({ v }: { v: PackageReview }) {
  const list = groups(v);
  const ok = passed(v);
  const word = (r: CheckResult) => (r.verdict === "info" ? "Information" : r.confirmed ? "Passed" : "Would pass");
  const name = (id: string | null) => v.items.find((i) => i.id === id)?.name;
  return (
    <>
      {list.map((g) => (
        <section key={g.id} className="sheet group" aria-label={g.name}>
          <div className="sheet-head">
            <span className="group-name">{g.name}{g.model && <span className="typed">{g.model}</span>}</span>
            <span className="count">{g.rows.length}</span>
          </div>
          {g.rows.map((row, i) => <Finding key={row.id} v={v} row={row} first={i === 0 && g === list[0]} />)}
        </section>
      ))}
      {!list.length && <p className="band-note">No problems. Every check passed or is only for information.</p>}
      <details className="sheet passed">
        <summary className="sheet-head"><span className="lab">What passed or is only for information</span><span className="count">{ok.length}</span></summary>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Check</th><th>About</th><th>Result</th><th>Why</th></tr></thead>
            <tbody>
              {ok.map((r) => (
                <tr key={r.key}>
                  <td className="nowrap">{r.check_name}</td>
                  <td>{name(r.item) || r.doc || "Package"}</td>
                  <td className="nowrap">{word(r)}</td>
                  <td className="wrap"><Linked text={plainReason(r.reason)} name={MAKER} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

function Finding({ v, row, first }: { v: PackageReview; row: Row; first: boolean }) {
  const pane = useContext(Pane);
  const at = placeOf(v, row);
  const opened = (e: SyntheticEvent<HTMLDetailsElement>) => {
    if (e.currentTarget.open && at) pane.open(at); // opening a problem shows its page beside it, as on the laptop
  };
  if (row.kind === "ai") {
    const f = row.f;
    const state = { suggested: "AI, not decided", accepted: "AI, in the answer", rejected: "AI, not relevant" }[f.status];
    return (
      <details className={`finding${f.status === "rejected" ? " off" : ""}`} onToggle={opened}>
        <summary><span className="tag ai">{state}</span><b>{f.title}</b></summary>
        <div className="finding-body">
          <p className="say">{f.finding}</p>
          {f.evidence.map((e, i) => (
            <div key={i} className="f"><span className="lab">Quoted by the AI</span><span className="typed"><span className="un">{e.quote}</span></span><PageLink file={e.source} page={e.page} /></div>
          ))}
          <p className="ai-note">AI suggestion. No rule checks this and it changes no check result. It goes into the answer only if the reviewer adds it.</p>
          <p className="fine">Comment it would add: {f.suggested_comment}</p>
          {f.status === "rejected" && f.note && <p className="fine">Why it is not relevant: {f.note}</p>}
        </div>
      </details>
    );
  }
  const r = row.r;
  const d = r.doc ? v.documents.find((x) => x.file === r.doc) : undefined;
  const kept = v.decisions[r.key]?.decision === "kept";
  const tag = r.dismissed ? <span className="tag">Not a problem</span> : r.verdict === "unclear" ? <span className="tag q">Question</span>
    : <span className="tag p">Problem</span>;
  const sources = !r.evidence.length && !d ? r.sources : [];
  return (
    <details className={`finding${r.dismissed ? " off" : ""}`} open={first} onToggle={opened}>
      <summary>
        {tag}<b>{r.title}</b>
        {!r.confirmed && !r.dismissed && <span className="un-tag">on readings nobody has confirmed yet</span>}
        {kept && <span className="meta">kept in the answer</span>}
      </summary>
      <div className="finding-body">
        <p className="say"><Linked text={r.comment || plainReason(r.reason)} name={MAKER} /></p>
        {d && (
          <div className="f"><span className="lab">Read as</span>
            <span className="typed"><span className={d.status === "verified" ? "co" : "un"}>{d.type}{d.covers.length ? `, covers ${d.covers.join("; ")}` : ""}</span></span>
            <PageLink file={d.file} page={1} /><Mark ok={d.status === "verified"} />
          </div>
        )}
        {r.evidence.map((e) => (
          <div key={`${e.item}|${e.key}`} className="f"><span className="lab">{e.what}</span><Typed value={e.value} unit={e.unit} ok={e.status === "verified"} />
            <PageLink file={e.source} page={e.page} /><Mark ok={e.status === "verified"} /></div>
        ))}
        {sources.map((s) => {
          const m = /^(.*), p\. (\S+)$/.exec(s);
          return <div key={s} className="f"><span className="lab">Where</span><span className="typed small">{m ? m[1] : s}</span>{m && <PageLink file={m[1]} page={m[2]} />}</div>;
        })}
        {r.dismissed && <p className="gone">The reviewer marked this as not a problem: {r.dismissed}. It is left out of the answer.</p>}
        <details className="why">
          <summary>Why this was raised</summary>
          <p><Linked text={plainReason(r.reason)} name={MAKER} /></p>
          {r.rules.length > 0 && (
            <dl>
              {r.rules.map((u) => (
                <div key={u.id}>
                  <dt>Rule {u.id}</dt>
                  <dd>{u.text}{u.source ? ` (${u.source})` : ""}; {RULE_STATUS[u.status] ?? u.status.replace(/_/g, " ")}.
                    {u.url && <> <a href={u.url} target="_blank" rel="noreferrer">Open the text</a></>}</dd>
                </div>
              ))}
            </dl>
          )}
        </details>
      </div>
    </details>
  );
}

// ------------------------------------------------------------------ step 2, what the AI read, page by page
function Readings({ v }: { v: PackageReview }) {
  const pane = useContext(Pane);
  const { docs, form, missing } = readingPages(v);
  const valueLine = (x: Reading) => (
    <div key={`${x.item}|${x.key}`} className="v">
      <Mark ok={x.status === "verified"} by={x.checked_by} />
      <span>{x.what}<small>{x.product}</small></span>
      <span><Typed value={x.value} unit={x.unit} ok={x.status === "verified"} />
        {x.status === "verified" && <span className="by">{x.checked_by || "reviewer"}{x.verified_on ? `, ${day(x.verified_on)}` : ""}</span>}</span>
    </div>
  );
  const matchLine = (d: ReviewDoc, m: Match) => (
    <div key={`m|${d.file}|${m.item}`} className="v">
      <Mark ok={m.status === "verified"} />
      <span>Covers this product<small>{m.product}</small></span>
      <span className="typed"><span className={m.status === "verified" ? "co" : "un"}>{m.kind}</span></span>
    </div>
  );
  return (
    <section className="sheet readings" aria-label="What the AI read">
      <p className="hold">Each line is what the AI read, with the page it came from. A person confirms it in RightFit on the laptop; until then, every check that rests on it stays a question.</p>
      {docs.map(({ d, pages, loose }) => (
        <div key={d.file}>
          <div className="dg"><b>{pad(d.no)} · {d.file}</b><span>{d.type} · {plural(d.pages, "page", "pages")}</span></div>
          <div className="v">
            <Mark ok={d.status === "verified"} />
            <span>What this document is<small>Listed in the form as {d.listed_as || "not listed"}</small></span>
            <span className="typed"><span className={d.status === "verified" ? "co" : "un"}>{d.type}</span></span>
          </div>
          {loose.matches.map((m) => matchLine(d, m))}
          {loose.values.map(valueLine)}
          {pages.map((pg) => (
            <div key={pg.page}>
              <div className="pgh">
                <a href={pane.url(d.file, pg.page)} target="_blank" rel="noreferrer" onClick={(e) => pane.show(e, { file: d.file, page: pg.page })}>Page {pg.page}</a>
              </div>
              {pg.values.map(valueLine)}
              {pg.matches.map((m) => matchLine(d, m))}
            </div>
          ))}
        </div>
      ))}
      {form.length > 0 && (
        <>
          <div className="dg"><b>From the form</b><span>The MAF form is a spreadsheet, so it has no page to show</span></div>
          {form.map(valueLine)}
        </>
      )}
      {missing.length > 0 && (
        <>
          <div className="dg"><b>Not found in the documents</b><span>A person agrees, or finds it, on the laptop</span></div>
          {missing.map(valueLine)}
        </>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ step 3, the draft answer and what was checked
function Answer({ v, projectId }: { v: PackageReview; projectId: string }) {
  const [copied, setCopied] = useState("");
  const c = v.counts;
  const used = new Map(v.results.flatMap((r) => r.rules).map((u) => [u.id, u.status]));
  const legal = [...used.values()].filter((s) => ["verified_official", "verified_secondary", "to_confirm"].includes(s));
  const official = legal.filter((s) => s === "verified_official").length;
  const open = [...new Set(v.results.filter((r) => r.verdict === "unclear").map((r) => plainReason(r.reason)))];
  const copy = () => navigator.clipboard.writeText(v.answer.text).then(() => setCopied("Copied."), () => setCopied("The browser did not allow copying; select the text instead."));
  return (
    <>
      <article className="sheet letter-sheet" aria-label="The draft answer">
        <div className="lh">
          <h2>MAF {v.form.form_no} rev {v.form.revision}: {v.status.label} ({v.status.letter})</h2>
          <button type="button" className="btn" onClick={() => void copy()}>Copy the draft</button>
        </div>
        {copied && <p className="fine" role="status">{copied}</p>}
        {v.answer.lines.length ? <ol>{v.answer.lines.map((line, i) => <li key={i}><Linked text={line} /></li>)}</ol> : <p className="empty">No comments.</p>}
        <p className="sign">Drafted by RightFit from the checks and the reviewer's decisions. A person checks it and signs it; the tool certifies nothing.</p>
      </article>
      <section className="sheet checked" aria-label="What RightFit checked">
        <div className="sheet-head"><span className="lab">What RightFit checked</span></div>
        <div className="checked-body">
          <p>
            The documents, the values and the reviewers' checklist, against EU rules and the rules for {v.location === "ES" ? "Spain" : "Romania"}.
            {" "}{official} of the {legal.length} legal rules used here {official === 1 ? "was" : "were"} read in the official text, so this is not a statement of compliance.
            {" "}<a href={`/p/${projectId}/rules`} onClick={go(`/p/${projectId}/rules`)}>See the rules</a>
          </p>
          <p>Certificates were checked for {day(v.review)}, the review date, and for {day(v.delivery)}, the expected delivery.</p>
          <span className="lab">The result</span>
          <ul>
            <li>{c.passed} passed on values a person confirmed</li>
            <li>{c.would_pass} would pass once a person confirms the readings</li>
            <li>{plural(c.problems, "problem", "problems")}</li>
            <li>{plural(c.questions, "question", "questions")}</li>
          </ul>
          {open.length > 0 && (
            <>
              <span className="lab">What it could not check</span>
              <ul>{open.map((t) => <li key={t}><Linked text={t} name={MAKER} /></li>)}</ul>
            </>
          )}
          {v.notes.length > 0 && (
            <>
              <span className="lab">Notes the AI left while reading the package</span>
              <ul className="ai-notes">{v.notes.map((t) => <li key={t}>{t}</li>)}</ul>
            </>
          )}
        </div>
      </section>
    </>
  );
}

// ------------------------------------------------------------------ the document beside the work, and the package's files
function Document({ doc, place, url }: { doc: ReviewDoc | undefined; place: Place; url: (file: string, page?: number) => string }) {
  const pdf = /\.pdf$/i.test(place.file);
  const fit = `${url(place.file, place.page)}&view=FitH&navpanes=0`; // the page across the pane, without the thumbnails
  return (
    <aside className="doc-pane sheet" aria-label="The document">
      <div className="sheet-head">
        <span className="typed small grow">{doc ? `${pad(doc.no)} · ` : ""}{place.file}</span>
        {pdf && <span className="meta">page {place.page}</span>}
        <a className="meta" href={url(place.file, place.page)} target="_blank" rel="noreferrer">Open in a new tab</a>
      </div>
      {place.own === false && <p className="sheet-note band">No page in this package shows this, so the product's data sheet is open.</p>}
      {pdf ? <iframe key={`${place.file}#${place.page}`} src={fit} title={`${place.file}, page ${place.page}`} />
        : <p className="empty">This file is not a PDF, so it opens in a new tab.</p>}
    </aside>
  );
}

function Files({ projectId, code, files, docs }: { projectId: string; code: string; files: PackageFile[]; docs: ReviewDoc[] }) {
  return (
    <details className="sheet answer-text">
      <summary className="sheet-head"><span className="lab">The package's files</span><span className="count">{files.length}</span></summary>
      <div className="rows">
        {files.map((f) => {
          const listed = docs.find((d) => d.file === f.name);
          return (
            <a key={f.name} className="row file-row" href={fileUrl(projectId, code, f.name)} target="_blank" rel="noreferrer">
              <span className="typed grow">{f.name}</span>
              {listed && <span className="meta">{listed.type}</span>}
              <span className="meta">{f.pages ? plural(f.pages, "page", "pages") : `${Math.max(1, Math.round(f.size / 1024))} KB`}</span>
            </a>
          );
        })}
        {!files.length && <p className="empty">No file of this package is online.</p>}
      </div>
    </details>
  );
}
