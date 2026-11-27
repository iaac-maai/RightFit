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
interface LiveRange { id: string; title: string; unit: string; answered: number; mean: number | null; atLeast: boolean; lowest: string | null; highest: string | null }
interface Live {
  n: number; lastDay: string | null; ranges: LiveRange[];
  returned: { answered: number; mean: number | null; min: number | null; max: number | null };
  misfit: { answered: number; atLeastOnce: number };
  useful: { id: string; title: string; answered: number; mean: number | null }[];
  reasons: { label: string; n: number }[]; roles: { label: string; n: number }[];
}

const EVERY = 5000; // milliseconds between two looks at the numbers, while the page is on screen

function amount(unit: string, x: number) {
  if (unit === "minutes") {
    const m = Math.round(x / 5) * 5;
    if (m < 60) return `${Math.max(5, m)} min`;
    const h = Math.floor(m / 60), r = m % 60;
    return r ? `${h} h ${String(r).padStart(2, "0")}` : `${h} h`;
  }
  if (unit === "days") return `${x < 10 ? Math.round(x * 2) / 2 : Math.round(x)} days`;
  if (unit === "euros") return `€${(Math.round(x / 100) * 100).toLocaleString("en-GB")}`;
  return `${Math.round(x * 10) / 10}`;
}

function Tile({ value, title, note }: { value: string; title: string; note: string }) {
  return (
    <div className="live-tile">
      <span className="live-value">{value}</span>
      <span className="live-title">{title}</span>
      <span className="live-note">{note}</span>
    </div>
  );
}

const people = (n: number) => `${n} ${n === 1 ? "answer" : "answers"}`;

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
  return (
    <section className="live" aria-live="polite">
      <div className="live-head">
        <span className="live-dot" aria-hidden="true" />
        <b>Live results</b>
        <span className="meta">{data.n ? <>what {data.n} {data.n === 1 ? "person" : "people"} reported so far, last on {day(data.lastDay!)}; updates by itself</> : "no answer yet: yours will be the first"}</span>
      </div>
      {data.n > 0 && (
        <>
          <div className="live-grid">
            {data.ranges.map((r) => (
              <Tile key={r.id} title={r.title}
                value={r.mean === null ? "–" : `${r.atLeast ? "at least " : "about "}${amount(r.unit, r.mean)}`}
                note={r.answered ? `${people(r.answered)} · from “${r.lowest}” to “${r.highest}”` : "no answer yet"} />
            ))}
            <Tile title="Get C (revise and resubmit) at the first submission"
              value={data.returned.mean === null ? "–" : `about ${Math.round(data.returned.mean * 10) / 10} out of 10`}
              note={data.returned.answered ? `${people(data.returned.answered)} · from ${data.returned.min} to ${data.returned.max} out of 10` : "no answer yet"} />
            <Tile title="Saw approved equipment not fit on site, in their last 3 projects"
              value={data.misfit.answered ? `${data.misfit.atLeastOnce} of ${data.misfit.answered}` : "–"}
              note={data.misfit.answered ? `${Math.round((data.misfit.atLeastOnce / data.misfit.answered) * 100)}% at least once` : "no answer yet"} />
            {data.useful.map((u) => (
              <Tile key={u.id} title={`How useful: ${u.title.toLowerCase()}`}
                value={u.mean === null ? "–" : `${Math.round(u.mean * 10) / 10} / 5`} note={u.answered ? people(u.answered) : "no answer yet"} />
            ))}
          </div>
          {data.reasons.length > 0 && (
            <p className="live-line"><b>Most common reasons a form comes back:</b> {data.reasons.map((r) => `${r.label} (${r.n})`).join(" · ")}</p>
          )}
          <p className="live-line"><b>Who answered:</b> {data.roles.map((r) => `${r.label} (${r.n})`).join(" · ")}</p>
          <p className="live-foot meta">
            People's own estimates, not measurements. Each answer is a range; an average counts each range at its middle, and an
            open range such as “Over 4 hours” at its lower bound, which makes that average “at least”. “Don't know” is left out.
          </p>
        </>
      )}
    </section>
  );
}
