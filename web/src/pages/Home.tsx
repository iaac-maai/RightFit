// The first page: what waits for this person, then their projects
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ROLE_LABEL } from "../../worker/roles";
import { api, go, navigate, post } from "../api";
import { aRole, country, day, greeting, plural } from "../format";
import { ARROW, Icon, Modal, PLUS } from "../ui";
import type { HomeData, Session, WaitingInvitation } from "../types";

export function Home({ session }: { session: Session }) {
  const [data, setData] = useState<HomeData | null>(null);
  const [error, setError] = useState("");
  const [opening, setOpening] = useState(false);

  const load = useCallback(() => api<HomeData>("/api/home").then(setData, (err: Error) => setError(err.message)), []);
  useEffect(() => { void load(); }, [load]);

  const waiting = data?.invitations ?? [];
  const projects = data?.projects ?? [];
  const summary = !data ? "" : [
    plural(projects.length, "project", "projects"),
    waiting.length ? `${plural(waiting.length, "invitation waits", "invitations wait")} for you` : "",
  ].filter(Boolean).join(" · ");

  return (
    <div className="screen">
      <header className="screen-head">
        <h1>{greeting(session.user.name)}</h1>
        <button type="button" className="btn p" onClick={() => setOpening(true)}><Icon d={PLUS} /> Open a project</button>
        <p>{summary || " "}</p>
      </header>
      {error && <p className="err" role="alert">{error}</p>}

      {waiting.length > 0 && (
        <section className="sheet waiting" aria-label="Waiting for you">
          <div className="sheet-head"><span className="lab">Waiting for you</span></div>
          {waiting.map((invitation) => <Waiting key={invitation.id} invitation={invitation} onAnswered={load} />)}
        </section>
      )}

      {data && projects.length === 0 && waiting.length === 0 && (
        <section className="sheet first">
          <span className="lab">No project yet</span>
          <h2>Open a project, or wait for an invitation.</h2>
          <p>A consultant opens the project and brings in the contractor and the other reviewers. If someone has invited you, open the link they sent you, signed in with the address it was sent to.</p>
          <button type="button" className="btn p" onClick={() => setOpening(true)}><Icon d={PLUS} /> Open a project</button>
        </section>
      )}

      {projects.length > 0 && (
        <section className="sheet" aria-label="Your projects">
          <div className="sheet-head"><span className="lab">Your projects</span><span className="count">{projects.length}</span></div>
          <div className="rows">
            {projects.map((p) => (
              <a key={p.id} className="row project-row" href={`/p/${p.id}`} onClick={go(`/p/${p.id}`)}>
                <span className="typed name">{p.name}</span>
                <span className="meta">{country(p.country)}</span>
                <span className="chip">{ROLE_LABEL[p.role]}</span>
                <span className="meta">{plural(p.people, "person", "people")}</span>
                <Icon d={ARROW} />
              </a>
            ))}
          </div>
        </section>
      )}
      <NewProject open={opening} onClose={() => setOpening(false)} />
    </div>
  );
}

function Waiting({ invitation, onAnswered }: { invitation: WaitingInvitation; onAnswered: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const answer = async (action: "accept" | "decline") => {
    setBusy(true);
    setError("");
    try {
      const done = await post<{ projectId?: string }>(`/api/invitations/${invitation.id}/${action}`);
      if (done.projectId) navigate(`/p/${done.projectId}`);
      else onAnswered();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  const from = [invitation.invitedBy, invitation.inviterCompany].filter(Boolean).join(", ");
  return (
    <div className="row waiting-row">
      <div className="waiting-what">
        <span className="typed">{invitation.project}</span>
        <span>{from || "Someone"} invites you as {aRole(invitation.role)}{invitation.company ? `, for ${invitation.company}` : ""}. Until {day(invitation.expiresAt)}.</span>
        {error && <span className="err" role="alert">{error}</span>}
      </div>
      <div className="actions">
        <button type="button" className="btn p" disabled={busy} onClick={() => void answer("accept")}>Join as {ROLE_LABEL[invitation.role].toLowerCase()}</button>
        <button type="button" className="link" disabled={busy} onClick={() => void answer("decline")}>Decline</button>
      </div>
    </div>
  );
}

function NewProject({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const { id } = await post<{ id: string }>("/api/projects", { name: form.get("name"), country: form.get("country"), company: form.get("company") });
      onClose();
      navigate(`/p/${id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="Open a project">
      <form className="stack" onSubmit={(e) => void submit(e)}>
        <p className="sheet-note">You will be its consultant: you bring in the contractor and the other reviewers, and they bring in the rest.</p>
        <label className="field">
          <span className="lab">Project name</span>
          <input name="name" type="text" required maxLength={120} autoFocus />
        </label>
        <div className="field-row">
          <label className="field">
            <span className="lab">Country</span>
            <select name="country" defaultValue="RO">
              <option value="RO">Romania</option>
              <option value="ES">Spain</option>
            </select>
          </label>
          <label className="field">
            <span className="lab">Your company</span>
            <input name="company" type="text" maxLength={120} />
          </label>
        </div>
        {error && <p className="err" role="alert">{error}</p>}
        <div className="actions">
          <button className="btn p" disabled={busy}>Open the project</button>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Modal>
  );
}
