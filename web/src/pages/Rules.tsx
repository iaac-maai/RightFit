// The rules RightFit checks for the project's country, as the laptop's Rules screen lists them (app/review/views/rules.js):
// the law with its source and where each rule stands, the consultant's own rules, and the reviewers' checklist.
// The consultant switches their own rules on or off and writes new ones by hand; each change goes to the engine,
// which reviews every package again with it.
import { useState, type FormEvent } from "react";
import { post } from "../api";
import { country } from "../format";
import type { ConsultantRule, LawRule, ProjectRules } from "../types";
import { useData } from "./ProjectData";

const STATUS: Record<string, string> = {
  verified_official: "Read in the official journal",
  verified_secondary: "Read in a copy, to check on the official text",
  to_confirm: "To confirm on the official text",
  practice: "Reviewers' practice",
  engineer_input: "Set by the team's engineer",
  guidance: "Manufacturer's recommendation",
};
const EFFECTS: Record<string, string> = { B: "a comment (B)", C: "revise and resubmit (C)", info: "information only" };
const OPS: Record<string, string> = { ">=": "at least", "<=": "at most", "=": "" };
const FAMILIES: Record<string, string> = { all: "Every product", pump: "Pumps", ahu: "Air handling units", outdoor_unit: "Outdoor units", dx_kit: "DX kits" };
const LAYER: Record<string, string> = { EU: "European Union", RO: "Romania", ES: "Spain", ANY: "Practice" };
const KINDS: [string, string][] = [["brand", "the brand"], ["value", "a value"], ["document", "a document"], ["included", "that something is included"],
  ["reminder", "something to check by hand"]];
const INCLUDED = ["controller_included", "bms_included", "float_switch", "controller_included|float_switch"]; // as on the laptop

const dmy = (iso: string) => iso.split("-").reverse().join(".");
const words = (s: string) => (s || "").replace(/;/g, ", ").replace(/\|/g, " or ").replace(/_/g, " ");
const today = new Date().toISOString().slice(0, 10);
const when = (r: LawRule) => (r.valid_to ? `until ${dmy(r.valid_to)}` : r.valid_from > today ? `from ${dmy(r.valid_from)}` : "");
const reading = (k: string, names: ProjectRules["mine"]) =>
  k.split("|").map((x) => (names.values[x] || words(x)).replace(/ \((form|data sheet)\)$/, "").replace(/\s*included$/i, "")).join(" or ");

// A consultant's rule as one sentence: who it applies to, what it checks, what happens if it is not met
function sentence(r: ConsultantRule, names: ProjectRules["mine"]) {
  const who = FAMILIES[r.family] || words(r.family).replace(/^./, (c) => c.toUpperCase());
  const what = {
    brand: `the brand is ${r.value.split(";").map((b) => b.trim()).filter(Boolean).join(" or ")}`,
    value: `${reading(r.field, names)} is ${OPS[r.operator] ?? ""} ${r.value} ${r.unit}`.replace(/\s+/g, " "),
    document: `a ${names.doc_types[r.field] || words(r.field)} is attached`,
    included: `${reading(r.field, names).toLowerCase()} is included`,
    reminder: `check by hand: ${r.text}`,
  }[r.kind] ?? r.text;
  return { who: `${who}${r.application ? ` used for ${words(r.application)}` : ""}`, what, effect: EFFECTS[r.effect] ?? r.effect };
}

export function Rules({ projectId }: { projectId: string }) {
  const { data, error } = useData<ProjectRules>(`/api/projects/${projectId}/rules`);
  const [edited, setEdited] = useState<ProjectRules | null>(null);
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const r = edited ?? data;
  const change = async (body: Record<string, unknown>, done: string, failed: string) => {
    setBusy(true);
    setSaid(null);
    try {
      setEdited(await post<ProjectRules>(`/api/projects/${projectId}/rules/change`, body));
      setSaid({ ok: true, text: done });
      return true;
    } catch (err) {
      setSaid({ ok: false, text: `${failed}: ${(err as Error).message}.` });
      return false;
    } finally {
      setBusy(false);
    }
  };
  const tally = new Map<string, number>();
  r.law.forEach((x) => tally.set(x.status, (tally.get(x.status) ?? 0) + 1));
  const blocking = r.checklist.filter((c) => c.blocking === "yes").length;
  return (
    <>
      <p className="sheet-note">
        RightFit checks the law, the reviewers' checklist and the consultant's own rules, for {country(r.location)} and the EU.
        A rule not read in the official text is never presented as a legal requirement, and the consultant's rules are preferences:
        the answer says "the consultant asks", never that the law asks.
      </p>

      <section className="sheet" aria-label="Rules of the law">
        <div className="sheet-head">
          <span className="lab">Rules of the law and practice</span>
          <span className="count">{[...tally].map(([s, n]) => `${n} ${(STATUS[s] ?? s).toLowerCase()}`).join(" · ")}</span>
        </div>
        <div className="table-wrap">
          <table className="table rules-table">
            <thead><tr><th>Where</th><th>What it asks</th><th>Source</th><th>Applies to</th><th>Where it stands</th></tr></thead>
            <tbody>
              {r.law.map((x) => (
                <tr key={x.rule_id}>
                  <td className="nowrap">{LAYER[x.jurisdiction] ?? x.jurisdiction}<span className="sub typed small">{x.rule_id}</span></td>
                  <td className="wrap">{x.requirement}</td>
                  <td className="wrap">
                    {x.source_url ? <a href={x.source_url} target="_blank" rel="noreferrer">{x.code}</a> : x.code}{x.clause ? `, ${x.clause}` : ""}
                    {when(x) && <span className="sub">Applies {when(x)}</span>}
                  </td>
                  <td>{words(x.applies_to)}</td>
                  <td>{STATUS[x.status] ?? x.status}{x.verified_on && <span className="sub">Read on {dmy(x.verified_on)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sheet" aria-label="The consultant's own rules">
        <div className="sheet-head"><span className="lab">The consultant's own rules</span><span className="count">{r.mine.rules.length}</span></div>
        <ul className="my-rules">
          {r.mine.rules.map((rule) => {
            const s = sentence(rule, r.mine);
            const on = rule.active === "yes";
            return (
              <li key={rule.rule_id} className={on ? "" : "off"}>
                {r.mayEdit ? (
                  <label className="toggle">
                    <input type="checkbox" role="switch" checked={on} disabled={busy} aria-label={`Rule ${rule.rule_id} on`}
                      onChange={(e) => void change({ op: "rule_active", rule_id: rule.rule_id, active: e.target.checked },
                        `${rule.rule_id} is ${e.target.checked ? "on" : "off"}; every package was reviewed again.`, `${rule.rule_id} was not changed`)} />
                    <span aria-hidden="true" />
                  </label>
                ) : <span className={`chip${on ? " ok" : ""}`}>{on ? "On" : "Off"}</span>}
                <div><b>{s.who}</b>: {s.what}. <span className="meta">If not: {s.effect}.</span>
                  <span className="sub">{rule.rule_id} · {rule.source}</span></div>
              </li>
            );
          })}
          {!r.mine.rules.length && <li className="empty">No rules of the consultant's own yet.</li>}
        </ul>
        {said && <p className={said.ok ? "sheet-note band" : "err pad"} role={said.ok ? "status" : "alert"}>{said.text}</p>}
        {r.mayEdit && <NewRule names={r.mine} busy={busy}
          onSave={(rule) => change({ op: "new_rule", rule }, "Saved. It applies to every package from now on.", "The rule was not saved")} />}
      </section>

      <section className="sheet" aria-label="The reviewers' checklist">
        <div className="sheet-head">
          <span className="lab">The reviewers' checklist, from past reviewers' comments</span>
          <span className="count">{r.checklist.length} items, {blocking} blocking</span>
        </div>
        <div className="table-wrap">
          <table className="table rules-table">
            <thead><tr><th>Item</th><th>What it asks</th><th>How it is checked</th><th>For</th><th>If missing</th></tr></thead>
            <tbody>
              {r.checklist.map((c) => (
                <tr key={c.id}>
                  <td className="nowrap typed small">{c.id}</td>
                  <td className="wrap">{c.item}</td>
                  <td className="wrap">{c.how_to_check}</td>
                  <td>{words(c.family)}</td>
                  <td className="nowrap">{c.if_missing}{c.blocking === "yes" ? ", blocking" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

// A consultant's rule written by hand, field by field as on the laptop; the engine checks it before it is saved
function NewRule({ names, busy, onSave }: { names: ProjectRules["mine"]; busy: boolean; onSave: (rule: Record<string, string>) => Promise<boolean> }) {
  const [kind, setKind] = useState("brand");
  const fields: [string, string][] = kind === "document" ? Object.entries(names.doc_types)
    : kind === "included" ? INCLUDED.map((k) => [k, reading(k, names)]) : Object.entries(names.values);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const rule = Object.fromEntries([...new FormData(form)].map(([k, v]) => [k, String(v)]));
    if (await onSave(rule)) form.reset();
  };
  return (
    <details className="new-rule">
      <summary>Add a rule of your own</summary>
      <form className="hand" onSubmit={(e) => void submit(e)}>
        <label>Products<select name="family" defaultValue="all">
          <option value="all">every product</option>
          {(names.families ?? []).map((f) => <option key={f} value={f}>{words(f)}</option>)}
        </select></label>
        <label>Only when used for<input type="text" name="application" placeholder="optional, e.g. circulation" /></label>
        <label>What it checks<select name="kind" value={kind} onChange={(e) => setKind(e.target.value)}>
          {KINDS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
        </select></label>
        {["value", "document", "included"].includes(kind) && (
          <label>Which<select name="field">{fields.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
        )}
        {kind === "value" && (
          <label>Must be<select name="operator"><option value=">=">at least</option><option value="<=">at most</option><option value="=">exactly</option></select></label>
        )}
        {(kind === "brand" || kind === "value") && (
          <label>{kind === "brand" ? "Brands, separated by ;" : "Value"}<input type="text" name="value" placeholder={kind === "brand" ? "Grundfos;Wilo" : "16"} /></label>
        )}
        {kind === "value" && <label>Unit<input type="text" name="unit" placeholder="bar" /></label>}
        <label>If not met<select name="effect" defaultValue="B">{Object.entries(EFFECTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="wide">In a few words<input type="text" name="text" required maxLength={200} placeholder="pumps only from Grundfos" /></label>
        <div className="wide actions">
          <button type="submit" className="btn p" disabled={busy}>Save the rule</button>
          <span className="fine">Writing it in your own words for the AI to turn into a rule works in RightFit on the laptop.</span>
        </div>
      </form>
    </details>
  );
}
