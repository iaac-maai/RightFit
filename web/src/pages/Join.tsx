// Opening an invitation link while signed in: join, or see why not
import { useEffect, useState } from "react";
import { ROLE_LABEL } from "../../worker/roles";
import { ApiError, api, go, navigate, post, signOut } from "../api";
import { InvitationSheet } from "../ui";
import type { InvitationPreview, Session } from "../types";

export function Join({ token, session }: { token: string; session: Session }) {
  const [invitation, setInvitation] = useState<InvitationPreview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<InvitationPreview>(`/api/join/${token}`).then(setInvitation, (err: Error) => setError(err.message));
  }, [token]);

  const join = async () => {
    setBusy(true);
    setError("");
    try {
      const { projectId } = await post<{ projectId: string }>(`/api/join/${token}`);
      navigate(`/p/${projectId}`);
    } catch (err) {
      const projectId = err instanceof ApiError ? err.data.projectId : undefined;
      if (typeof projectId === "string") return navigate(`/p/${projectId}`); // already in it
      setError((err as Error).message);
      setBusy(false);
    }
  };

  const otherAccount = invitation && invitation.email !== session.user.email.toLowerCase();
  const open = invitation && invitation.state === "pending" && !invitation.expired;

  return (
    <div className="screen narrow">
      <header className="screen-head"><h1>Your invitation</h1></header>
      {invitation && <InvitationSheet invitation={invitation} />}
      {error && <p className="err" role="alert">{error}</p>}
      {invitation && !open && (
        <p className="sheet-note">This link no longer works. Ask whoever invited you for a new one. <a href="/" onClick={go("/")}>Your projects</a></p>
      )}
      {open && otherAccount && (
        <div className="callout">
          <p>The invitation is for <span className="typed">{invitation.email}</span>, and you are signed in as <span className="typed">{session.user.email}</span>.</p>
          <div className="actions">
            <button type="button" className="btn p" onClick={() => void signOut()}>Sign out, then use {invitation.email}</button>
          </div>
        </div>
      )}
      {open && !otherAccount && (
        <div className="actions">
          <button type="button" className="btn p" disabled={busy} onClick={() => void join()}>Join as {ROLE_LABEL[invitation.role].toLowerCase()}</button>
          <a className="btn" href="/" onClick={go("/")}>Not now</a>
        </div>
      )}
    </div>
  );
}
