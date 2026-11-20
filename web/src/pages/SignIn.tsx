// Signing in (Google, or an email and a password) and accepting the terms once
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { ROLE_LABEL, type Role } from "../../worker/roles";
import { ApiError, api, post } from "../api";
import { DeleteAccount, GoogleMark, InvitationSheet } from "../ui";
import type { InvitationPreview, Session } from "../types";

// The chain on the sign-in page: who brings in whom, and what each does
const CHAIN: [Role, string][] = [
  ["consultant", "opens the project, brings in the contractor and the reviewers"],
  ["contractor", "brings in the subcontractors, sends the forms on"],
  ["subcontractor", "prepares the forms for its part of the work"],
];

function Story() {
  return (
    <section className="gate-art">
      <span className="brand">RightFit<span className="brand-tag">online</span></span>
      <div className="gate-story">
        <h1>The approval forms of one project, and everyone who signs them.</h1>
        <p>Each person signs in once and sees what their role needs: the reviewers and the contractor see the whole team, and every subcontractor sees its own branch.</p>
        <ol className="chain">
          {CHAIN.map(([role, what], k) => (
            <li key={role} style={{ "--k": k } as CSSProperties}>
              <span className="lab">{ROLE_LABEL[role]}</span>
              <span className="chain-what">{what}</span>
            </li>
          ))}
        </ol>
      </div>
      <p className="gate-foot">A student project at IAAC, Barcelona, 2026–27. RightFit drafts; the person who signs decides.</p>
    </section>
  );
}

export function SignIn({ google, joinToken, onSignedIn }: { google: boolean; joinToken?: string; onSignedIn: () => void }) {
  const [invitation, setInvitation] = useState<InvitationPreview | null>(null);
  const [linkError, setLinkError] = useState("");
  const [mode, setMode] = useState<"in" | "up">("in");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!joinToken) return;
    api<InvitationPreview>(`/api/join/${joinToken}`).then(
      (found) => { setInvitation(found); setMode("up"); }, // most people who come with an invitation are new here
      (err: Error) => setLinkError(err.message),
    );
  }, [joinToken]);

  const withGoogle = async () => {
    setError("");
    try {
      const { url } = await post<{ url: string }>("/api/auth/sign-in/social", { provider: "google", callbackURL: joinToken ? `/join/${joinToken}` : "/" });
      window.location.assign(url);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const field = (name: string) => String(form.get(name) ?? "").trim();
    setBusy(true);
    setError("");
    try {
      if (mode === "in") await post("/api/auth/sign-in/email", { email: field("email"), password: String(form.get("password") ?? "") });
      else await post("/api/auth/sign-up/email", { name: field("name"), email: field("email"), password: String(form.get("password") ?? "") });
      onSignedIn();
    } catch (err) {
      const message = (err as Error).message;
      setError(err instanceof ApiError && err.status === 401 ? "That email and password don't match an account." : message);
      setBusy(false);
    }
  };

  return (
    <div className="gate">
      <Story />
      <section className="gate-work">
        <div className="gate-stack">
          {invitation && <InvitationSheet invitation={invitation} />}
          {linkError && <p className="err" role="alert">{linkError}</p>}
          <form className="sheet signin" onSubmit={(e) => void submit(e)}>
            <h2>{mode === "in" ? "Sign in" : "Create your account"}</h2>
            {invitation && <p className="sheet-note">Use <b>{invitation.email}</b>: the invitation works only for that address.</p>}
            {google && (
              <>
                <button type="button" className="btn google" onClick={() => void withGoogle()}>
                  <GoogleMark /> Continue with Google
                </button>
                <div className="or"><span>or with your email</span></div>
              </>
            )}
            {mode === "up" && (
              <label className="field">
                <span className="lab">Your name</span>
                <input name="name" type="text" autoComplete="name" required maxLength={80} />
              </label>
            )}
            <label className="field">
              <span className="lab">Email</span>
              <input name="email" type="email" autoComplete="email" required defaultValue={invitation?.email ?? ""} key={invitation?.email ?? "email"} />
            </label>
            <label className="field">
              <span className="lab">Password{mode === "up" ? ", at least 10 characters" : ""}</span>
              <input name="password" type="password" autoComplete={mode === "in" ? "current-password" : "new-password"} minLength={10} required />
            </label>
            {error && <p className="err" role="alert">{error}</p>}
            <button className="btn p wide" disabled={busy}>{mode === "in" ? "Sign in" : "Create the account"}</button>
            <p className="switch">
              {mode === "in" ? "New to RightFit? " : "Already have an account? "}
              <button type="button" className="link" onClick={() => { setMode(mode === "in" ? "up" : "in"); setError(""); }}>
                {mode === "in" ? "Create an account" : "Sign in"}
              </button>
            </p>
          </form>
          <p className="fine">After you sign in, you are asked to accept the <a href="/terms">terms</a> and the <a href="/privacy">privacy note</a>.</p>
        </div>
      </section>
    </div>
  );
}

export function TermsGate({ session, onAccepted }: { session: Session; onAccepted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [leaving, setLeaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      await post("/api/terms/accept");
      onAccepted();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <div className="gate">
      <Story />
      <section className="gate-work">
        <form className="sheet terms" onSubmit={(e) => void submit(e)}>
          <span className="lab">Before you start, {session.user.name.split(" ")[0]}</span>
          <h2>RightFit online is a student prototype.</h2>
          <ul className="points">
            <li>RightFit drafts. It never approves a form: the person who signs it answers for it.</li>
            <li>We keep your name, your email and your place in each project, and later the forms and files you add. They live on Cloudflare, with the database in Western Europe.</li>
            <li>You can delete your account at any time, and your data goes with it.</li>
          </ul>
          <label className="tick">
            <input type="checkbox" required />
            <span>I agree to the <a href="/terms" target="_blank" rel="noreferrer">terms</a> and the <a href="/privacy" target="_blank" rel="noreferrer">privacy note</a> of {session.termsVersion}.</span>
          </label>
          {error && <p className="err" role="alert">{error}</p>}
          <div className="actions">
            <button className="btn p" disabled={busy}>Continue</button>
            <button type="button" className="link" onClick={() => setLeaving(true)}>No thanks, delete my account</button>
          </div>
        </form>
      </section>
      <DeleteAccount open={leaving} onClose={() => setLeaving(false)} />
    </div>
  );
}
