// RightFit online: who is signed in, which page is open, and the rail around the pages
import { useCallback, useEffect, useState } from "react";
import { ApiError, api, go, signOut } from "./api";
import { Home } from "./pages/Home";
import { Join } from "./pages/Join";
import { Legal } from "./pages/Legal";
import { Project } from "./pages/Project";
import { SignIn, TermsGate } from "./pages/SignIn";
import { DeleteAccount } from "./ui";
import type { Session } from "./types";

type Route =
  | { page: "home" }
  | { page: "project"; id: string }
  | { page: "join"; token: string }
  | { page: "terms" | "privacy" };

function parse(path: string): Route {
  const project = path.match(/^\/p\/([\w-]+)\/?$/);
  if (project) return { page: "project", id: project[1] };
  const join = path.match(/^\/join\/([\w-]+)\/?$/);
  if (join) return { page: "join", token: join[1] };
  if (path === "/terms" || path === "/privacy") return { page: path.slice(1) as "terms" | "privacy" };
  return { page: "home" };
}

export function App() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.pathname));
  // undefined while we ask, null when nobody is signed in
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [google, setGoogle] = useState(false);
  const [projectName, setProjectName] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    const onMove = () => setRoute(parse(window.location.pathname));
    window.addEventListener("popstate", onMove);
    return () => window.removeEventListener("popstate", onMove);
  }, []);

  const load = useCallback(async () => {
    try {
      setSession(await api<Session>("/api/session"));
    } catch (err) {
      setGoogle(err instanceof ApiError && Boolean(err.data.google));
      setSession(null);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    document.title = route.page === "project" && projectName?.id === route.id ? `${projectName.name} · RightFit` : "RightFit";
  }, [route, projectName]);

  if (route.page === "terms" || route.page === "privacy") return <Legal page={route.page} signedIn={Boolean(session)} />;
  if (session === undefined) return <Splash />;
  if (session === null) return <SignIn google={google} joinToken={route.page === "join" ? route.token : undefined} onSignedIn={load} />;
  if (!session.termsAccepted) return <TermsGate session={session} onAccepted={load} />;

  return (
    <div className="app">
      <Rail session={session} route={route} project={route.page === "project" && projectName?.id === route.id ? projectName : null} />
      <main>
        {route.page === "home" && <Home session={session} />}
        {route.page === "project" && <Project id={route.id} onLoaded={setProjectName} />}
        {route.page === "join" && <Join token={route.token} session={session} />}
      </main>
    </div>
  );
}

function Splash() {
  return (
    <div className="splash" aria-busy="true">
      <span className="spinner" aria-hidden="true" />
      <span className="lab">RightFit</span>
    </div>
  );
}

function Rail({ session, route, project }: { session: Session; route: Route; project: { id: string; name: string } | null }) {
  const [leaving, setLeaving] = useState(false);
  return (
    <nav className="rail" aria-label="RightFit">
      <a className="brand" href="/" onClick={go("/")}>RightFit<span className="brand-tag">online</span></a>
      <div className="rail-links">
        <a href="/" onClick={go("/")} aria-current={route.page === "home" ? "page" : undefined}>Projects</a>
        {project && (
          <a className="rail-project" href={`/p/${project.id}`} onClick={go(`/p/${project.id}`)} aria-current="page">{project.name}</a>
        )}
      </div>
      <div className="rail-person">
        <span className="rail-sep">Signed in</span>
        <span className="rail-name">{session.user.name}</span>
        <span className="rail-mail">{session.user.email}</span>
        <div className="rail-actions">
          <button type="button" onClick={() => void signOut()}>Sign out</button>
          <button type="button" onClick={() => setLeaving(true)}>Delete my account</button>
        </div>
        <span className="rail-note">
          <a href="/terms" onClick={go("/terms")}>Terms</a> · <a href="/privacy" onClick={go("/privacy")}>Privacy</a>
        </span>
      </div>
      <DeleteAccount open={leaving} onClose={() => setLeaving(false)} />
    </nav>
  );
}
