// Booster sizing, as on the laptop (app/review/views/booster.js): what the building needs, whether the submitted set
// does it, and what fits from the catalogue. The engine calculates it with the laptop's own code (app/booster.py).
import { useEffect, useState, type FormEvent } from "react";
import { post } from "../api";
import { COLOR, Chart, ceilTo, type Point, type Series } from "../chart";

interface Judged {
  model: string; pumps: number; kw_total: number | null; head_at_need_m: number | null; head_one_pump_out_m: number | null;
  issues: string[]; verdict: string;
}
interface Sizing {
  need: { peak_flow_m3h: number; required_head_m: number; geometric_height_m: number; losses_m: number; residual_m: number; mains_subtracted_m: number };
  submitted: Judged | null; unknown_submitted: boolean; suggest: Judged[]; sets: number; curves: Record<string, [number, number][]>;
  rules: string[];
}
const fmt = (n: number | null | undefined, d = 1) => (n == null ? "n/a" : Number(n).toFixed(d));

export function Booster({ projectId }: { projectId: string }) {
  const [sets, setSets] = useState<string[]>([]);
  const [supply, setSupply] = useState("");
  const [result, setResult] = useState<{ r: Sizing; flats: number } | null>(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    post<{ sets: { model: string }[] }>(`/api/projects/${projectId}/booster`, { sets: true })
      .then((x) => setSets(x.sets.map((s) => s.model)), () => undefined); // without the list, a model is still typed by hand
  }, [projectId]);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const flats = Number(f.get("flats"));
    const floors = Number(f.get("floors"));
    const mains = supply === "mains" ? Number(f.get("mains_m")) : 0;
    if (!Number.isInteger(flats) || !Number.isInteger(floors) || flats < 1 || floors < 1) { setProblem("Give the flats and the floors as whole numbers."); return; }
    if (!supply) { setProblem("Choose how the building is supplied."); return; }
    if (supply === "mains" && !(mains > 0)) { setProblem("Give the mains pressure in metres."); return; }
    setBusy(true);
    setProblem("");
    try {
      setResult({ r: await post<Sizing>(`/api/projects/${projectId}/booster`, { flats, floors, submitted: String(f.get("submitted") ?? "").trim(), mains_m: mains }), flats });
    } catch (err) {
      setProblem((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="sheet-note">What does this building need, will the submitted set do it, and what fits? Calculated by RightFit's checks, the same as on the laptop.</p>
      <div className="booster-grid">
        <form className="sheet booster-form" onSubmit={(e) => void submit(e)} noValidate>
          <label><span className="lab">Flats</span><input type="text" name="flats" inputMode="numeric" autoComplete="off" placeholder="e.g. 40" /></label>
          <label><span className="lab">Floors</span><input type="text" name="floors" inputMode="numeric" autoComplete="off" placeholder="e.g. 10" /></label>
          <label><span className="lab">Supply</span>
            <select value={supply} onChange={(e) => setSupply(e.target.value)}>
              <option value="" disabled>Choose</option><option value="mains">Mains, pressure known</option><option value="tank">Break tank (CTE default)</option>
            </select>
          </label>
          {supply === "mains" && <label><span className="lab">Mains pressure, m</span><input type="text" name="mains_m" inputMode="decimal" autoComplete="off" placeholder="e.g. 25" /></label>}
          <label><span className="lab">Submitted set</span><input type="text" name="submitted" list="booster-sets" autoComplete="off" placeholder="model, e.g. GHV20/…" /></label>
          <datalist id="booster-sets">{sets.map((m) => <option key={m} value={m} />)}</datalist>
          <button className="btn p" type="submit" disabled={busy}>{busy ? "Calculating…" : "Check and suggest"}</button>
          {problem && <p className="err" role="alert">{problem}</p>}
        </form>
        {result && <Result r={result.r} flats={result.flats} />}
      </div>
    </>
  );
}

function Result({ r, flats }: { r: Sizing; flats: number }) {
  const n = r.need;
  const s = r.submitted;
  const sug = r.suggest[0];
  const shown = Object.values(r.curves).flat();
  const lead = r.curves[s ? s.model : sug?.model ?? ""] ?? shown; // the chart is framed on the submitted set's own range
  const xMax = Math.max(10, ceilTo(Math.max(...lead.map(([q]) => q), n.peak_flow_m3h * 2), 5));
  const yMax = ceilTo(Math.max(...shown.map(([, h]) => h), n.required_head_m), 25);
  const series: Series[] = [];
  if (s && r.curves[s.model]) {
    const c = r.curves[s.model];
    series.push({ pts: c, color: COLOR.red, label: `${s.model} (submitted)`, at: [c[0][0] + xMax * 0.02, c[0][1] + yMax * 0.01] });
  }
  if (sug && r.curves[sug.model]) {
    const c = r.curves[sug.model].filter(([q]) => q <= xMax);
    series.push({ pts: c, color: COLOR.green, label: `${sug.model} (suggested)`, at: [xMax * 0.99, c[c.length - 1][1] - yMax * 0.09], anchor: "end" });
  }
  const points: Point[] = [{ x: n.peak_flow_m3h, y: n.required_head_m, color: COLOR.ink, label: `need ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m`,
    dx: -14, dy: 34, anchor: "middle", tip: `Need: ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m` }];
  const guides = [];
  if (s && s.head_at_need_m != null) {
    points.unshift({ x: n.peak_flow_m3h, y: s.head_at_need_m, color: COLOR.red, r: 6, tip: `${s.model}: ${fmt(s.head_at_need_m)} m` });
    guides.push({ x1: n.peak_flow_m3h, y1: n.required_head_m, x2: n.peak_flow_m3h, y2: s.head_at_need_m, color: COLOR.red });
  }
  const at = s ? `${fmt(s.head_at_need_m, 0)} m available at ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m needed` : "";
  return (
    <div className="booster-result">
      <section className="sheet">
        <div className="sheet-head"><span className="lab">What the building needs</span></div>
        <div className="figures">
          <div className="fld"><span className="lab">Peak flow</span><span className="typed big">{fmt(n.peak_flow_m3h)}</span> m³/h</div>
          <div className="fld"><span className="lab">Head</span><span className="typed big">{fmt(n.required_head_m)}</span> m</div>
        </div>
        <p className="fine pad-x">
          {flats} flats, mixer taps: {fmt(n.geometric_height_m)} m height + {fmt(n.losses_m)} m losses + {fmt(n.residual_m, 0)} m at the tap
          {n.mains_subtracted_m ? ` − ${fmt(n.mains_subtracted_m)} m from the mains` : ""}. {r.rules.join(", ")}, DIN 1988-300.
        </p>
      </section>
      {s && (
        <p className={`band-note verdict ${s.verdict === "fits" ? "ok" : "no"}`} role="status">
          <b>{s.verdict === "fits" ? `${s.model} fits` : `${s.model}: ${(s.issues[0] ?? "").split(":")[0]}`}</b>
          <span>{s.verdict === "fits" || s.head_at_need_m != null ? at : s.issues[0]}{s.verdict !== "fits" && s.issues.length > 1 ? `; ${s.issues.slice(1).join("; ")}` : ""}</span>
        </p>
      )}
      {r.unknown_submitted && <p className="err" role="alert">That set is not one of the {r.sets} Lowara sets. Check the model name.</p>}
      {series.length > 0 && (
        <figure className="sheet chart-box">
          <Chart xMax={xMax} yMax={yMax} xStep={5} yStep={25} xLabel="Flow Q (m³/h)" yLabel="Head H (m)" series={series} points={points} guides={guides}
            label="Pump curves of the submitted and suggested sets against the need" />
        </figure>
      )}
      <section className="sheet">
        <div className="sheet-head"><span className="lab">What fits, from {r.sets} Lowara booster sets, lowest power first</span></div>
        {r.suggest.length ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Set</th><th>Power</th><th>Head at {fmt(n.peak_flow_m3h)} m³/h</th><th>With one pump out</th><th>Verdict</th></tr></thead>
              <tbody>
                {r.suggest.map((x) => (
                  <tr key={x.model}>
                    <td><b>{x.model}</b>, {x.pumps} pumps</td><td className="typed">{fmt(x.kw_total)} kW</td>
                    <td className="typed">{fmt(x.head_at_need_m)} m</td><td className="typed">{fmt(x.head_one_pump_out_m)} m</td>
                    <td><span className="chip ok">Fits, standby OK</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="empty">Nothing in the catalogue fits this building.</p>}
        <p className="fine pad-x">Curves from the Lowara GHV catalogue. An engineer confirms the choice.</p>
      </section>
    </div>
  );
}
