// A project's own data: its MAF packages, the files of each, RightFit's draft review of those already read, and the
// BOQ lines. Imported from the laptop (web/scripts/import_project.py); a locked project opens with the team password.
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, go, post } from "../api";
import { day, plural } from "../format";
import type { BoqLine, Finding, PackageData, PackageRow } from "../types";

const fileUrl = (projectId: string, code: string, name: string, page?: number) =>
  `/api/projects/${projectId}/files/${code}/${encodeURIComponent(name)}${page ? `#page=${page}` : ""}`;

function useData<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setData(null);
    api<T>(path).then(setData, (err: Error) => setError(err.message));
  }, [path]);
  return { data, error };
}

const Letter = ({ letter }: { letter: string | null }) =>
  letter ? <i className={`letter sm ${letter}`} aria-label={`Draft answer ${letter}`}>{letter}</i> : <span className="meta">not read yet</span>;

export function TeamLock({ name, onUnlocked }: { name: string; onUnlocked: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("password") ?? "");
    setBusy(true);
    setError("");
    try {
      await post("/api/team/unlock", { password });
      onUnlocked();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <div className="screen narrow">
      <form className="sheet lock" onSubmit={(e) => void submit(e)}>
        <span className="lab">Locked project</span>
        <h1 className="typed">{name}</h1>
        <p className="sheet-note">This project holds real packages and its BOQ. Besides your account, it opens with the team password, for 7 days on this browser.</p>
        <label className="field">
          <span className="lab">Team password</span>
          <input name="password" type="password" autoComplete="off" required autoFocus />
        </label>
        {error && <p className="err" role="alert">{error}</p>}
        <div className="actions"><button className="btn p" disabled={busy}>Open the project</button></div>
      </form>
    </div>
  );
}

export function Packages({ projectId }: { projectId: string }) {
  const { data, error } = useData<{ packages: PackageRow[]; note?: string }>(`/api/projects/${projectId}/packages`);
  const [discipline, setDiscipline] = useState("");
  const [find, setFind] = useState("");
  const all = data?.packages ?? [];
  const disciplines = useMemo(() => [...new Set(all.map((p) => p.discipline).filter(Boolean))].sort(), [all]);
  const shown = all.filter((p) => (!discipline || p.discipline === discipline)
    && (!find || `${p.formNo} ${p.code} ${p.items.join(" ")}`.toLowerCase().includes(find.toLowerCase())));
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  if (data.note) return <p className="sheet-note">{data.note}</p>;
  const read = all.filter((p) => p.letter);
  return (
    <section className="sheet" aria-label="Packages">
      <div className="sheet-head">
        <span className="lab">The project's packages</span>
        <span className="count">{plural(all.length, "package", "packages")}, {read.length} read by RightFit</span>
      </div>
      <div className="filters">
        <select aria-label="Discipline" value={discipline} onChange={(e) => setDiscipline(e.target.value)}>
          <option value="">All disciplines</option>
          {disciplines.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <input type="search" aria-label="Find a form or a product" placeholder="Find a form or a product" value={find} onChange={(e) => setFind(e.target.value)} />
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Form</th><th>Rev</th><th>Products</th><th>Discipline</th><th>Files</th><th>Pages</th><th>RightFit's draft</th></tr></thead>
          <tbody>
            {shown.map((p) => {
              const path = `/p/${projectId}/packages/${p.code}`;
              return (
                <tr key={p.code}>
                  <td><a className="typed" href={path} onClick={go(path)}>{p.formNo}</a></td>
                  <td>{p.revision}</td>
                  <td className="wrap">{p.items.join(", ")}</td>
                  <td>{p.discipline || "—"}</td>
                  <td>{p.files}</td>
                  <td>{p.pages ?? "—"}</td>
                  <td className="draft">
                    <Letter letter={p.letter} />
                    {p.letter && <span className="meta">{p.label}; {plural(p.problems ?? 0, "problem", "problems")}, {plural(p.questions ?? 0, "question", "questions")}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!shown.length && <p className="empty">No package matches.</p>}
    </section>
  );
}

// "file.pdf, p. 2" in a finding's sources becomes a link to that page of the file, when the package holds the file
function Source({ text, projectId, code, files }: { text: string; projectId: string; code: string; files: Set<string> }) {
  const m = text.match(/^(.*), p\. (\d+)$/);
  if (m && files.has(m[1])) {
    return <a href={fileUrl(projectId, code, m[1], Number(m[2]))} target="_blank" rel="noreferrer">{m[1]}, page {m[2]}</a>;
  }
  return <span>{text}</span>;
}

function Findings({ title, items, projectId, code, files }: { title: string; items: Finding[]; projectId: string; code: string; files: Set<string> }) {
  if (!items.length) return null;
  return (
    <section className="sheet" aria-label={title}>
      <div className="sheet-head"><span className="lab">{title}</span><span className="count">{items.length}</span></div>
      <ol className="findings">
        {items.map((f, i) => (
          <li key={i}>
            <div className="finding-head">
              <span className="chip">{f.check}</span>
              <b>{f.check_name}</b>
              {f.product && <span className="meta">{f.product}</span>}
              {!f.confirmed && <span className="un-tag">on readings nobody has confirmed yet</span>}
            </div>
            <p>{f.reason}</p>
            {(f.sources?.length || f.rules?.length) ? (
              <div className="finding-meta">
                {f.sources?.map((s, j) => <Source key={j} text={s} projectId={projectId} code={code} files={files} />)}
                {f.rules?.map((r) => <span key={r.id} className="meta">rule {r.id}, {r.status.replace(/_/g, " ")}</span>)}
              </div>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function PackageView({ projectId, code }: { projectId: string; code: string }) {
  const { data, error } = useData<PackageData>(`/api/projects/${projectId}/packages/${code}`);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const { package: p, files, review } = data;
  const names = new Set(files.map((f) => f.name));
  return (
    <>
      <a className="back" href={`/p/${projectId}/packages`} onClick={go(`/p/${projectId}/packages`)}>All packages</a>
      <header className="project-head">
        <div className="fld title"><span className="lab">Form</span><h2 className="typed big-title">{p.formNo} rev {p.revision}</h2></div>
        <div className="fld"><span className="lab">Discipline</span><span className="typed">{p.discipline || "—"}</span></div>
        <div className="fld"><span className="lab">Products</span><span className="typed">{p.items.join(", ")}</span></div>
      </header>

      {review ? (
        <section className="sheet draft-sheet" aria-label="RightFit's draft answer">
          <div className="draft-answer">
            <i className={`letter ${review.draft_answer.letter}`}>{review.draft_answer.letter}</i>
            <div>
              <span className="lab">RightFit's draft answer</span>
              <b>{review.draft_answer.label}</b>
              <span className="meta">
                {plural(review.counts.problems ?? 0, "problem", "problems")}, {plural(review.counts.questions ?? 0, "question", "questions")};
                {" "}{review.counts.to_confirm ?? 0} of {review.counts.readings ?? 0} readings still to confirm.
                {" "}Drafted on the laptop{p.reviewedAt ? ` on ${day(p.reviewedAt)}` : ""}, for a review on {day(review.review_date)}. A person decides.
              </span>
            </div>
          </div>
        </section>
      ) : (
        <p className="sheet-note band-note">RightFit has not read this package yet: its files are here, the draft comes once it is read.</p>
      )}

      {review && <Findings title="Problems" items={review.problems} projectId={projectId} code={code} files={names} />}
      {review && <Findings title="Questions for a person" items={review.questions} projectId={projectId} code={code} files={names} />}

      <section className="sheet" aria-label="The package's files">
        <div className="sheet-head"><span className="lab">The package's files</span><span className="count">{files.length}</span></div>
        <div className="rows">
          {files.map((f) => {
            const listed = review?.documents.find((d) => d.file === f.name);
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
      </section>

      {review && (
        <details className="sheet answer-text">
          <summary className="sheet-head"><span className="lab">The draft answer's text</span></summary>
          <pre>{review.answer_text}</pre>
        </details>
      )}
    </>
  );
}

export function Boq({ projectId }: { projectId: string }) {
  const { data, error } = useData<{ lines: BoqLine[]; note?: string }>(`/api/projects/${projectId}/boq`);
  const [sheet, setSheet] = useState("");
  const [find, setFind] = useState("");
  const lines = data?.lines ?? [];
  const sheets = useMemo(() => {
    const counts = new Map<string, number>();
    for (const l of lines) counts.set(l.sheet, (counts.get(l.sheet) ?? 0) + 1);
    return [...counts.entries()];
  }, [lines]);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  if (data.note) return <p className="sheet-note">{data.note}</p>;
  const shown = lines.filter((l) => (!sheet || l.sheet === sheet) && (!find || `${l.nr ?? ""} ${l.text} ${l.producer ?? ""}`.toLowerCase().includes(find.toLowerCase())));
  return (
    <section className="sheet" aria-label="The BOQ">
      <div className="sheet-head">
        <span className="lab">The bill of quantities</span>
        <span className="count">{plural(lines.length, "line", "lines")} in {plural(sheets.length, "chapter", "chapters")}; prices stay on the laptop</span>
      </div>
      <div className="chapters" role="group" aria-label="Chapters">
        <button type="button" className={`chapter${sheet ? "" : " on"}`} onClick={() => setSheet("")}>All</button>
        {sheets.map(([s, n]) => (
          <button key={s} type="button" className={`chapter${sheet === s ? " on" : ""}`} onClick={() => setSheet(s)}>{s} <span>{n}</span></button>
        ))}
      </div>
      <div className="filters">
        <input type="search" aria-label="Find a line" placeholder="Find a line, a product or a code" value={find} onChange={(e) => setFind(e.target.value)} />
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Chapter</th><th>Row</th><th>No.</th><th>What the line asks</th><th>Unit</th><th>Quantity</th><th>Producer</th></tr></thead>
          <tbody>
            {shown.map((l) => (
              <tr key={`${l.file}-${l.sheet}-${l.row}`}>
                <td className="nowrap">{l.sheet}</td>
                <td>{l.row}</td>
                <td className="typed small">{l.nr ?? ""}</td>
                <td className="wrap">{l.text}</td>
                <td>{l.unit ?? ""}</td>
                <td className="typed small">{l.qty ?? ""}</td>
                <td>{l.producer ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!shown.length && <p className="empty">No line matches.</p>}
    </section>
  );
}
