// The rules RightFit checks for the project's country, as the laptop's Rules screen lists them (app/review/views/rules.js):
// the law with its source and where each rule stands, the consultant's own rules, and the reviewers' checklist.
// Imported from the laptop with the packages; changed there for now.
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

const dmy = (iso: string) => iso.split("-").reverse().join(".");
const words = (s: string) => (s || "").replace(/;/g, ", ").replace(/\|/g, " or ").replace(/_/g, " ");
const today = new Date().toISOString().slice(0, 10);
const when = (r: LawRule) => (r.valid_to ? `until ${dmy(r.valid_to)}` : r.valid_from > today ? `from ${dmy(r.valid_from)}` : "");

// A consultant's rule as one sentence: who it applies to, what it checks, what happens if it is not met
function sentence(r: ConsultantRule, names: ProjectRules["mine"]) {
  const reading = (k: string) => k.split("|").map((x) => (names.values[x] || words(x)).replace(/ \((form|data sheet)\)$/, "").replace(/\s*included$/i, "")).join(" or ");
  const who = FAMILIES[r.family] || words(r.family).replace(/^./, (c) => c.toUpperCase());
  const what = {
    brand: `the brand is ${r.value.split(";").map((b) => b.trim()).filter(Boolean).join(" or ")}`,
    value: `${reading(r.field)} is ${OPS[r.operator] ?? ""} ${r.value} ${r.unit}`.replace(/\s+/g, " "),
    document: `a ${names.doc_types[r.field] || words(r.field)} is attached`,
    included: `${reading(r.field).toLowerCase()} is included`,
    reminder: `check by hand: ${r.text}`,
  }[r.kind] ?? r.text;
  return { who: `${who}${r.application ? ` used for ${words(r.application)}` : ""}`, what, effect: EFFECTS[r.effect] ?? r.effect };
}

export function Rules({ projectId }: { projectId: string }) {
  const { data, error } = useData<ProjectRules>(`/api/projects/${projectId}/rules`);
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const tally = new Map<string, number>();
  data.law.forEach((r) => tally.set(r.status, (tally.get(r.status) ?? 0) + 1));
  const blocking = data.checklist.filter((c) => c.blocking === "yes").length;
  return (
    <>
      <p className="sheet-note">
        RightFit checks the law, the reviewers' checklist and the consultant's own rules, for {country(data.location)} and the EU.
        A rule not read in the official text is never presented as a legal requirement, and the consultant's rules are preferences:
        the answer says "the consultant asks", never that the law asks. The rules are changed in RightFit on the laptop for now.
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
              {data.law.map((r) => (
                <tr key={r.rule_id}>
                  <td className="nowrap">{LAYER[r.jurisdiction] ?? r.jurisdiction}<span className="sub typed small">{r.rule_id}</span></td>
                  <td className="wrap">{r.requirement}</td>
                  <td className="wrap">
                    {r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.code}</a> : r.code}{r.clause ? `, ${r.clause}` : ""}
                    {when(r) && <span className="sub">Applies {when(r)}</span>}
                  </td>
                  <td>{words(r.applies_to)}</td>
                  <td>{STATUS[r.status] ?? r.status}{r.verified_on && <span className="sub">Read on {dmy(r.verified_on)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sheet" aria-label="The consultant's own rules">
        <div className="sheet-head"><span className="lab">The consultant's own rules</span><span className="count">{data.mine.rules.length}</span></div>
        <ul className="my-rules">
          {data.mine.rules.map((r) => {
            const s = sentence(r, data.mine);
            return (
              <li key={r.rule_id} className={r.active === "yes" ? "" : "off"}>
                <span className={`chip${r.active === "yes" ? " ok" : ""}`}>{r.active === "yes" ? "On" : "Off"}</span>
                <div><b>{s.who}</b>: {s.what}. <span className="meta">If not: {s.effect}.</span>
                  <span className="sub">{r.rule_id} · {r.source}</span></div>
              </li>
            );
          })}
          {!data.mine.rules.length && <li className="empty">No rules of the consultant's own yet.</li>}
        </ul>
      </section>

      <section className="sheet" aria-label="The reviewers' checklist">
        <div className="sheet-head">
          <span className="lab">The reviewers' checklist, from past reviewers' comments</span>
          <span className="count">{data.checklist.length} items, {blocking} blocking</span>
        </div>
        <div className="table-wrap">
          <table className="table rules-table">
            <thead><tr><th>Item</th><th>What it asks</th><th>How it is checked</th><th>For</th><th>If missing</th></tr></thead>
            <tbody>
              {data.checklist.map((c) => (
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
