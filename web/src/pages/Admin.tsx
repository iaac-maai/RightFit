// Management: for the people who run RightFit. Every account and project, the activity log, and the few things that
// may need putting right. The Worker refuses all of it to anyone else, and logs every change made here.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ROLES, ROLE_LABEL, type Role } from "../../worker/roles";
import { api, go, navigate, post } from "../api";
import { country, day, plural } from "../format";
import { Modal } from "../ui";
import { Inside } from "./Inside";
import type { AdminEvent, AdminMember, AdminOverview, AdminPerson, AdminProjectData, AdminProjectRow } from "../types";

type Tab = "overview" | "people" | "projects" | "activity" | "inside";

// How each logged action reads, from the details it carries (role names come as labels, for example "Subcontractor")
const a = (label: unknown) => (typeof label === "string" ? `${/^[aeiou]/i.test(label) ? "an" : "a"} ${label.toLowerCase()}` : "someone");
const lower = (label: unknown) => (typeof label === "string" ? label.toLowerCase() : "");
const ACTION: Record<string, (d: Record<string, unknown>) => string> = {
  "account.created": () => "created an account",
  "account.deleted": () => "deleted their account",
  "terms.accepted": (d) => `accepted the terms of ${String(d.version ?? "")}`,
  "project.opened": () => "opened the project and accepted the data processing agreement",
  "project.dpa_accepted": (d) => `accepted the data processing agreement of ${String(d.version ?? "")} for the project`,
  "package.answered": (d) => (d.answer ? `recorded answer ${String(d.answer)} for ${String(d.code ?? "")}` : `cleared the answer of ${String(d.code ?? "")}`),
  "invitation.sent": (d) => `invited ${a(d.role)}`,
  "invitation.withdrawn": () => "withdrew an invitation",
  "invitation.declined": () => "declined an invitation",
  "member.joined": (d) => `joined as ${lower(d.role)}`,
  "member.removed": (d) => `took out ${a(d.role)}`,
  "admin.role_changed": (d) => `changed a role from ${lower(d.from)} to ${lower(d.to)}`,
  "admin.member_removed": (d) => `took out ${a(d.role)}`,
  "admin.project_deleted": (d) => `deleted the project ${String(d.name ?? "")}`,
  "admin.invitation_withdrawn": () => "withdrew an invitation",
  "admin.signed_out": () => "signed someone out everywhere",
  "admin.account_deleted": () => "deleted an account",
  "project.imported": (d) => `got its data from the laptop: ${String(d.packages ?? 0)} packages, ${String(d.files ?? 0)} files, ${String(d.boqLines ?? 0)} BOQ lines`,
  "team.unlocked": () => "opened a locked project with the team password",
  "team.unlock_failed": () => "gave a wrong team password",
  "review.confirmed": (d) => `confirmed ${String(d.readings ?? 0)} readings in ${String(d.code ?? "a package")}`,
  "review.decided": (d) => `decided on findings in ${String(d.code ?? "a package")}`,
  "review.ai_decided": (d) => `decided on an AI suggestion in ${String(d.code ?? "a package")}: ${String(d.status ?? "")}`,
  "review.dated": (d) => `changed the review dates of ${String(d.code ?? "a package")}`,
  "package.added": (d) => `added the package ${String(d.code ?? "")} on the site`,
  "rules.added": () => "added a consultant's rule",
  "rules.switched": (d) => `switched the consultant's rule ${String(d.rule ?? "")} ${d.active ? "on" : "off"}`,
};

const when = (iso: string) => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function EventRows({ events, showProject }: { events: AdminEvent[]; showProject: boolean }) {
  if (!events.length) return <p className="empty">Nothing has happened yet.</p>;
  return (
    <div className="rows">
      {events.map((e) => {
        const said = ACTION[e.action]?.(e.detail) ?? e.action;
        return (
          <div key={e.id} className="row event-row">
            <span className="typed when">{when(e.at)}</span>
            <span className="event-what">
              <b>{e.actor ?? (e.action === "project.imported" ? "RightFit" : "A deleted account")}</b> {said}
              {e.action.startsWith("admin.") && <span className="chip">Management</span>}
            </span>
            {showProject && e.projectId && e.project && (
              <a className="event-project" href={`/admin/p/${e.projectId}`} onClick={go(`/admin/p/${e.projectId}`)}>{e.project}</a>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function Admin({ tab }: { tab: Tab }) {
  const tabs: [Tab, string][] = [["overview", "Overview"], ["people", "People"], ["projects", "Projects"], ["activity", "Activity"], ["inside", "Inside RightFit"]];
  return (
    <div className="screen">
      <header className="screen-head">
        <h1>Management</h1>
        <p>Only RightFit's own team sees this page, signed in with Google. Everything done here goes in the activity log.</p>
      </header>
      <nav className="tabs" aria-label="Management">
        {tabs.map(([key, label]) => {
          const path = key === "overview" ? "/admin" : `/admin/${key}`;
          return <a key={key} href={path} onClick={go(path)} aria-current={tab === key ? "page" : undefined}>{label}</a>;
        })}
      </nav>
      {tab === "overview" && <Overview />}
      {tab === "people" && <People />}
      {tab === "projects" && <Projects />}
      {tab === "activity" && <Activity />}
      {tab === "inside" && <Inside />}
    </div>
  );
}

function useLoad<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => api<T>(path).then(setData, (err: Error) => setError(err.message)), [path]);
  useEffect(() => { void load(); }, [load]);
  return { data, error, load, setError };
}

function Overview() {
  const { data, error } = useLoad<AdminOverview>("/api/admin/overview");
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  const figures: [string, number][] = [
    ["People", data.counts.people], ["With Google", data.counts.google], ["New this week", data.counts.newPeople],
    ["Projects", data.counts.projects], ["Invitations waiting", data.counts.pending],
  ];
  return (
    <>
      <section className="sheet figures" aria-label="In numbers">
        {figures.map(([label, n]) => (
          <div key={label} className="fld"><span className="lab">{label}</span><span className="typed big">{n}</span></div>
        ))}
      </section>
      <section className="sheet" aria-label="Latest activity">
        <div className="sheet-head"><span className="lab">Latest activity</span><span className="count">kept 12 months</span></div>
        <EventRows events={data.events.slice(0, 12)} showProject />
      </section>
    </>
  );
}

function Activity() {
  const { data, error } = useLoad<AdminOverview>("/api/admin/overview");
  if (error) return <p className="err" role="alert">{error}</p>;
  if (!data) return <span className="spinner" aria-label="Loading" />;
  return (
    <section className="sheet" aria-label="Activity">
      <div className="sheet-head"><span className="lab">The last {data.events.length} events</span><span className="count">kept 12 months</span></div>
      <EventRows events={data.events} showProject />
    </section>
  );
}

function People() {
  const { data, error, load, setError } = useLoad<AdminPerson[]>("/api/admin/people");
  const [deleting, setDeleting] = useState<AdminPerson | null>(null);
  const signOut = async (p: AdminPerson) => {
    try { await post(`/api/admin/people/${p.id}/sign-out`); void load(); } catch (err) { setError((err as Error).message); }
  };
  if (!data) return error ? <p className="err" role="alert">{error}</p> : <span className="spinner" aria-label="Loading" />;
  return (
    <section className="sheet" aria-label="People">
      <div className="sheet-head"><span className="lab">Everyone with an account</span><span className="count">{data.length}</span></div>
      {error && <p className="err pad" role="alert">{error}</p>}
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Name</th><th>Email</th><th>Signs in with</th><th>Projects</th><th>Since</th><th aria-label="Actions" /></tr></thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id}>
                <td><b>{p.name}</b></td>
                <td className="typed small">{p.email}{p.verified && <span className="chip ok">verified</span>}</td>
                <td>{p.methods.map((m) => (m === "google" ? "Google" : "password")).join(", ") || "nothing yet"}</td>
                <td>{p.projects}</td>
                <td>{day(p.createdAt)}</td>
                <td className="row-actions">
                  <button type="button" className="link" disabled={!p.sessions} onClick={() => void signOut(p)}>
                    {p.sessions ? `Sign out (${p.sessions})` : "Signed out"}
                  </button>
                  <button type="button" className="link quiet" onClick={() => setDeleting(p)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Confirm
        open={deleting !== null}
        title={deleting ? `Delete ${deleting.name}'s account?` : ""}
        body="The account goes, with its sessions, sign-in links and place in every project, and can't come back. A project where this is the only consultant must go to someone else first."
        action="Delete the account"
        onClose={() => setDeleting(null)}
        onConfirm={async () => { await post(`/api/admin/people/${deleting!.id}/delete`); setDeleting(null); void load(); }}
      />
    </section>
  );
}

function Projects() {
  const { data, error } = useLoad<AdminProjectRow[]>("/api/admin/projects");
  if (!data) return error ? <p className="err" role="alert">{error}</p> : <span className="spinner" aria-label="Loading" />;
  return (
    <section className="sheet" aria-label="Projects">
      <div className="sheet-head"><span className="lab">Every project</span><span className="count">{data.length}</span></div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Project</th><th>Country</th><th>Consultants</th><th>People</th><th>Waiting</th><th>Opened</th></tr></thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id}>
                <td><a className="typed" href={`/admin/p/${p.id}`} onClick={go(`/admin/p/${p.id}`)}>{p.name}</a></td>
                <td>{country(p.country)}</td>
                <td>{p.consultants ?? "none"}</td>
                <td>{p.people}</td>
                <td>{p.pending}</td>
                <td>{day(p.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function AdminProject({ id, onLoaded }: { id: string; onLoaded: (p: { id: string; name: string }) => void }) {
  const { data, error, load, setError } = useLoad<AdminProjectData>(`/api/admin/projects/${id}`);
  const [removing, setRemoving] = useState<AdminMember | null>(null);
  const [deleting, setDeleting] = useState(false);
  useEffect(() => { if (data) onLoaded({ id: data.project.id, name: data.project.name }); }, [data, onLoaded]);

  if (!data) return <div className="screen">{error ? <p className="err" role="alert">{error}</p> : <span className="spinner" aria-label="Loading" />}</div>;
  const { project, people, invitations, events } = data;
  const byId = new Map(people.map((p) => [p.id, p.name]));

  const changeRole = async (m: AdminMember, role: Role) => {
    setError("");
    try { await post(`/api/admin/projects/${id}/members/${m.id}/role`, { role }); } catch (err) { setError((err as Error).message); }
    void load();
  };
  const withdraw = async (invitationId: string) => {
    try { await post(`/api/admin/invitations/${invitationId}/withdraw`); void load(); } catch (err) { setError((err as Error).message); }
  };

  return (
    <div className="screen">
      <a className="back" href="/admin/projects" onClick={go("/admin/projects")}>Management · Projects</a>
      <header className="project-head">
        <div className="fld title"><span className="lab">Project</span><h1 className="typed">{project.name}</h1></div>
        <div className="fld"><span className="lab">Country</span><span className="typed">{country(project.country)}</span></div>
        <div className="fld"><span className="lab">Opened</span><span className="typed">{day(project.createdAt)}</span></div>
        <div className="fld"><span className="lab">Data processing agreement</span><span className="typed">{project.dpaAcceptedAt ? `${project.dpaVersion}, accepted ${day(project.dpaAcceptedAt)}` : "not recorded"}</span></div>
      </header>
      {error && <p className="err" role="alert">{error}</p>}

      <section className="sheet" aria-label="The team">
        <div className="sheet-head"><span className="lab">The whole team</span><span className="count">{plural(people.length, "person", "people")}</span></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Email</th><th>Company</th><th>Role</th><th>Brought in by</th><th>Since</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {people.map((m) => (
                <tr key={m.id}>
                  <td><b>{m.name}</b></td>
                  <td className="typed small">{m.email}</td>
                  <td>{m.company || "—"}</td>
                  <td>
                    <select aria-label={`${m.name}'s role`} value={m.role} onChange={(e) => void changeRole(m, e.target.value as Role)}>
                      {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                    </select>
                  </td>
                  <td>{m.invitedBy ? byId.get(m.invitedBy) ?? "someone no longer here" : "opened the project"}</td>
                  <td>{day(m.joinedAt)}</td>
                  <td><button type="button" className="link quiet" onClick={() => setRemoving(m)}>Take out</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {invitations.length > 0 && (
        <section className="sheet" aria-label="Invitations waiting">
          <div className="sheet-head"><span className="lab">Invitations waiting</span><span className="count">{invitations.length}</span></div>
          <div className="rows">
            {invitations.map((i) => (
              <div key={i.id} className="row">
                <span className="typed small grow">{i.email}</span>
                <span className="chip">{ROLE_LABEL[i.role]}</span>
                <span className="meta">from {byId.get(i.invitedBy) ?? "someone no longer here"}, until {day(i.expiresAt)}</span>
                <button type="button" className="link quiet" onClick={() => void withdraw(i.id)}>Withdraw</button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="sheet" aria-label="This project's activity">
        <div className="sheet-head"><span className="lab">This project's activity</span></div>
        <EventRows events={events} showProject={false} />
      </section>

      <section className="sheet danger-zone" aria-label="Delete the project">
        <div><b>Delete this project</b><p className="sheet-note">The project, its members and its invitations go for good. The people keep their accounts.</p></div>
        <button type="button" className="btn danger" onClick={() => setDeleting(true)}>Delete the project</button>
      </section>

      <Confirm
        open={removing !== null}
        title={removing ? `Take ${removing.name} out of ${project.name}?` : ""}
        body="Their invitations that nobody has answered yet are withdrawn. The people they brought in stay."
        action="Take them out"
        onClose={() => setRemoving(null)}
        onConfirm={async () => { await post(`/api/admin/projects/${id}/members/${removing!.id}/remove`); setRemoving(null); void load(); }}
      />
      <DeleteProject open={deleting} name={project.name} onClose={() => setDeleting(false)} onConfirm={async (name) => {
        await post(`/api/admin/projects/${id}/delete`, { name });
        navigate("/admin/projects");
      }} />
    </div>
  );
}

function Confirm({ open, title, body, action, onClose, onConfirm }: {
  open: boolean; title: string; body: string; action: string; onClose: () => void; onConfirm: () => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setError(""); setBusy(false); } }, [open]);
  const run = async () => {
    setBusy(true);
    try { await onConfirm(); } catch (err) { setError((err as Error).message); setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p>{body}</p>
      {error && <p className="err" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="btn danger" disabled={busy} onClick={() => void run()}>{action}</button>
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

function DeleteProject({ open, name, onClose, onConfirm }: { open: boolean; name: string; onClose: () => void; onConfirm: (name: string) => Promise<void> }) {
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setTyped(""); setError(""); } }, [open]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    try { await onConfirm(typed); } catch (err) { setError((err as Error).message); }
  };
  return (
    <Modal open={open} onClose={onClose} title={`Delete ${name}?`}>
      <form className="stack" onSubmit={(e) => void submit(e)}>
        <p>This can't be undone. Type the project's name to confirm.</p>
        <label className="field">
          <span className="lab">Project name</span>
          <input type="text" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        </label>
        {error && <p className="err" role="alert">{error}</p>}
        <div className="actions">
          <button className="btn danger" disabled={typed !== name}>Delete the project</button>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Modal>
  );
}
