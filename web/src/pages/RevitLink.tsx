// Approving a computer with Revit (spec/features/revit_link.md, section 3): Revit shows a code and opens this page; the
// person checks the code and the computer's name, and approves or refuses. Revit never sees the password.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api, go, post } from "../api";
import { day } from "../format";

interface LinkInfo { code: string; computer: string; createdAt: string; expired: boolean; state: string }

export function RevitLink({ code: fromUrl }: { code: string }) {
  const [typed, setTyped] = useState(fromUrl);
  const [code, setCode] = useState(fromUrl.toUpperCase().replace(/[^A-Z0-9]/g, ""));
  const [info, setInfo] = useState<LinkInfo | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState<"approved" | "denied" | null>(null);
  const [locked, setLocked] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!code) return;
    setInfo(null); setError("");
    api<LinkInfo>(`/api/revit/link/${encodeURIComponent(code)}`).then(setInfo, (e: Error) => setError(e.message));
  }, [code]);

  // keep only letters and digits, so "abcd efgh" or "ABCD-EFGH" both work
  const look = (e: FormEvent) => { e.preventDefault(); setCode(typed.toUpperCase().replace(/[^A-Z0-9]/g, "")); };
  const answer = async (what: "approve" | "deny") => {
    setBusy(true); setError("");
    try {
      const r = await post<{ state: "approved" | "denied"; lockedProjects?: boolean }>(`/api/revit/link/${encodeURIComponent(code)}/${what}`);
      setDone(r.state); setLocked(Boolean(r.lockedProjects));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Try again.");
    } finally { setBusy(false); }
  };

  return (
    <div className="screen narrow">
      <section className="sheet lock">
        <span className="lab">Link Revit to RightFit online</span>
        {done === "approved" && (
          <>
            <h1 className="typed">Linked</h1>
            <p className="sheet-note">
              Go back to Revit: it finishes by itself in a few seconds. It can now get your projects' pump sets and send its checks,
              with the role you have in each project.{locked ? " It also opens the locked projects, while the team password stays the same." : ""}
            </p>
            <p className="sheet-note">You can unlink this computer at any time on a project's Fit check page.</p>
          </>
        )}
        {done === "denied" && (
          <>
            <h1 className="typed">Refused</h1>
            <p className="sheet-note">That computer is not linked. If you did not start this in your own Revit, you did the right thing.</p>
          </>
        )}
        {!done && (
          <>
            <form className="fit-code" onSubmit={look}>
              <label className="field">
                <span className="lab">The code Revit shows</span>
                <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="ABCD-EFGH" autoComplete="off" spellCheck={false} />
              </label>
              <button className="btn" disabled={!typed.trim()}>Look it up</button>
            </form>
            {error && <p className="err" role="alert">{error}</p>}
            {info && (
              <>
                <h1 className="typed">{info.code}</h1>
                <p className="sheet-note">
                  <b>{info.computer}</b> asked to link to your account on {day(info.createdAt)}. Approve only if this is the code your
                  own Revit shows right now. It will act for you, with your role in each project; it never sees your password.
                </p>
                {info.expired || info.state !== "pending" ? (
                  <p className="err" role="alert">
                    {info.expired ? "This code expired. In Revit, connect again." : `This code was already ${info.state === "denied" ? "refused" : "used"}.`}
                  </p>
                ) : (
                  <div className="actions">
                    <button type="button" className="btn p" disabled={busy} onClick={() => void answer("approve")}>Approve</button>
                    <button type="button" className="btn danger" disabled={busy} onClick={() => void answer("deny")}>Refuse</button>
                  </div>
                )}
              </>
            )}
          </>
        )}
        <p className="sheet-note"><a href="/" onClick={go("/")}>Back to your projects</a></p>
      </section>
    </div>
  );
}
