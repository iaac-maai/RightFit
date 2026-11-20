// One project: the team drawn as the chain of who brought in whom, and inviting the next people
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { REVIEWERS, ROLE_LABEL, ROLE_NOTE, type Role } from "../../worker/roles";
import { ApiError, api, go, post } from "../api";
import { aRole, country, day, daysLeft, plural } from "../format";
import { Icon, Modal, Monogram, PLUS } from "../ui";
import type { CreatedInvitation, PendingInvitation, ProjectData, TeamPerson } from "../types";
import { Boq, PackageView, Packages, TeamLock } from "./ProjectData";

export type ProjectView = "team" | "packages" | "package" | "boq";

// The order of people under one inviter: reviewers first, then down the chain
const TIER: Record<Role, number> = { consultant: 0, designer: 1, site_supervisor: 1, client: 1, contractor: 2, subcontractor: 3 };

type Node = { person: TeamPerson; children: Node[]; invites: PendingInvitation[] };
type Preset = { role?: Role; email?: string; company?: string };

function chain(people: TeamPerson[], invitations: PendingInvitation[]) {
  const nodes = new Map<string, Node>(people.map((p) => [p.id, { person: p, children: [], invites: [] }]));
  const roots: Node[] = [];
  for (const p of people) {
    const parent = p.invitedBy ? nodes.get(p.invitedBy) : undefined;
    (parent ? parent.children : roots).push(nodes.get(p.id)!);
  }
  const loose: PendingInvitation[] = [];
  for (const i of invitations) (nodes.get(i.invitedBy)?.invites ?? loose).push(i);
  const order = (list: Node[]) => {
    list.sort((a, b) => TIER[a.person.role] - TIER[b.person.role] || a.person.joinedAt.localeCompare(b.person.joinedAt));
    list.forEach((n) => order(n.children));
  };
  order(roots);
  return { roots, loose };
}

export function Project({ id, view, code, onLoaded }: {
  id: string; view: ProjectView; code?: string; onLoaded: (p: { id: string; name: string }) => void;
}) {
  const [data, setData] = useState<ProjectData | null>(null);
  const [error, setError] = useState("");
  const [inviting, setInviting] = useState<Preset | null>(null);
  const [removing, setRemoving] = useState<TeamPerson | null>(null);
  const [locked, setLocked] = useState<string | null>(null); // the project's name, while it waits for the team password

  const load = useCallback(() => api<ProjectData>(`/api/projects/${id}`).then(
    (found) => { setLocked(null); setData(found); onLoaded({ id: found.project.id, name: found.project.name }); },
    (err: Error) => {
      if (err instanceof ApiError && err.data.need === "team") setLocked(String(err.data.project ?? "This project"));
      else setError(err.message);
    },
  ), [id, onLoaded]);
  useEffect(() => { setData(null); setError(""); void load(); }, [load]);

  if (locked) return <TeamLock name={locked} onUnlocked={() => void load()} />;
  if (error && !data) return <div className="screen"><p className="err" role="alert">{error}</p></div>;
  if (!data) return <div className="screen"><span className="spinner" aria-label="Loading" /></div>;

  const { project, me, people, invitations, mayInvite, mayRemove } = data;
  const { roots, loose } = chain(people, invitations);
  const seesAll = REVIEWERS.includes(me.role) || me.role === "contractor";

  const withdraw = async (invitation: PendingInvitation) => {
    try {
      await post(`/api/invitations/${invitation.id}/withdraw`);
      void load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const renew = (x: PendingInvitation) => setInviting({ role: x.role, email: x.email, company: x.company });
  // one list per inviter: the people they brought in, then the invitations still waiting
  const tree = (nodes: Node[], invites: PendingInvitation[]) => (
    <ul>
      {nodes.map((node) => (
        <li key={node.person.id}>
          <PersonRow person={node.person} me={me.id} mayRemove={mayRemove} onRemove={setRemoving} />
          {(node.children.length > 0 || node.invites.length > 0) && tree(node.children, node.invites)}
        </li>
      ))}
      {invites.map((i) => (
        <li key={i.id}><InviteRow invitation={i} onWithdraw={withdraw} onRenew={renew} /></li>
      ))}
    </ul>
  );

  return (
    <div className="screen">
      <header className="project-head">
        <div className="fld title"><span className="lab">Project</span><h1 className="typed">{project.name}</h1></div>
        <div className="fld"><span className="lab">Country</span><span className="typed">{country(project.country)}</span></div>
        <div className="fld"><span className="lab">You are</span><span className="typed">{ROLE_LABEL[me.role]}{me.company ? `, ${me.company}` : ""}</span></div>
        {mayInvite.length > 0 && (
          <button type="button" className="btn p" onClick={() => setInviting({})}><Icon d={PLUS} /> Invite someone</button>
        )}
      </header>
      {error && <p className="err" role="alert">{error}</p>}

      {(project.packages > 0 || project.boqLines > 0) && (
        <nav className="tabs" aria-label="The project">
          {([["team", "Team", `/p/${id}`], ["packages", `Packages (${project.packages})`, `/p/${id}/packages`],
             ["boq", `BOQ (${project.boqLines} lines)`, `/p/${id}/boq`]] as const).map(([key, label, path]) => (
            <a key={key} href={path} onClick={go(path)} aria-current={view === key || (key === "packages" && view === "package") ? "page" : undefined}>{label}</a>
          ))}
          {Boolean(project.locked) && <span className="lock-note">Locked: opened with the team password</span>}
        </nav>
      )}

      {view === "packages" && <Packages projectId={id} />}
      {view === "package" && code && <PackageView projectId={id} code={code} />}
      {view === "boq" && <Boq projectId={id} />}

      {view === "team" && <div className="project-grid">
        <section className="sheet team" aria-label="The team">
          <div className="sheet-head">
            <span className="lab">The team</span>
            <span className="count">{plural(people.length, "person", "people")}{invitations.length ? `, ${invitations.length} invited` : ""}</span>
          </div>
          {!seesAll && (
            <p className="sheet-note band">You see the reviewers, the contractor, the people who brought you in and your own firm's branch. Other firms don't see yours either.</p>
          )}
          <div className="tree">{tree(roots, loose)}</div>
        </section>

        <aside className="side">
          {mayInvite.length > 0 && (
            <section className="sheet" aria-label="Whom you can invite">
              <div className="sheet-head"><span className="lab">You can bring in</span></div>
              <ul className="role-list">
                {mayInvite.map((role) => (
                  <li key={role}>
                    <button type="button" className="role-row" onClick={() => setInviting({ role })}>
                      <span><b>{ROLE_LABEL[role]}</b>{role === me.role && <em> a colleague</em>}</span>
                      <span className="role-note">{ROLE_NOTE[role]}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section className="sheet soon" aria-label="Next">
            <div className="sheet-head"><span className="lab">Next in RightFit online</span></div>
            <p>The forms come here next. A subcontractor prepares a form, the contractor checks it with RightFit and sends it on, and the reviewers answer. Everyone sees whose turn it is, and since when.</p>
          </section>
        </aside>
      </div>}

      <InviteDialog project={project} me={me} mayInvite={mayInvite} preset={inviting} onClose={() => setInviting(null)} onCreated={() => void load()} />
      <RemoveDialog project={project} person={removing} onClose={() => setRemoving(null)} onRemoved={() => { setRemoving(null); void load(); }} />
    </div>
  );
}

function PersonRow({ person, me, mayRemove, onRemove }: { person: TeamPerson; me: string; mayRemove: boolean; onRemove: (p: TeamPerson) => void }) {
  return (
    <div className="who">
      <Monogram name={person.name} image={person.image} />
      <div className="who-main">
        <div className="who-line">
          <b>{person.name}</b>
          {person.id === me && <span className="you">you</span>}
          <span className="chip">{ROLE_LABEL[person.role]}</span>
        </div>
        <div className="who-meta">
          {person.company && <span className="typed">{person.company}</span>}
          <span>{person.email}</span>
          <span>since {day(person.joinedAt)}</span>
        </div>
      </div>
      {mayRemove && person.id !== me && (
        <button type="button" className="link quiet" onClick={() => onRemove(person)}>Remove</button>
      )}
    </div>
  );
}

function InviteRow({ invitation, onWithdraw, onRenew }: {
  invitation: PendingInvitation; onWithdraw: (i: PendingInvitation) => void; onRenew: (i: PendingInvitation) => void;
}) {
  const left = daysLeft(invitation.expiresAt);
  return (
    <div className="who pending">
      <Monogram name={invitation.email} pending />
      <div className="who-main">
        <div className="who-line">
          <span className="typed">{invitation.email}</span>
          <span className="chip">{ROLE_LABEL[invitation.role]}</span>
        </div>
        <div className="who-meta">
          {invitation.company && <span className="typed">{invitation.company}</span>}
          <span>{invitation.expired ? "the link has expired" : `invited, the link works ${left === 1 ? "one more day" : `${left} more days`}`}</span>
        </div>
      </div>
      {invitation.mayWithdraw && (
        <span className="row-actions">
          <button type="button" className="link" onClick={() => onRenew(invitation)}>New link</button>
          <button type="button" className="link quiet" onClick={() => onWithdraw(invitation)}>Withdraw</button>
        </span>
      )}
    </div>
  );
}

function InviteDialog({ project, me, mayInvite, preset, onClose, onCreated }: {
  project: ProjectData["project"]; me: ProjectData["me"]; mayInvite: Role[]; preset: Preset | null; onClose: () => void; onCreated: () => void;
}) {
  const [role, setRole] = useState<Role | "">("");
  const [company, setCompany] = useState("");
  const [created, setCreated] = useState<CreatedInvitation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!preset) return;
    const start = preset.role ?? (mayInvite.length === 1 ? mayInvite[0] : "");
    setRole(start);
    setCompany(preset.company ?? (start === me.role ? me.company : ""));
    setCreated(null);
    setError("");
    setCopied(false);
    // only when the dialog opens: the team reloads after an invitation is made, and that must not clear the link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset]);

  const pick = (next: Role) => {
    setRole(next);
    if (next === me.role && !company) setCompany(me.company); // a colleague: same firm
    if (next !== me.role && company === me.company) setCompany("");
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      setCreated(await post<CreatedInvitation>(`/api/projects/${project.id}/invitations`, { email: form.get("email"), role, company }));
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.link);
      setCopied(true);
    } catch {
      setCopied(false); // the clipboard can be refused: the link stays selectable in the box
    }
  };

  const mail = created && `mailto:${created.email}?subject=${encodeURIComponent(`Join ${project.name} on RightFit`)}&body=${encodeURIComponent(
    `Hello,\n\nI'm inviting you to ${project.name} on RightFit, as ${aRole(created.role)}.\n\n` +
    `Open this link and sign in with ${created.email}, with Google or with a password:\n${created.link}\n\n` +
    `The link works until ${day(created.expiresAt)}.\n`)}`;

  return (
    <Modal open={preset !== null} onClose={onClose} title={created ? "Send them the link" : `Invite someone to ${project.name}`}>
      {!created ? (
        <form className="stack" onSubmit={(e) => void submit(e)}>
          <fieldset className="role-pick">
            <legend className="lab">Their role</legend>
            {mayInvite.map((r) => (
              <label key={r} className={`role-opt${role === r ? " on" : ""}`}>
                <input type="radio" name="role" value={r} checked={role === r} onChange={() => pick(r)} required />
                <span>
                  <span><b>{ROLE_LABEL[r]}</b>{r === me.role && <em> a colleague</em>}</span>
                  <small>{ROLE_NOTE[r]}</small>
                </span>
              </label>
            ))}
          </fieldset>
          <label className="field">
            <span className="lab">Their email</span>
            <input name="email" type="email" required defaultValue={preset?.email ?? ""} autoComplete="off" />
          </label>
          <label className="field">
            <span className="lab">Their company</span>
            <input type="text" maxLength={120} value={company} onChange={(e) => setCompany(e.target.value)} />
          </label>
          {error && <p className="err" role="alert">{error}</p>}
          <div className="actions">
            <button className="btn p" disabled={busy || !role}>Create the invitation</button>
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
          </div>
        </form>
      ) : (
        <div className="stack">
          <p>Send this link to <span className="typed">{created.email}</span>. It works once, only for that address, until {day(created.expiresAt)}.</p>
          <div className="linkbox">
            <input readOnly value={created.link} className="typed" aria-label="The invitation link" onFocus={(e) => e.currentTarget.select()} />
            <button type="button" className="btn" onClick={() => void copy()}>{copied ? "Copied" : "Copy"}</button>
          </div>
          <div className="actions">
            {mail && <a className="btn p" href={mail}>Write the email</a>}
            <button type="button" className="btn" onClick={onClose}>Done</button>
          </div>
          <p className="fine">RightFit sends no email itself yet: the link goes in yours. Anyone who has it and signs in with that address joins as {aRole(created.role)}.</p>
        </div>
      )}
    </Modal>
  );
}

function RemoveDialog({ project, person, onClose, onRemoved }: {
  project: ProjectData["project"]; person: TeamPerson | null; onClose: () => void; onRemoved: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { setError(""); setBusy(false); }, [person]);
  const remove = async () => {
    if (!person) return;
    setBusy(true);
    try {
      await post(`/api/projects/${project.id}/members/${person.id}/remove`);
      onRemoved();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <Modal open={person !== null} onClose={onClose} title={person ? `Take ${person.name} out of ${project.name}?` : ""}>
      <p>Their invitations that nobody has answered yet are withdrawn. The people they brought in stay in the project.</p>
      {error && <p className="err" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="btn danger" disabled={busy} onClick={() => void remove()}>Take them out</button>
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
