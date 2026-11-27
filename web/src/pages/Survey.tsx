// The practice survey (spec/features/survey.md): a public page, no account, anonymous. The questions come from the
// site (worker/survey_rules.ts), so they live in one place. The results page is for people signed in to RightFit.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api, go, post } from "../api";
import { day } from "../format";

type Question =
  | { id: string; kind: "one" | "many"; text: string; options: [string, string][]; optional?: boolean; showIf?: [string, string[]]; max?: number }
  | { id: string; kind: "number"; text: string; min: number; max: number; optional?: boolean }
  | { id: string; kind: "scale"; text: string; min: number; max: number; labels: [string, string] }
  | { id: string; kind: "text"; text: string; optional: true; hint: string };
type Value = string | string[] | number;

const DONE = "rightfit-survey-sent"; // this browser answered already

function Bar({ signedIn }: { signedIn?: boolean }) {
  return (
    <header className="legal-bar">
      <a className="brand" href="/" onClick={go("/")}>RightFit<span className="brand-tag">online</span></a>
      <nav aria-label="RightFit">
        <a href="/privacy" onClick={go("/privacy")}>Privacy</a>
        <a href="/" onClick={go("/")}>{signedIn ? "Your projects" : "Sign in"}</a>
      </nav>
    </header>
  );
}

export function Survey() {
  const [qs, setQs] = useState<{ questions: Question[]; consent: string } | null>(null);
  const [answers, setAnswers] = useState<Record<string, Value>>({});
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState(""); // the hidden field: people never see it, robots fill it in
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const [sent, setSent] = useState(() => { try { return localStorage.getItem(DONE) === "1"; } catch { return false; } });

  useEffect(() => { api<{ questions: Question[]; consent: string }>("/api/survey").then(setQs, (e: Error) => setError(e.message)); }, []);

  const set = (id: string, v: Value) => setAnswers((a) => ({ ...a, [id]: v }));
  const unset = (id: string) => setAnswers(({ [id]: _, ...rest }) => rest);
  const shown = (q: Question) => !("showIf" in q && q.showIf) || q.showIf[1].includes(String(answers[q.showIf[0]] ?? ""));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const visible = Object.fromEntries(Object.entries(answers).filter(([id]) => qs!.questions.some((q) => q.id === id && shown(q))));
      await post("/api/survey", { answers: visible, consent, website });
      try { localStorage.setItem(DONE, "1"); } catch { /* private browsing: fine */ }
      setSent(true);
      setTick((t) => t + 1); // the live numbers include this answer at once
      window.scrollTo(0, 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally { setBusy(false); }
  };

  return (
    <div className="legal">
      <Bar />
      <article className="sheet legal-text survey">
        <h1>How material approval forms go today</h1>
        <LivePanel refresh={tick} />
        {sent ? (
          <>
            <p><b>Thank you.</b> Your answers were sent. They help us measure what checking a form before review could save.</p>
            <p>If someone else in your team reviews or prepares submittals, please send them this page.</p>
          </>
        ) : (
          <>
            <p>
              We are three students at IAAC, Barcelona. We want to understand how material approval forms (submittals) for MEP
              equipment go today: how long they take, how often they come back and why. About <b>3 minutes</b>
              {qs ? <>, up to {qs.questions.length} questions</> : null}.
            </p>
            <p className="meta">
              Anonymous: no name, email, company or IP address is collected; only the day you answered and your answers are kept.
              Answers are estimates, and are shown as such.
            </p>
            {error && !qs && <p className="err" role="alert">{error}</p>}
            {qs && (
              <form className="survey-form" onSubmit={submit}>
                {qs.questions.filter(shown).map((q, i) => (
                  <fieldset key={q.id} className="survey-q">
                    <legend><span className="survey-n">{i + 1}</span> {q.text}{"optional" in q && q.optional ? <span className="meta"> (optional)</span> : null}</legend>
                    {q.kind === "one" && (
                      <select className="survey-select" value={(answers[q.id] as string) ?? ""} aria-label={q.text}
                        onChange={(e) => (e.target.value === "" ? unset(q.id) : set(q.id, e.target.value))}>
                        <option value="">Choose…</option>
                        {q.options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                      </select>
                    )}
                    {q.kind === "many" && (() => {
                      const v = Array.isArray(answers[q.id]) ? (answers[q.id] as string[]) : [];
                      const names = q.options.filter(([key]) => v.includes(key)).map(([, label]) => label);
                      return (
                        <details className="survey-pick">
                          <summary className="survey-select">{names.length ? names.join("; ") : `Choose${q.max ? ` up to ${q.max}` : ""}…`}</summary>
                          <div className="survey-pick-list">
                            {q.options.map(([key, label]) => {
                              const on = v.includes(key);
                              return (
                                <label key={key} className={on ? "on" : undefined}>
                                  <input type="checkbox" checked={on} disabled={!on && q.max !== undefined && v.length >= q.max}
                                    onChange={() => set(q.id, on ? v.filter((x) => x !== key) : [...v, key])} />
                                  {label}
                                </label>
                              );
                            })}
                          </div>
                        </details>
                      );
                    })()}
                    {q.kind === "scale" && (
                      <select className="survey-select" value={typeof answers[q.id] === "number" ? String(answers[q.id]) : ""} aria-label={q.text}
                        onChange={(e) => (e.target.value === "" ? unset(q.id) : set(q.id, Number(e.target.value)))}>
                        <option value="">Choose…</option>
                        {Array.from({ length: q.max - q.min + 1 }, (_, k) => q.min + k).map((n) => (
                          <option key={n} value={n}>{n}{n === q.min ? ` (${q.labels[0].toLowerCase()})` : n === q.max ? ` (${q.labels[1].toLowerCase()})` : ""}</option>
                        ))}
                      </select>
                    )}
                    {q.kind === "number" && (
                      <select className="survey-select" value={typeof answers[q.id] === "number" ? String(answers[q.id]) : ""} aria-label={q.text}
                        onChange={(e) => (e.target.value === "" ? unset(q.id) : set(q.id, Number(e.target.value)))}>
                        <option value="">Choose…</option>
                        {Array.from({ length: q.max - q.min + 1 }, (_, k) => q.min + k).map((n) => <option key={n} value={n}>{n} out of 10</option>)}
                      </select>
                    )}
                    {q.kind === "text" && (
                      <label className="field">
                        <textarea rows={4} maxLength={500} value={(answers[q.id] as string) ?? ""} onChange={(e) => set(q.id, e.target.value)} />
                        <span className="meta">{q.hint}</span>
                      </label>
                    )}
                  </fieldset>
                ))}
                <label className="survey-hidden" aria-hidden="true">
                  Website <input tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
                </label>
                <label className="survey-consent">
                  <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> {qs.consent}
                </label>
                {error && <p className="err" role="alert">{error}</p>}
                <button className="btn p" disabled={busy || !consent}>{busy ? "Sending…" : "Send my answers"}</button>
              </form>
            )}
          </>
        )}
      </article>
    </div>
  );
}

interface Result {
  id: string; text: string; kind: string; answered: number;
  counts?: { key: string; label: string; n: number }[];
  spread?: { median: number | null; low: number | null; high: number | null };
}
interface Results { n: number; firstDay: string | null; lastDay: string | null; results: Result[]; comments: { day: string; text: string }[] | null; admin: boolean }

export function SurveyResults() {
  const [data, setData] = useState<Results | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Results>("/api/survey/results").then(setData, (e: Error) => setError(e.message)); }, []);
  const link = `${window.location.origin}/survey`;

  if (error) return <div className="screen"><p className="err" role="alert">{error}</p></div>;
  if (!data) return <div className="screen"><span className="spinner" aria-label="Loading" /></div>;
  return (
    <div className="screen">
      <header className="screen-head">
        <h1>Survey: how material approval forms go today</h1>
        <p>
          {data.n ? <>As reported by <b>{data.n} {data.n === 1 ? "person" : "people"}</b>, from {day(data.firstDay!)} to {day(data.lastDay!)}. </> : "No answer yet. "}
          These are people's own estimates, not measurements. The link to share: <a href={link}>{link}</a>
          {data.admin && <> · <a href="/api/survey/results.csv">Download every answer (CSV)</a></>}
        </p>
      </header>
      <section className="sheet"><LivePanel /></section>
      {data.results.map((r) => {
        const max = Math.max(1, ...(r.counts ?? []).map((c) => c.n));
        return (
          <section key={r.id} className="sheet survey-result">
            <div className="sheet-head"><span className="lab">{r.text}</span><span className="count">{r.answered} answered</span></div>
            <div className="survey-bars">
              {(r.counts ?? []).map((c) => (
                <div key={c.key} className="survey-bar">
                  <span className="survey-bar-label">{c.label}</span>
                  <span className="survey-bar-track"><span style={{ width: `${(c.n / max) * 100}%` }} /></span>
                  <span className="survey-bar-n">{c.n}{r.answered ? ` · ${Math.round((c.n / r.answered) * 100)}%` : ""}</span>
                </div>
              ))}
            </div>
            {r.spread && r.spread.median !== null && (
              <p className="sheet-note">Median {r.spread.median}; the middle half answered {r.spread.low} to {r.spread.high}.</p>
            )}
          </section>
        );
      })}
      {data.comments && (
        <section className="sheet">
          <div className="sheet-head"><span className="lab">Comments</span><span className="count">{data.comments.length}, seen only by the people who run RightFit</span></div>
          {data.comments.length ? <ul className="survey-comments">{data.comments.map((c, i) => <li key={i}><span className="meta">{day(c.day)}</span> {c.text}</li>)}</ul>
            : <p className="empty">No comment yet.</p>}
        </section>
      )}
    </div>
  );
}

// ---- The live numbers (spec/features/survey.md §4): what everyone answered so far, asked again every few seconds ----
// Drawn like a sheet of drawings: a fine grid, line icons, and each range as a dimension line from the lowest answer to
// the highest, with the average marked on it.
interface LiveRange {
  id: string; title: string; unit: string; answered: number; mean: number | null; atLeast: boolean; lowest: string | null; highest: string | null;
  scale: string[]; lowIndex: number | null; highIndex: number | null; meanAt: number | null;
}
interface Live {
  n: number; lastDay: string | null; ranges: LiveRange[];
  returned: { answered: number; mean: number | null; min: number | null; max: number | null };
  misfit: { answered: number; atLeastOnce: number };
  useful: { id: string; title: string; answered: number; mean: number | null }[];
  reasons: { label: string; n: number }[]; roles: { label: string; n: number }[];
}

const EVERY = 5000; // milliseconds between two looks at the numbers, while the page is on screen

// Line icons, 24 x 24, drawn with the text colour
const ICONS: Record<string, string> = {
  review_time: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7v5l3.5 2",
  prepare_time: "M7 3h7l4 4v14H7z M14 3v4h4 M9.5 12h5 M9.5 15.5h5",
  rounds: "M19.5 12a7.5 7.5 0 1 1-2.2-5.3 M19.5 4.5v3.7h-3.7 M12 9v3.2l2 1.3",
  delay: "M3.5 5.5h17v15h-17z M3.5 10h17 M8 3v4.5 M16 3v4.5 M7.5 14h3 M7.5 17h6",
  misfit_cost: "M16.5 6.8a6.5 6.5 0 1 0 0 10.4 M5 10.3h8.5 M5 13.7h8.5",
  returned: "M4 4h16v16H4z M15 9.6a3.4 3.4 0 1 0 0 4.8",
  misfit: "M4 20V5 M20 20V5 M2.5 20h19 M11 11h11v9 M11 11v9",
  useful_check: "M10 6.5h10 M10 12h10 M10 17.5h10 M3.5 6.5l1.5 1.5 2.5-3 M3.5 12l1.5 1.5 2.5-3 M3.5 17.5l1.5 1.5 2.5-3",
  useful_fit: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M12 12l8-4.5 M12 12v9 M12 12L4 7.5",
  reasons: "M9 14L4 9l5-5 M4 9h10.5a5.5 5.5 0 0 1 0 11H11",
  roles: "M9 11a3.2 3.2 0 1 0 0-6.4a3.2 3.2 0 1 0 0 6.4 M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6 M16.5 11.5a2.6 2.6 0 1 0 0-5.2 M17.5 14.3c2 .5 3.5 2.4 3.5 4.7",
};
function Icon({ name }: { name: string }) {
  return (
    <svg className="live-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={ICONS[name]} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function amount(unit: string, x: number) {
  if (unit === "minutes") {
    const m = Math.round(x / 5) * 5;
    if (m < 60) return [`${Math.max(5, m)}`, "min"];
    const h = Math.floor(m / 60), r = m % 60;
    return [r ? `${h}h${String(r).padStart(2, "0")}` : `${h}`, r ? "" : "h"];
  }
  if (unit === "days") return [`${x < 10 ? Math.round(x * 2) / 2 : Math.round(x)}`, "days"];
  if (unit === "euros") return [`€${(Math.round(x / 100) * 100).toLocaleString("en-GB")}`, ""];
  return [`${Math.round(x * 10) / 10}`, unit];
}

// A dimension line, as on a drawing: ticks for each answer, the span from the lowest to the highest answer with
// slash ends, and a marker where the average falls
function Dimension({ steps, low, high, at, ends }: { steps: number; low: number | null; high: number | null; at: number | null; ends?: [string, string] }) {
  const x = (i: number) => 8 + (i * 224) / Math.max(1, steps - 1);
  return (
    <div className="live-dim">
      <svg viewBox="0 0 240 34" preserveAspectRatio="none" aria-hidden="true">
        <line x1="8" y1="22" x2="232" y2="22" className="dim-base" />
        {Array.from({ length: steps }, (_, i) => <line key={i} x1={x(i)} y1="19" x2={x(i)} y2="25" className="dim-tick" />)}
        {low !== null && high !== null && (
          <>
            <line x1={x(low)} y1="22" x2={x(high)} y2="22" className="dim-span" />
            {[low, high].map((i, k) => <line key={k} x1={x(i) - 4} y1="26" x2={x(i) + 4} y2="18" className="dim-span" />)}
          </>
        )}
        {at !== null && <path d={`M${x(at)} 15 l-5 -8 h10 z`} className="dim-mean" />}
      </svg>
      {ends && <div className="live-dim-ends"><span>{ends[0]}</span><span>{ends[1]}</span></div>}
    </div>
  );
}

const answers = (n: number) => `${n} ${n === 1 ? "answer" : "answers"}`;

export function LivePanel({ refresh = 0 }: { refresh?: number }) {
  const [data, setData] = useState<Live | null>(null);
  useEffect(() => {
    let stop = false;
    const look = () => { if (!document.hidden) api<Live>("/api/survey/live").then((d) => { if (!stop) setData(d); }, () => {}); };
    look();
    const timer = window.setInterval(look, EVERY);
    document.addEventListener("visibilitychange", look);
    return () => { stop = true; window.clearInterval(timer); document.removeEventListener("visibilitychange", look); };
  }, [refresh]);

  if (!data) return null;
  const share = data.misfit.answered ? data.misfit.atLeastOnce / data.misfit.answered : 0;
  const maxReason = Math.max(1, ...data.reasons.map((r) => r.n));
  return (
    <section className="live" aria-live="polite" aria-label="Live results">
      <header className="live-head">
        <div>
          <span className="live-eyebrow"><span className="live-dot" aria-hidden="true" />Live · updates by itself</span>
          <h2>What people report so far</h2>
        </div>
        <div className="live-count">
          <b>{data.n}</b>
          <span>{data.n === 1 ? "answer" : "answers"}{data.lastDay ? <><br />last on {day(data.lastDay)}</> : null}</span>
        </div>
      </header>

      {data.n === 0 ? <p className="live-empty">No answer yet. Yours will be the first.</p> : (
        <>
          <div className="live-grid">
            {data.ranges.map((r) => {
              const [num, unit] = r.mean === null ? ["–", ""] : amount(r.unit, r.mean);
              return (
                <article key={r.id} className="live-card">
                  <div className="live-card-head"><Icon name={r.id} /><h3>{r.title}</h3></div>
                  <p className="live-value">{r.mean !== null && <small>{r.atLeast ? "at least" : "about"}</small>}{num}<em>{unit}</em></p>
                  {r.answered ? <Dimension steps={r.scale.length} low={r.lowIndex} high={r.highIndex} at={r.meanAt} ends={[r.lowest!, r.highest!]} />
                    : <p className="live-note">No answer yet</p>}
                  <p className="live-note">{r.answered ? answers(r.answered) : ""}</p>
                </article>
              );
            })}
            <article className="live-card">
              <div className="live-card-head"><Icon name="returned" /><h3>Get C (revise and resubmit) at the first submission</h3></div>
              <p className="live-value">{data.returned.mean !== null && <small>about</small>}{data.returned.mean === null ? "–" : Math.round(data.returned.mean * 10) / 10}<em>/ 10</em></p>
              {data.returned.answered ? <Dimension steps={11} low={data.returned.min} high={data.returned.max} at={data.returned.mean} ends={[`${data.returned.min} of 10`, `${data.returned.max} of 10`]} />
                : <p className="live-note">No answer yet</p>}
              <p className="live-note">{data.returned.answered ? answers(data.returned.answered) : ""}</p>
            </article>
            <article className="live-card">
              <div className="live-card-head"><Icon name="misfit" /><h3>Saw approved equipment not fit on site, in their last 3 projects</h3></div>
              <div className="live-ring-row">
                <svg className="live-ring" viewBox="0 0 44 44" aria-hidden="true">
                  <circle cx="22" cy="22" r="18" className="ring-base" />
                  <circle cx="22" cy="22" r="18" className="ring-fill" strokeDasharray={`${share * 113.1} 113.1`} transform="rotate(-90 22 22)" />
                </svg>
                <p className="live-value">{data.misfit.answered ? Math.round(share * 100) : "–"}<em>%</em></p>
              </div>
              <p className="live-note">{data.misfit.answered ? `${data.misfit.atLeastOnce} of ${data.misfit.answered}, at least once` : "No answer yet"}</p>
            </article>
            {data.useful.map((u) => (
              <article key={u.id} className="live-card">
                <div className="live-card-head"><Icon name={u.id} /><h3>How useful: {u.title.toLowerCase()}</h3></div>
                <p className="live-value">{u.mean === null ? "–" : Math.round(u.mean * 10) / 10}<em>/ 5</em></p>
                <div className="live-blocks" aria-hidden="true">
                  {[1, 2, 3, 4, 5].map((k) => <span key={k} style={{ ["--fill" as string]: `${Math.max(0, Math.min(1, (u.mean ?? 0) - (k - 1))) * 100}%` }} />)}
                </div>
                <p className="live-note">{u.answered ? answers(u.answered) : "No answer yet"}</p>
              </article>
            ))}
          </div>

          <div className="live-lower">
            <article className="live-card">
              <div className="live-card-head"><Icon name="reasons" /><h3>Why forms come back most</h3></div>
              <ol className="live-reasons">
                {data.reasons.map((r) => (
                  <li key={r.label}><span>{r.label}</span><span className="live-reason-bar"><i style={{ width: `${(r.n / maxReason) * 100}%` }} /></span><b>{r.n}</b></li>
                ))}
              </ol>
            </article>
            <article className="live-card">
              <div className="live-card-head"><Icon name="roles" /><h3>Who answered</h3></div>
              <ul className="live-chips">{data.roles.map((r) => <li key={r.label}>{r.label}<b>{r.n}</b></li>)}</ul>
            </article>
          </div>

          <p className="live-foot">
            People's own estimates, not measurements. Each answer is a range; an average counts each range at its middle, and an
            open range such as “Over 4 hours” at its lower bound, which makes that average “at least”. “Don't know” is left out.
            The line under each number runs from the lowest answer to the highest; ▼ marks the average.
          </p>
        </>
      )}
    </section>
  );
}
