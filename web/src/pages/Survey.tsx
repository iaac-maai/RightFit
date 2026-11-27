// The practice survey (spec/features/survey.md): a public page with the questions only, no account, anonymous. The
// questions come from the site (worker/survey_rules.ts), so they live in one place. The live results are the Survey page
// of RightFit online, for people signed in.
import { useEffect, useRef, useState, type FormEvent } from "react";
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
                    {(q.kind === "one" || q.kind === "many") && (
                      <div className="survey-options">
                        {q.options.map(([key, label]) => {
                          const v = answers[q.id];
                          const on = q.kind === "one" ? v === key : Array.isArray(v) && v.includes(key);
                          return (
                            <label key={key} className={`survey-option${on ? " on" : ""}`}>
                              <input type={q.kind === "one" ? "radio" : "checkbox"} name={q.id} checked={on}
                                disabled={q.kind === "many" && !on && q.max !== undefined && Array.isArray(v) && v.length >= q.max}
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

// One question's answers as bars: each answer, how many chose it, and its share of those who answered
function QuestionBars({ r }: { r: Result }) {
  const max = Math.max(1, ...(r.counts ?? []).map((c) => c.n));
  return (
    <div className="survey-bars">
      {(r.counts ?? []).map((c) => (
        <div key={c.key} className="survey-bar">
          <span className="survey-bar-label">{c.label}</span>
          <span className="survey-bar-track"><span style={{ width: `${(c.n / max) * 100}%` }} /></span>
          <span className="survey-bar-n">{c.n}{r.answered ? ` · ${Math.round((c.n / r.answered) * 100)}%` : ""}</span>
        </div>
      ))}
    </div>
  );
}

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
      <LivePanel />
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
// Two headline numbers first, time lost and money lost, then the rest smaller, with line icons.
interface LiveRange {
  id: string; title: string; unit: string; answered: number; mean: number | null; atLeast: boolean; lowest: string | null; highest: string | null;
  scale: string[]; lowIndex: number | null; highIndex: number | null; meanAt: number | null;
}
interface Lost { answered: number; mean: number | null; atLeast: boolean; low: number | null; high: number | null }
interface Live {
  n: number; lastDay: string | null; ranges: LiveRange[];
  timeLost: Lost; moneyLost: Lost & { lowest: string | null; highest: string | null };
  returned: { answered: number; mean: number | null; min: number | null; max: number | null };
  misfit: { answered: number; atLeastOnce: number };
  useful: { id: string; title: string; answered: number; mean: number | null }[];
  reasons: { label: string; n: number }[]; roles: { label: string; n: number }[];
  results: Result[];
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
  time_lost: "M7 3h10 M7 21h10 M8 3c0 5 8 5 8 9s-8 4-8 9 M16 3c0 5-8 5-8 9s8 4 8 9 M10 18.5h4",
  money_lost: "M16.5 6.8a6.5 6.5 0 1 0 0 10.4 M5 10.3h8.5 M5 13.7h8.5 M19 15l2.5 2.5 M21.5 15L19 17.5",
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


// A number that counts up to its value the first time, and glides to the new value when an answer comes in.
// People who ask their system for less motion see the value at once.
function useGlide(target: number | null, ms = 1200) {
  const [shown, setShown] = useState(0);
  const now = useRef(0);
  useEffect(() => {
    if (target === null) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { now.current = target; setShown(target); return; }
    const from = now.current, start = performance.now();
    let frame = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / ms);
      now.current = from + (target - from) * (1 - Math.pow(1 - k, 3)); // fast first, gentle at the end
      setShown(now.current);
      if (k < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return shown;
}

export function LivePanel() {
  const [data, setData] = useState<Live | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let stop = false;
    const look = () => { if (!document.hidden) api<Live>("/api/survey/live").then((d) => { if (!stop) setData(d); }, () => {}); };
    look();
    const timer = window.setInterval(look, EVERY);
    document.addEventListener("visibilitychange", look);
    return () => { stop = true; window.clearInterval(timer); document.removeEventListener("visibilitychange", look); };
  }, []);
  const timeShown = useGlide(data?.timeLost.mean ?? null);
  const moneyShown = useGlide(data?.moneyLost.mean ?? null, 1500);

  if (!data) return null;
  const share = data.misfit.answered ? data.misfit.atLeastOnce / data.misfit.answered : 0;
  const r = (id: string) => data.ranges.find((x) => x.id === id)!;
  const small = (id: string, label: string) => {
    const x = r(id);
    const [num, unit] = x.mean === null ? ["–", ""] : amount(x.unit, x.mean);
    return { id, label, value: <>{x.mean !== null && x.atLeast ? "≥ " : x.mean !== null ? "≈ " : ""}{num}{unit && <em> {unit}</em>}</>, n: x.answered, at: `${num}${unit}` };
  };
  const smalls = [
    small("review_time", "own time to review one submittal"),
    small("prepare_time", "own time to prepare one"),
    small("rounds", "rounds until approved"),
    small("delay", "delay each time it comes back"),
    { id: "returned", label: "out of 10 get C at the first submission", n: data.returned.answered, at: String(data.returned.mean),
      value: <>{data.returned.mean === null ? "–" : <>≈ {Math.round(data.returned.mean * 10) / 10}<em> / 10</em></>}</> },
    { id: "misfit", label: "saw approved equipment not fit on site", n: data.misfit.answered, at: String(share),
      value: <>{data.misfit.answered ? <>{Math.round(share * 100)}<em> %</em></> : "–"}</> },
    ...data.useful.map((u) => ({ id: u.id, label: u.id === "useful_check" ? "find a check before review useful" : "find seeing the fit in the model useful", n: u.answered, at: String(u.mean),
      value: <>{u.mean === null ? "–" : <>{Math.round(u.mean * 10) / 10}<em> / 5</em></>}</> })),
  ];
  const t = data.timeLost, m = data.moneyLost;
  const days = (x: number) => `${x < 10 ? Math.round(x * 2) / 2 : Math.round(x)}`;
  const euros = (x: number) => `€${(Math.round(x / 100) * 100).toLocaleString("en-GB")}`;
  return (
    <section className="live" aria-live="polite" aria-label="Live results">
      <header className="live-head">
        <span className="live-eyebrow"><span className="live-dot" aria-hidden="true" />Live results</span>
        <span className="live-sub">{data.n ? <>from <b key={data.n} className="live-pop">{data.n}</b> {data.n === 1 ? "person" : "people"} so far · updates by itself</> : "no answer yet: yours will be the first"}</span>
      </header>

      <div className="live-heroes">
        <article className="live-hero" style={{ ["--i" as string]: 0 }}>
          <span key={String(t.mean)} className="live-hero-icon live-flip"><Icon name="time_lost" /></span>
          <p className="live-hero-label">Time lost per submittal</p>
          <p className="live-hero-value">{t.mean === null ? "–" : <>{t.atLeast ? <small>at least</small> : <small>about</small>}{days(timeShown)}<em>days</em></>}</p>
          <p className="live-hero-how">waiting on resubmissions: extra review rounds × the delay each one causes</p>
          <p className="live-hero-n">{t.answered ? <>answers from {days(t.low!)} to {days(t.high!)} days · {t.answered} {t.answered === 1 ? "answer" : "answers"}</> : "no answer yet"}</p>
        </article>
        <article className="live-hero" style={{ ["--i" as string]: 1 }}>
          <span key={String(m.mean)} className="live-hero-icon live-drop"><Icon name="money_lost" /></span>
          <p className="live-hero-label">Money lost per misfit on site</p>
          <p className="live-hero-value">{m.mean === null ? "–" : <>{m.atLeast ? <small>at least</small> : <small>about</small>}{euros(moneyShown)}</>}</p>
          <p className="live-hero-how">to fix one approved item that did not fit once it reached site</p>
          <p className="live-hero-n">{m.answered ? <>answers from “{m.lowest}” to “{m.highest}” · {m.answered} {m.answered === 1 ? "answer" : "answers"}</> : "no answer yet"}</p>
        </article>
      </div>

      {data.n > 0 && (
        <>
          <div className="live-smalls">
            {smalls.map((x, i) => (
              <div key={x.id} className="live-small" style={{ ["--i" as string]: i + 2 }} title={`${x.n} ${x.n === 1 ? "answer" : "answers"}`}>
                <Icon name={x.id} />
                <div><b key={x.at} className="live-pop">{x.value}</b><span>{x.label}</span></div>
              </div>
            ))}
          </div>
          {data.reasons.length > 0 && (
            <p className="live-line"><Icon name="reasons" /><span><b>Why forms come back most:</b> {data.reasons.map((x) => `${x.label} (${x.n})`).join(" · ")}</span></p>
          )}
          <button type="button" className={`live-fold${open ? " open" : ""}`} aria-expanded={open} aria-controls="live-answers" onClick={() => setOpen((o) => !o)}>
            <span>{open ? "Hide" : "See"} the answers to every question</span>
            <span className="meta">{data.n} {data.n === 1 ? "person" : "people"}, counted · no one's answers shown one by one</span>
            <svg className="live-chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <div id="live-answers" className={`live-answers${open ? " open" : ""}`}>
            <div>
              {data.results.map((r, i) => (
                <section key={r.id} className="live-q">
                  <h4><span className="survey-n">{i + 1}</span>{r.text}<span className="meta"> · {r.answered} answered</span></h4>
                  <QuestionBars r={r} />
                </section>
              ))}
            </div>
          </div>
          <p className="live-foot">
            People's own estimates, not measurements. Answers are ranges: averages use each range's middle; “at least” when an
            open range such as “over a month” is included; “don't know” is left out.
          </p>
        </>
      )}
    </section>
  );
}
