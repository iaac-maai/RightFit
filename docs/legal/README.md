# docs/legal: the legal file of RightFit online

Drafted on 20 Nov 2026 for RightFit online (`web/`, `spec/features/rightfit_online.md`). The documents users read live in `web/legal/` and are shown by the app; the ones kept here are the operator's own records, which the GDPR asks for but users don't read.

**Status:** drafts, not yet reviewed by a lawyer. Before real users outside the team sign up, a lawyer qualified in Spanish and EU data protection law should review them, and the operator's details must be filled in (below).

## What users read (`web/legal/`, shown at the paths in brackets)

| Document | What it does | Law it answers |
|---|---|---|
| `terms.md` (`/terms`) | the contract between the operator and each user: accounts, roles and invitations, what RightFit does and does not do, content, acceptable use, liability, law | Spanish Civil Code, Royal Legislative Decree 1/2007 (consumers), Regulation (EU) No 1215/2012 (jurisdiction) |
| `privacy.md` (`/privacy`) | what personal data is processed, why, on what basis, with whom, for how long, and the users' rights | GDPR Articles 12 to 14, LOPDGDD |
| `data-processing.md` (`/data-processing`) | the agreement between the organisation that opens a project (controller) and the operator (processor), with its three annexes | GDPR Article 28 |
| `cookies.md` (`/cookies`) | the cookies used; only strictly necessary ones, so no banner | LSSI-CE Article 22.2, Directive 2002/58/EC Article 5(3) |
| `legal-notice.md` (`/legal-notice`) | who operates the service | LSSI-CE Article 10 |

Every user accepts the terms (having read the privacy policy) at first sign-in; a consultant accepts the data processing agreement for their organisation when opening a project. The Worker records the version and the date (`TERMS_VERSION` and `DPA_VERSION` in `web/worker/index.ts`). A new version of the terms asks everyone to accept it again.

## The operator's own records (here)

| Document | Why |
|---|---|
| `records_of_processing.md` | the records of processing activities, as controller and as processor (GDPR Article 30) |
| `breach_procedure.md` | what to do in the first 72 hours after a personal data breach (GDPR Articles 33 and 34) |
| `dpia_screening.md` | why a data protection impact assessment is not required for now, and what would change that (GDPR Article 35) |

## Before going live

1. Decide who operates the service (Luca, the team, or IAAC with its agreement; the IAAC terms say commercial use needs IAAC's written agreement) and fill in `OPERATOR` in `web/src/pages/Legal.tsx`: legal name, postal address, contact email, tax number. Until then the documents say what is missing.
2. Have the five documents reviewed by a lawyer.
3. Accept the data processing terms of Cloudflare and Render in their dashboards, and keep a copy.
4. Change the version date in the documents and in `web/worker/index.ts` whenever a document changes in substance.
