// Pieces several pages share: the dialog, a person's monogram, the invitation as a form, and the icons
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ROLE_LABEL, ROLE_NOTE } from "../worker/roles";
import { post } from "./api";
import { initials } from "./format";
import type { InvitationPreview } from "./types";

// A dialog over the page; Escape or the cross closes it
export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog ref={ref} className="modal" aria-labelledby={titleId} onCancel={(e) => { e.preventDefault(); onClose(); }}>
      <div className="modal-head">
        <h2 id={titleId}>{title}</h2>
        <button type="button" className="x" onClick={onClose} aria-label="Close">
          <Icon d="M5 5l10 10M15 5L5 15" />
        </button>
      </div>
      {open && children}
    </dialog>
  );
}

export function Monogram({ name, image, pending }: { name: string; image?: string | null; pending?: boolean }) {
  if (image && !pending) return <img className="mono" src={image} alt="" referrerPolicy="no-referrer" />;
  return <span className={`mono${pending ? " pending" : ""}`} aria-hidden="true">{pending ? "@" : initials(name)}</span>;
}

// 16 px line drawings on a 20-unit grid, as in the review app
export function Icon({ d }: { d: string }) {
  return (
    <svg className="i" viewBox="0 0 20 20" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}
export const PLUS = "M10 4v12M4 10h12";
export const ARROW = "M7 4l6 6-6 6";

export function GoogleMark() {
  return (
    <svg className="g" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.2l7.9 6.2C12.5 13.6 17.8 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.8c4.3-4 6.9-9.9 6.9-17.2z" />
      <path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.2C1 16.6 0 20.2 0 24s1 7.4 2.7 10.8l7.9-6.2z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.8c-2.1 1.4-4.8 2.3-8.5 2.3-6.2 0-11.5-4.1-13.4-9.8l-7.9 6.2C6.6 42.6 14.6 48 24 48z" />
    </svg>
  );
}

// The invitation drawn as the head of a form: printed labels, typed values
export function InvitationSheet({ invitation }: { invitation: InvitationPreview }) {
  const from = [invitation.invitedBy, invitation.inviterCompany].filter(Boolean).join(", ");
  const state = invitation.state !== "pending" ? invitation.state : invitation.expired ? "expired" : "";
  return (
    <section className="sheet invitation" aria-label="Your invitation">
      <div className="sheet-head">
        <span className="lab">Invitation to a RightFit project</span>
        {state && <span className="chip off">{state}</span>}
      </div>
      <dl className="form-fields">
        <div className="fld"><dt className="lab">Project</dt><dd className="typed">{invitation.project}</dd></div>
        <div className="fld"><dt className="lab">Your role</dt><dd className="typed">{ROLE_LABEL[invitation.role]}</dd></div>
        {from && <div className="fld"><dt className="lab">From</dt><dd className="typed">{from}</dd></div>}
        <div className="fld"><dt className="lab">For</dt><dd className="typed">{invitation.email}</dd></div>
      </dl>
      <p className="sheet-note">{ROLE_NOTE[invitation.role]}</p>
    </section>
  );
}

// Deleting the account, from the rail or from the terms
export function DeleteAccount({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const remove = async () => {
    setBusy(true);
    setError("");
    try {
      await post("/api/account/delete");
      window.location.assign("/");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="Delete your account?">
      <p>Your account goes, with your sessions, your sign-in links and your place in every project. A project with nobody else in it goes too. This can't be undone.</p>
      {error && <p className="err" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="btn danger" onClick={() => void remove()} disabled={busy}>Delete my account</button>
        <button type="button" className="btn" onClick={onClose}>Keep it</button>
      </div>
    </Modal>
  );
}
