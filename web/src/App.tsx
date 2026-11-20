// RightFit online: who is signed in, which page is open, and the rail around the pages
import { useCallback, useEffect, useState } from "react";
import { ApiError, api, go, signOut } from "./api";
import { Admin, AdminProject } from "./pages/Admin";
import { Home } from "./pages/Home";
import { Join } from "./pages/Join";
import { LEGAL_PATHS, Legal, type LegalDoc } from "./pages/Legal";
import { Project } from "./pages/Project";
import { SignIn, TermsGate } from "./pages/SignIn";
import { DeleteAccount } from "./ui";
import type { Session } from "./types";

type AdminTab = "overview" | "people" | "projects" | "activity";
type Route =
  | { page: "home" }
  | { page: "project"; id: string }
  | { page: "join"; token: string }
  | { page: "admin"; tab: AdminTab }
  | { page: "admin-project"; id: string }
  | { page: "legal"; doc: LegalDoc };

function parse(path: string): Route {
  const clean = path.replace(/\/+$/, "") || "/";
  const project = clean.match(/^\/p\/([\w-]+)$/);
  if (project) return { page: "project", id: project[1] };
  const join = clean.match(/^\/join\/([\w-]+)$/);
  if (join) return { page: "join", token: join[1] };
  const adminProject = clean.match(/^\/admin\/p\/([\w-]+)$/);
  if (adminProject) return { page: "admin-project", id: adminProject[1] };
  const admin = clean.match(/^\/admin(?:\/(people|projects|activity))?$/);
  if (admin) return { page: "admin", tab: (admin[1] as AdminTab | undefined) ?? "overview" };
  const doc = (Object.keys(LEGAL_PATHS) as LegalDoc[]).find((d) => LEGAL_PATHS[d] === clean);
  if (doc) return { page: "legal", doc };
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

  const openProject = (route.page === "project" || route.page === "admin-project") && projectName?.id === route.id ? projectName : null;
  useEffect(() => {
    document.title = openProject ? `${openProject.name} · RightFit` : route.page === "admin" ? "Management · RightFit" : "RightFit";
  }, [route, openProject]);

  if (route.page === "legal") return <Legal doc={route.doc} signedIn={Boolean(session)} />;
  if (session === undefined) return <Splash />;
  if (session === null) return <SignIn google={google} joinToken={route.page === "join" ? route.token : undefined} onSignedIn={load} />;
  if (!session.termsAccepted) return <TermsGate session={session} onAccepted={load} />;

  const adminPage = route.page === "admin" || route.page === "admin-project";
  return (
    <div className="app">
      <Rail session={session} route={route} project={openProject} />
      <main>
        {route.page === "home" && <Home session={session} />}
        {route.page === "project" && <Project id={route.id} onLoaded={setProjectName} />}
        {route.page === "join" && <Join token={route.token} session={session} />}
        {adminPage && !session.admin && (
          <div className="screen"><p className="err" role="alert">This page is for the people who run RightFit.</p></div>
        )}
        {route.page === "admin" && session.admin && <Admin tab={route.tab} />}
        {route.page === "admin-project" && session.admin && <AdminProject id={route.id} onLoaded={setProjectName} />}
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
  const inAdmin = route.page === "admin" || route.page === "admin-project";
  return (
    <nav className="rail" aria-label="RightFit">
      <a className="brand" href="/" onClick={go("/")}>RightFit<span className="brand-tag">online</span></a>
      <div className="rail-links">
        <a href="/" onClick={go("/")} aria-current={route.page === "home" ? "page" : undefined}>Projects</a>
        {project && route.page === "project" && (
          <a className="rail-project" href={`/p/${project.id}`} onClick={go(`/p/${project.id}`)} aria-current="page">{project.name}</a>
        )}
        {session.admin && (
          <>
            <span className="rail-sep">RightFit's team</span>
            <a href="/admin" onClick={go("/admin")} aria-current={route.page === "admin" ? "page" : undefined}>Management</a>
            {project && route.page === "admin-project" && (
              <a className="rail-project" href={`/admin/p/${project.id}`} onClick={go(`/admin/p/${project.id}`)} aria-current="page">{project.name}</a>
            )}
          </>
        )}
      </div>
      <div className="rail-person">
        <span className="rail-sep">Signed in{inAdmin ? ", in Management" : ""}</span>
        <span className="rail-name">{session.user.name}</span>
        <span className="rail-mail">{session.user.email}</span>
        <div className="rail-actions">
          <button type="button" onClick={() => void signOut()}>Sign out</button>
          <button type="button" onClick={() => setLeaving(true)}>Delete my account</button>
        </div>
        <span className="rail-note">
          <a href={LEGAL_PATHS.terms} onClick={go(LEGAL_PATHS.terms)}>Terms</a> · <a href={LEGAL_PATHS.privacy} onClick={go(LEGAL_PATHS.privacy)}>Privacy</a> · <a href={LEGAL_PATHS.cookies} onClick={go(LEGAL_PATHS.cookies)}>Cookies</a>
        </span>
      </div>
      <DeleteAccount open={leaving} onClose={() => setLeaving(false)} />
    </nav>
  );
}
