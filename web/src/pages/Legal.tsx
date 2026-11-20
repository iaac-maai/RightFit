// The legal documents, written in web/legal/*.md and shown here. Their versions are the dates in worker/index.ts
// (TERMS_VERSION, DPA_VERSION): a new version of the terms or the agreement asks everyone to accept it again.
import cookies from "../../legal/cookies.md?raw";
import dpa from "../../legal/data-processing.md?raw";
import notice from "../../legal/legal-notice.md?raw";
import privacy from "../../legal/privacy.md?raw";
import terms from "../../legal/terms.md?raw";
import { go } from "../api";
import { Markdown } from "../markdown";

export type LegalDoc = "terms" | "privacy" | "cookies" | "dpa" | "notice";

export const LEGAL_PATHS: Record<LegalDoc, string> = {
  terms: "/terms", privacy: "/privacy", cookies: "/cookies", dpa: "/data-processing", notice: "/legal-notice",
};
const TITLES: Record<LegalDoc, string> = {
  terms: "Terms", privacy: "Privacy", cookies: "Cookies", dpa: "Data processing", notice: "Legal notice",
};
const SOURCES: Record<LegalDoc, string> = { terms, privacy, cookies, dpa, notice };

// Who runs RightFit online, in one place. Until it is filled in, the documents say what is still missing.
export const OPERATOR = {
  name: "[the operator's full legal name, to be completed]",
  address: "[the operator's postal address, to be completed]",
  email: "[the operator's contact email address, to be completed]",
  taxId: "[the operator's tax identification number, to be completed]",
};

const fill = (text: string) =>
  text.replace(/\{\{operator\.(name|address|email|taxId)\}\}/g, (_, field: keyof typeof OPERATOR) => OPERATOR[field]);

export function Legal({ doc, signedIn }: { doc: LegalDoc; signedIn: boolean }) {
  return (
    <div className="legal">
      <header className="legal-bar">
        <a className="brand" href="/" onClick={go("/")}>RightFit<span className="brand-tag">online</span></a>
        <nav aria-label="Legal documents">
          {(Object.keys(LEGAL_PATHS) as LegalDoc[]).map((d) => (
            <a key={d} href={LEGAL_PATHS[d]} onClick={go(LEGAL_PATHS[d])} aria-current={doc === d ? "page" : undefined}>{TITLES[d]}</a>
          ))}
          <a href="/" onClick={go("/")}>{signedIn ? "Your projects" : "Sign in"}</a>
        </nav>
      </header>
      <article className="sheet legal-text"><Markdown source={fill(SOURCES[doc])} /></article>
    </div>
  );
}
