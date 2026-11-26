// The project's Fit check (spec/features/revit_link.md): the checks sent from the fit check in Revit, the pump sets
// with the status of their values, the set the reviewers choose, and this person's linked computers. The checks run in
// Revit; this page shows what they found and never changes it.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, post } from "../api";
import { day, plural } from "../format";
import { Modal } from "../ui";

interface FitSet {
  id: string; maker: string; model: string; submitted: boolean; status: string; verifiedBy: string; verifiedOn: string;
  L: number | null; W: number | null; H: number | null; kg: number | null; pumps: number | null;
}
interface FitRun {
  id: string; at: string; action: "check" | "preview" | "swap"; setId: string; setLabel: string; submitted: boolean; verdict: string;
  confirmed: boolean; room: string; model: string; counts: Record<string, number>; computer: string; hasImage: boolean; ranBy: string | null;
}
interface Chosen { setId: string; setLabel: string; note: string; chosenAt: string; chosenBy: string | null }
interface FitData { sets: FitSet[]; sentAt: string | null; sentBy: string | null; runs: FitRun[]; chosen: Chosen | null; mayChoose: boolean }
interface LinkRow { id: string; computer: string; createdAt: string; lastUsedAt: string | null; locked: number }
interface Result { check: string; result: string; would_be: string; reason: string; rules: string[] }
interface FullRun { results?: Result[]; room?: Record<string, unknown>; set?: Record<string, unknown>; candidates?: string[][]; verdict?: { verdict: string; confirmed: boolean } }

const ACTION: Record<FitRun["action"], string> = { check: "Check Pump", preview: "Next Option (preview)", swap: "Swap" };
const VERDICT_CLASS: Record<string, string> = { pass: "ok", "would pass": "ok", flag: "warn", FAIL: "off", unclear: "" };

const size = (s: FitSet) => (s.L && s.W && s.H ? `${s.L} × ${s.W} × ${s.H} mm` : "not given");
const when = (iso: string) => `${day(iso)}, ${new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;

export function FitCheck({ projectId }: { projectId: string }) {
  const [data, setData] = useState<FitData | null>(null);
  const [links, setLinks] = useState<LinkRow[]>([]);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<FitRun | null>(null);
  // a Preview in Revit message and where it stands (spec/features/revit_link.md §9)
  const [revit, setRevit] = useState<{ label: string; text: string; final: boolean } | null>(null);
  const watching = useRef(0);
  useEffect(() => () => { watching.current++; }, []);
  const askRevit = async (setId: string, label: string) => {
    const turn = ++watching.current;
    setRevit({ label, text: "Sending…", final: false });
    try {
      const sent = await post<{ id: string; text: string }>(`/api/projects/${projectId}/fitcheck/revit`, { setId });
      setRevit({ label, text: sent.text, final: false });
      for (let i = 0; i < 80 && turn === watching.current; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        if (turn !== watching.current) return;
        const st = await api<{ text: string; final: boolean; state: string }>(`/api/projects/${projectId}/fitcheck/revit/${sent.id}`);
        setRevit({ label, text: st.text, final: st.final });
        if (st.final) { if (st.state === "done") setTimeout(load, 4000); return; } // the check Revit sends arrives just after
      }
    } catch (e) {
      if (turn === watching.current) setRevit({ label, text: (e as Error).message, final: true });
    }
  };
  const load = useCallback(() => {
    api<FitData>(`/api/projects/${projectId}/fitcheck`).then(setData, (e: Error) => setError(e.message));
    api<{ links: LinkRow[] }>("/api/revit/links").then((l) => setLinks(l.links), () => undefined);
  }, [projectId]);
  useEffect(() => { load(); }, [load]);

  const choose = async (setId: string) => {
    const note = setId ? window.prompt("A note for the team (optional): why this set?") : "";
    if (note === null) return;
    try {
      await post(`/api/projects/${projectId}/fitcheck/choose`, { setId, note });
      load();
    } catch (e) { setError((e as Error).message); }
  };
  const unlink = async (id: string) => {
    try { await post(`/api/revit/links/${id}/unlink`); load(); } catch (e) { setError((e as Error).message); }
  };

  if (error && !data) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const last = new Map<string, FitRun>();
  for (const r of data.runs) if (!last.has(r.setId)) last.set(r.setId, r); // runs come newest first

  return (
    <>
      {error && <p className="err" role="alert">{error}</p>}
      <section className="sheet" aria-labelledby="fit-chosen">
        <div className="sheet-head"><span className="lab" id="fit-chosen">The set the reviewers chose</span></div>
        {data.chosen ? (
          <p className="sheet-note band">
            <b>{data.chosen.setLabel}</b>, chosen by {data.chosen.chosenBy ?? "a former member"} on {when(data.chosen.chosenAt)}
            {data.chosen.note ? <>: “{data.chosen.note}”</> : "."} Revit shows it in every report.
            {data.mayChoose && <button type="button" className="btn small" onClick={() => void choose("")}>Clear</button>}
          </p>
        ) : (
          <p className="sheet-note band">No set chosen yet. {data.mayChoose ? "Choose one below once the checks are in." : "The reviewers choose it."}</p>
        )}
      </section>

      <section className="sheet" aria-labelledby="fit-sets">
        <div className="sheet-head">
          <span className="lab" id="fit-sets">Pump sets</span>
          <span className="count">
            {data.sentAt ? `${plural(data.sets.length, "set", "sets")}, sent from Revit by ${data.sentBy ?? "a former member"} on ${when(data.sentAt)}` : "none sent yet"}
          </span>
        </div>
        {revit && (
          <p className={`sheet-note band revit-status${revit.final ? " final" : ""}`} role="status">
            <b>Preview in Revit: {revit.label}.</b> {revit.text}
            {revit.final && <button type="button" className="btn small" onClick={() => setRevit(null)}>OK</button>}
          </p>
        )}
        {data.sets.length ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Set</th><th>Size (L × W × H)</th><th>Weight</th><th>Values</th><th>Last check in the model</th>
                {links.length > 0 && <th>In Revit</th>}{data.mayChoose && <th />}</tr></thead>
              <tbody>
                {data.sets.map((s) => {
                  const r = last.get(s.id);
                  return (
                    <tr key={s.id}>
                      <td className="wrap"><b>{s.maker} {s.model}</b>{s.submitted && <span className="tag q">submitted</span>}</td>
                      <td>{size(s)}</td>
                      <td>{s.kg ? `${s.kg} kg` : "not given"}</td>
                      <td>
                        <span className={`chip${s.status === "verified" ? " ok" : ""}`}>{s.status}</span>
                        {s.verifiedBy && <span className="meta"> {s.verifiedBy}, {s.verifiedOn}</span>}
                      </td>
                      <td>{r ? <button type="button" className="linkish" onClick={() => setOpen(r)}><Verdict run={r} /> {day(r.at)}</button> : <span className="meta">not checked yet</span>}</td>
                      {links.length > 0 && (
                        <td><button type="button" className="btn small" disabled={Boolean(revit && !revit.final)}
                          onClick={() => void askRevit(s.id, `${s.maker} ${s.model}`.trim())}>Preview in Revit</button></td>
                      )}
                      {data.mayChoose && (
                        <td>{data.chosen?.setId === s.id ? <span className="chip ok">chosen</span>
                          : <button type="button" className="btn small" onClick={() => void choose(s.id)}>Choose</button>}</td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty">The pump sets come from Revit: RightFit › Online › Send project data, by a consultant or a designer.</p>
        )}
      </section>

      <section className="sheet" aria-labelledby="fit-runs">
        <div className="sheet-head">
          <span className="lab" id="fit-runs">Checks from Revit</span>
          <span className="count">{data.runs.length ? `the latest ${plural(data.runs.length, "check", "checks")}` : "none yet"}</span>
        </div>
        <p className="sheet-note band">
          Each Check Pump, Next Option and Swap in Revit comes here with its room, its results and a picture of the RightFit 3D view.
          The checks run in Revit, with fixed rules and no AI; a result on values nobody has confirmed says what the check would be.
        </p>
        {data.runs.length ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>When</th><th>What</th><th>Set</th><th>Room</th><th>Verdict</th><th>Results</th><th>By</th></tr></thead>
              <tbody>
                {data.runs.map((r) => (
                  <tr key={r.id}>
                    <td><button type="button" className="linkish" onClick={() => setOpen(r)}>{when(r.at)}</button></td>
                    <td>{ACTION[r.action]}</td>
                    <td className="wrap">{r.setLabel}{r.submitted && <span className="tag q">submitted</span>}</td>
                    <td>{r.room || "—"}</td>
                    <td><Verdict run={r} /></td>
                    <td className="wrap">{Object.entries(r.counts).map(([k, n]) => `${n} ${k}`).join(", ")}</td>
                    <td className="wrap">{r.ranBy ?? "a former member"}<span className="meta"> on {r.computer}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty">No check yet. Link Revit (below), then run Check Pump on the pump set.</p>
        )}
      </section>

      <section className="sheet" aria-labelledby="fit-links">
        <div className="sheet-head"><span className="lab" id="fit-links">Your computers linked to Revit</span></div>
        <p className="sheet-note band">
          In Revit: RightFit › Online › Connect this computer. Revit shows a code and opens this site to approve it; it never sees your
          password. Unlink a computer you no longer use. To open a locked project from Revit, approve the link from a browser where the
          project is open with the team password. Once linked, <b>Preview in Revit</b> next to a pump set draws it in your open Revit, from
          this page on any device.
        </p>
        {links.length ? (
          <ul className="fit-links">
            {links.map((l) => (
              <li key={l.id}>
                <b>{l.computer}</b>
                <span className="meta">linked {day(l.createdAt)}{l.lastUsedAt ? `, last used ${when(l.lastUsedAt)}` : ""}{l.locked ? ", opens locked projects" : ""}</span>
                <button type="button" className="btn small danger" onClick={() => void unlink(l.id)}>Unlink</button>
              </li>
            ))}
          </ul>
        ) : <p className="empty">No computer linked yet.</p>}
      </section>

      <Modal open={Boolean(open)} onClose={() => setOpen(null)} title={open ? `${ACTION[open.action]}: ${open.setLabel}` : ""}>
        {open && (
          <>
            {links.length > 0 && open.setId && (
              <p className="sheet-note fit-run-revit">
                <button type="button" className="btn small" disabled={Boolean(revit && !revit.final)}
                  onClick={() => { const r = open; setOpen(null); void askRevit(r.setId, r.setLabel); }}>Show in Revit</button>
                <span className="meta"> Your linked Revit draws this set in the pump's place and sends the check here again.</span>
              </p>
            )}
            <RunDetail projectId={projectId} run={open} />
          </>
        )}
      </Modal>
    </>
  );
}

function Verdict({ run }: { run: FitRun }) {
  return (
    <span className={`chip verdict-chip ${VERDICT_CLASS[run.verdict] ?? ""}`}>
      {run.verdict}{!run.confirmed && run.verdict !== "unclear" ? " (would be)" : ""}
    </span>
  );
}

function RunDetail({ projectId, run }: { projectId: string; run: FitRun }) {
  const [full, setFull] = useState<FullRun | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<FullRun>(`/api/projects/${projectId}/fitcheck/runs/${run.id}`).then(setFull, (e: Error) => setError(e.message));
  }, [projectId, run.id]);
  const room = full?.room ?? {};
  return (
    <div className="fit-run">
      <p className="sheet-note">
        {run.ranBy ?? "A former member"} on {run.computer}, {when(run.at)}{run.model ? `, in ${run.model}` : ""}. Room <b>{run.room || "—"}</b>
        {typeof room.length === "number" ? `: ${Math.round(room.length as number)} × ${Math.round(room.width as number)} mm, ${Math.round(room.height as number)} mm high` : ""}.
      </p>
      {run.hasImage && <img className="fit-picture" src={`/api/projects/${projectId}/fitcheck/runs/${run.id}.png`} alt={`The RightFit 3D view of ${run.setLabel} in its room`} />}
      {error && <p className="err" role="alert">{error}</p>}
      {full?.results && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Check</th><th>Result</th><th>Finding</th><th>Rule</th></tr></thead>
            <tbody>
              {full.results.map((r, i) => (
                <tr key={i}>
                  <td>{r.check}</td>
                  <td>{r.result === r.would_be ? r.result : `${r.result} (would be ${r.would_be})`}</td>
                  <td className="wrap">{r.reason}</td>
                  <td className="wrap">{(r.rules ?? []).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="sheet-note">RightFit does not certify. The checks ran in Revit on the values shown with their status; the people who sign the form decide.</p>
    </div>
  );
}
