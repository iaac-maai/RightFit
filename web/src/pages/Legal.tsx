// The terms and the privacy note. TERMS_VERSION in worker/index.ts carries the same date: change both together.
// Written for a course project and not checked by a lawyer.
import { go } from "../api";

const VERSION = "2026-11-20";

export function Legal({ page, signedIn }: { page: "terms" | "privacy"; signedIn: boolean }) {
  return (
    <div className="legal">
      <header className="legal-bar">
        <a className="brand" href="/" onClick={go("/")}>RightFit<span className="brand-tag">online</span></a>
        <nav>
          <a href="/terms" onClick={go("/terms")} aria-current={page === "terms" ? "page" : undefined}>Terms</a>
          <a href="/privacy" onClick={go("/privacy")} aria-current={page === "privacy" ? "page" : undefined}>Privacy</a>
          <a href="/" onClick={go("/")}>{signedIn ? "Your projects" : "Sign in"}</a>
        </nav>
      </header>
      <article className="sheet legal-text">{page === "terms" ? <Terms /> : <Privacy />}</article>
    </div>
  );
}

function Terms() {
  return (
    <>
      <span className="lab">Version {VERSION}</span>
      <h1>Terms</h1>
      <p>RightFit online is a student project of the Master in AI at IAAC, Barcelona, in 2026–27. It is a prototype: it may change, stop or lose data, and it comes with no warranty. Keep your own copies of everything you share in it.</p>
      <h2>What RightFit does, and what it doesn't</h2>
      <p>RightFit drafts the review of a material approval form and says what it checked and what it couldn't. It never approves, rejects or certifies anything. The person who signs a form decides, and answers for it.</p>
      <h2>Who may use it</h2>
      <p>A consultant opens a project; everyone else comes in through an invitation from someone in it. You must be at least 16, and you use your own account only.</p>
      <h2>What you put in</h2>
      <p>Share only documents and data you are allowed to share with the parties of your project. Don't share anything unlawful, or anything that harms others.</p>
      <h2>The law</h2>
      <p>Spanish law applies to these terms.</p>
    </>
  );
}

function Privacy() {
  return (
    <>
      <span className="lab">Version {VERSION}</span>
      <h1>Privacy note</h1>
      <h2>What we keep</h2>
      <p>Your name, your email address and, if you sign in with Google, your picture there; your sessions, for 7 days at most; the projects you are in, your role and company in each, and the invitations you send and receive; the version of these terms you accepted, and when. Later, the forms and files you add to a project.</p>
      <h2>Why</h2>
      <p>To run the project space you asked for: to sign you in, show you your projects and let the people in them work together (GDPR, article 6(1)(b)), and to keep it safe (article 6(1)(f)).</p>
      <h2>Who else handles it</h2>
      <p>Cloudflare hosts the app, its database (in Western Europe) and its files. Google handles your sign-in only if you choose it. Render will run RightFit's checks on forms, and keeps nothing.</p>
      <h2>Who sees what</h2>
      <p>The people in a project see each other's name, company and email address. A subcontractor sees the reviewers, the contractor and its own branch of the project, never the other firms.</p>
      <h2>Cookies</h2>
      <p>One cookie keeps you signed in. There is no tracking and no advertising.</p>
      <h2>How long, and your rights</h2>
      <p>Until you delete your account, which you can do at any time from the rail; your data goes with it. At the end of the project we delete everything and say so here. You may ask what we hold about you, have it corrected or deleted, and complain to the Spanish data protection agency (AEPD).</p>
    </>
  );
}
