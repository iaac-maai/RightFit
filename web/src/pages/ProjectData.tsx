// A project's own data: its MAF packages and the BOQ lines (a package's review is in Review.tsx, the rules in Rules.tsx).
// Imported from the laptop (web/scripts/import_project.py); a locked project opens with the team password.
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, go, post } from "../api";
import { plural } from "../format";
import type { BoqLine, PackageRow } from "../types";

export const fileUrl = (projectId: string, code: string, name: string, page?: number) =>
  `/api/projects/${projectId}/files/${code}/${encodeURIComponent(name)}${page ? `#page=${page}` : ""}`;

export function useData<T>(path: string) {
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
