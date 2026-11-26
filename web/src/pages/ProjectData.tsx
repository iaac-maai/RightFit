// A project's own data: its MAF packages and the BOQ lines (a package's review is in Review.tsx, the rules in Rules.tsx).
// Imported from the laptop (web/scripts/import_project.py); a locked project opens with the team password.
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, go, navigate, post } from "../api";
import { AddPackage } from "./AddPackage";
import { plural } from "../format";
import type { BoqLine, PackageRow } from "../types";
import { key, type Entry, type Status } from "../../worker/register";

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
  const { data, error } = useData<{ packages: PackageRow[]; note?: string; mayAdd?: boolean }>(`/api/projects/${projectId}/packages`);
  const [adding, setAdding] = useState(false);
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
        {data.mayAdd && <button type="button" className="btn p small" onClick={() => setAdding(true)}>Add a package</button>}
      </div>
      {all.some((p) => !p.letter) && (
        <p className="sheet-note band">A package waits to be read until RightFit's reader has been through it: the AI reads every value with its page, then the checks run and the review appears here. For now the reader runs on the team's laptop.</p>
      )}
      <AddPackage projectId={projectId} open={adding} onClose={() => setAdding(false)}
        onDone={(code) => { setAdding(false); navigate(`/p/${projectId}/packages/${code}`); }} />
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

// Where a BOQ line stands (MAF-36c), from the forms that reach it; the order is the order of the filters
const STATUS: [Status, string, string][] = [
  ["approved", "Approved", "a form of this project covers it and got A or B"],
  ["submitted", "Submitted", "a form of this project covers it and waits for its answer"],
  ["returned", "Returned", "the forms that cover it got C"],
  ["approved_before", "Approved before", "not submitted here; the same product line got A or B in your earlier project"],
  ["might", "Perhaps covered", "a form might cover it, a part is not given on one side: you decide"],
  ["none", "No form", "RightFit reads this kind of line and found no form for it"],
  ["unread", "Not matched yet", "RightFit does not match this kind of line to forms yet"],
];

export function Boq({ projectId }: { projectId: string }) {
  const { data, error } = useData<{ lines: BoqLine[]; note?: string; register?: Record<string, Entry>; graph?: boolean; earlier?: boolean }>(`/api/projects/${projectId}/boq`);
  const [sheet, setSheet] = useState("");
  const [find, setFind] = useState("");
  const [only, setOnly] = useState<Status | "">("");
  const lines = data?.lines ?? [];
  const sheets = useMemo(() => {
    const counts = new Map<string, number>();
    for (const l of lines) counts.set(l.sheet, (counts.get(l.sheet) ?? 0) + 1);
    return [...counts.entries()];
  }, [lines]);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  if (data.note) return <p className="sheet-note">{data.note}</p>;
  const entry = (l: BoqLine): Entry => data.register?.[key(l)] ?? { status: "unread", forms: [] };
  const inSheet = lines.filter((l) => (!sheet || l.sheet === sheet) && (!find || `${l.nr ?? ""} ${l.text} ${l.producer ?? ""}`.toLowerCase().includes(find.toLowerCase())));
  const counts = new Map<Status, number>();
  for (const l of inSheet) counts.set(entry(l).status, (counts.get(entry(l).status) ?? 0) + 1);
  const shown = inSheet.filter((l) => !only || entry(l).status === only);
  const statuses = STATUS.filter(([s]) => s !== "approved_before" || data.earlier);
  return (
    <section className="sheet" aria-label="The BOQ">
      <div className="sheet-head">
        <span className="lab">The bill of quantities</span>
        <span className="count">{plural(lines.length, "line", "lines")} in {plural(sheets.length, "chapter", "chapters")}; prices stay on the laptop</span>
      </div>
      <p className="sheet-note band">
        Each line shows whether a form covers it, and the answer that form got. RightFit finds the forms with fixed rules, no AI:
        cables, pipes, valves and boilers by their product line, and the products of the packages it has read by their BOQ line.
        A reviewer records a form's answer on its package; until then the line shows as submitted.
        {!data.graph && " This project's product lines come with the next import from the laptop."}
      </p>
      <div className="chapters" role="group" aria-label="Chapters">
        <button type="button" className={`chapter${sheet ? "" : " on"}`} onClick={() => setSheet("")}>All</button>
        {sheets.map(([s, n]) => (
          <button key={s} type="button" className={`chapter${sheet === s ? " on" : ""}`} onClick={() => setSheet(s)}>{s} <span>{n}</span></button>
        ))}
      </div>
      <div className="chapters reg-filters" role="group" aria-label="Where the lines stand">
        <button type="button" className={`chapter${only ? "" : " on"}`} onClick={() => setOnly("")}>Every line<span>{inSheet.length}</span></button>
        {statuses.map(([s, label, hint]) => (
          <button key={s} type="button" className={`chapter reg-${s}${only === s ? " on" : ""}`} title={hint} aria-pressed={only === s}
            onClick={() => setOnly(only === s ? "" : s)}><i className="reg-dot" aria-hidden="true" />{label}<span>{counts.get(s) ?? 0}</span></button>
        ))}
      </div>
      <div className="filters">
        <input type="search" aria-label="Find a line" placeholder="Find a line, a product or a code" value={find} onChange={(e) => setFind(e.target.value)} />
      </div>
      <div className="table-wrap">
        <table className="table reg-table">
          <thead><tr><th>Where it stands</th><th>Chapter</th><th>Row</th><th>No.</th><th>What the line asks</th><th>Unit</th><th>Quantity</th><th>Producer</th><th>Forms</th></tr></thead>
          <tbody>
            {shown.map((l) => {
              const e = entry(l);
              const [, label, hint] = STATUS.find(([s]) => s === e.status)!;
              return (
                <tr key={`${l.file}-${l.sheet}-${l.row}`} className={`reg-${e.status}`}>
                  <td className="nowrap"><span className="reg-chip" title={hint}><i className="reg-dot" aria-hidden="true" />{label}</span></td>
                  <td className="nowrap">{l.sheet}</td>
                  <td>{l.row}</td>
                  <td className="typed small">{l.nr ?? ""}</td>
                  <td className="wrap">{l.text}</td>
                  <td>{l.unit ?? ""}</td>
                  <td className="typed small">{l.qty ?? ""}</td>
                  <td>{l.producer ?? ""}</td>
                  <td className="reg-forms">
                    {e.forms.map((f) => {
                      const name = <>{f.form}{f.answer ? <i className={`letter sm ${f.answer}`} aria-label={`answered ${f.answer}`}>{f.answer}</i> : <em> waiting</em>}</>;
                      const path = f.code ? `/p/${projectId}/packages/${f.code}` : "";
                      return (
                        <span key={`${f.form}|${f.how}`} className={`reg-form${f.how === "might" ? " might" : ""}`}
                          title={f.earlier ? "earlier project" : f.how === "might" ? "might cover it" : f.how === "read" ? "matched on the read package" : "covers it"}>
                          {path ? <a href={path} onClick={go(path)}>{name}</a> : name}{f.earlier && <em> earlier project</em>}
                        </span>
                      );
                    })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!shown.length && <p className="empty">No line matches.</p>}
    </section>
  );
}
