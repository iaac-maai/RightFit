// The practice survey (spec/features/survey.md): a public page, no account, anonymous. The questions come from the
// site (worker/survey_rules.ts), so they live in one place. The results page is for people signed in to RightFit.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api, go, post } from "../api";
import { day } from "../format";

type Question =
  | { id: string; kind: "one" | "many"; text: string; options: [string, string][]; optional?: boolean; showIf?: [string, string[]] }
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
  const [sent, setSent] = useState(() => { try { return localStorage.getItem(DONE) === "1"; } catch { return false; } });

  useEffect(() => { api<{ questions: Question[]; consent: string }>("/api/survey").then(setQs, (e: Error) => setError(e.message)); }, []);

  const set = (id: string, v: Value) => setAnswers((a) => ({ ...a, [id]: v }));
  const shown = (q: Question) => !("showIf" in q && q.showIf) || q.showIf[1].includes(String(answers[q.showIf[0]] ?? ""));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const visible = Object.fromEntries(Object.entries(answers).filter(([id]) => qs!.questions.some((q) => q.id === id && shown(q))));
      await post("/api/survey", { answers: visible, consent, website });
      try { localStorage.setItem(DONE, "1"); } catch { /* private browsing: fine */ }
      setSent(true);
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
        {sent ? (
          <>
            <p><b>Thank you.</b> Your answers were sent. They help us measure what checking a form before review could save.</p>
            <p>If someone else in your team reviews or prepares submittals, please send them this page.</p>
          </>
        ) : (
          <>
            <p>
              We are three students at IAAC, Barcelona, building <b>RightFit</b>, a tool that checks material approval forms (submittals)
              for MEP equipment before they are signed, and shows whether the equipment fits in the building model. To know what it could
              save, we need to know how the work goes today. About <b>3 minutes</b>, 12 questions.
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
                    {(q.kind === "one" || q.kind === "many") && (
                      <div className="survey-options">
                        {q.options.map(([key, label]) => {
                          const v = answers[q.id];
                          const on = q.kind === "one" ? v === key : Array.isArray(v) && v.includes(key);
                          return (
                            <label key={key} className={`survey-option${on ? " on" : ""}`}>
                              <input type={q.kind === "one" ? "radio" : "checkbox"} name={q.id} checked={on}
                                onChange={() => {
                                  if (q.kind === "one") set(q.id, key);
                                  else {
                                    const list = Array.isArray(v) ? v : [];
                                    set(q.id, on ? list.filter((x) => x !== key) : [...list, key]);
                                  }
                                }} />
                              {label}
                            </label>
                          );
                        })}
                      </div>
                    )}
                    {q.kind === "scale" && (
                      <div className="survey-scale" role="radiogroup" aria-label={q.text}>
                        <span className="meta">{q.labels[0]}</span>
                        {Array.from({ length: q.max - q.min + 1 }, (_, k) => q.min + k).map((n) => (
                          <label key={n} className={`survey-option${answers[q.id] === n ? " on" : ""}`}>
                            <input type="radio" name={q.id} checked={answers[q.id] === n} onChange={() => set(q.id, n)} />{n}
                          </label>
                        ))}
                        <span className="meta">{q.labels[1]}</span>
                      </div>
                    )}
                    {q.kind === "number" && (
                      <label className="field survey-number">
                        <input type="number" inputMode="numeric" min={q.min} max={q.max} step={1}
                          value={typeof answers[q.id] === "number" ? (answers[q.id] as number) : ""}
                          onChange={(e) => (e.target.value === "" ? setAnswers(({ [q.id]: _, ...rest }) => rest) : set(q.id, Number(e.target.value)))} />
                        <span className="meta">out of 10</span>
                      </label>
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
