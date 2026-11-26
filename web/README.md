# web: RightFit online

The project space where the parties of one project meet: the consultant opens the project and invites the contractor and the other reviewers, the contractor its subcontractors. Everyone signs in with Google or with an email and a password, and sees what their role in that project lets them see. The spec is `spec/features/rightfit_online.md`; the review app on the laptop (`app/`) stays the reviewer's tool.

It is built like the app of the AI Methods hackathon: one Cloudflare Worker serves the React page and answers `/api/...`, Better Auth keeps the accounts, and D1 keeps the data.

| File | What it does |
|---|---|
| `worker/roles.ts` | who may invite whom, who sees whom, and who opens Management; the page and the Worker both use it |
| `worker/roles.test.ts`, `worker/admin.test.ts` | the tests for those rules (`npm test`) |
| `worker/admin.ts` | Management: every account and project, the activity log, and the changes the team that runs RightFit may make |
| `worker/data.ts` | what the routes share: answers, the activity log, deleting an account |
| `worker/index.ts` | the API: every request checked for an account, the terms, membership and role |
| `worker/auth.ts` | sign-in with Better Auth: email and password, or Google |
| `schema.sql` | the D1 tables: accounts, consent, projects (with the data processing agreement accepted), members, invitations, the activity log |
| `legal/` | the Terms of Service, Privacy Policy, Data Processing Agreement, Cookie Policy and Legal Notice the app shows; `docs/legal/` has the operator's own records |
| `worker/project_data.ts`, `worker/team.ts` | a project's own data (packages, files, RightFit's draft reviews, the rules, BOQ lines) and the team password that opens a locked project |
| `src/pages/Inside.tsx` | Inside RightFit, in Management: how a package goes through RightFit with its own numbers, the tools, and the knowledge graph drawn; a project opens only for an admin who is a member of it |
| `src/pages/Products.tsx`, `worker/products.ts` | Product lines, for the consultant's people: the products that come back, with their forms, answers, documents and the BOQ lines they cover, from this project and the consultant's other projects that accepted the agreement of 26 Nov 2026; `worker/products.test.ts` tests putting the projects together |
| `worker/revit.ts`, `worker/revit_link.ts` | the Revit link (`spec/features/revit_link.md`): a computer with Revit linked by a code approved on the site, the project's pump sets for Revit, the checks Revit sends, the chosen set; `worker/revit_link.test.ts` tests its rules |
| `worker/survey.ts`, `worker/survey_rules.ts`, `src/pages/Survey.tsx` | the practice survey (`spec/features/survey.md`): the public page `/survey`, its checks, and the results at `/survey/results`; `worker/survey_rules.test.ts` tests it |
| `migrations/0006_revit_command.sql` | Preview in Revit: a message from the Fit check page for the person's own linked Revit (`spec/features/revit_link.md` §9) |
| `src/pages/FitCheck.tsx`, `src/pages/RevitLink.tsx` | the project's Fit check page, and the page that approves a computer with Revit (`/revit?code=...`) |
| `worker/upload.ts` | a package added on the site: its files into the private bucket, one at a time; the package waits to be read |
| `worker/review_edit.ts` | a review changed online: ticks on readings, decisions on findings and AI suggestions, the review dates, the consultant's rules; each change goes to the engine; and the booster sizing |
| `engine/` | the checks engine: a Python Worker with no address of its own that runs the laptop's review code (`app/engine.py`); `build.py` copies that code in before Wrangler bundles it |
| `scripts/import_project.py` | puts the project the review app has open online: files in the private bucket, rows in D1, the BOQ without prices; an import again keeps what was confirmed or decided online, unless `--replace-online-work`; with the files or `--pages` it also draws every page of the read packages for the marks |
| `worker/reuse.ts` | The same file in another package (MAF-36b): readings a person confirmed on a file with the same fingerprint, offered on the Readings step for a reviewer to confirm; `worker/reuse.test.ts` tests it |
| `worker/register.ts` | The BOQ register (MAF-36c): where each BOQ line stands, from the knowledge graph, the read packages' BOQ matches and the answers recorded on packages; shown on the BOQ page; `worker/register.test.ts` tests it |
| `migrations/` | changes for a database made before them; a new database gets everything from `schema.sql` |
| `src/` | the page: sign-in, the terms, the projects, a project's team and the invitations, a package's review in three steps with its pages and their marks (`src/review.ts` arranges it, with its tests), the rules and booster sizing (`src/chart.tsx` draws the curves) |
| `wrangler.jsonc` | the Worker and its database on Cloudflare |

## On the laptop

The installed packages go to `node_modules.nosync`, which iCloud leaves alone, behind a `node_modules` link:

```bash
mkdir -p node_modules.nosync && ln -sfn node_modules.nosync node_modules
npm install
cp .dev.vars.example .dev.vars   # then put a long random string in BETTER_AUTH_SECRET
npm run db:local
npm run dev
```

The page opens at the address Vite prints. Google sign-in shows only when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.dev.vars`; Management opens only for the addresses in `ADMIN_EMAILS`, signed in with Google. `npm test` runs the rules' tests, and `npm run check` the TypeScript check. On the laptop too, a change to a review is checked by the engine on Cloudflare (`remote` in `wrangler.jsonc`): the checks need nothing of the laptop's.

## Online (Luca's Cloudflare account)

Live since 20 Nov 2026 at https://rightfit.hackathon-team6-cubicasa-app.workers.dev, with the database `rightfit-db` in Western Europe. The secrets `BETTER_AUTH_SECRET` and `ADMIN_EMAILS` are set; `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` wait for the Google client. The steps, for a new account or a new database:

```bash
npx wrangler d1 create rightfit-db --location weur   # put the id it prints in wrangler.jsonc
npm run db:remote
npx wrangler secret put BETTER_AUTH_SECRET
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put ADMIN_EMAILS   # the Google addresses that open Management, separated by commas
npx wrangler secret put TEAM_PASSWORD  # opens a locked project's data, besides the account
npx wrangler r2 bucket create rightfit-files --location weur
# a database made before 26 Nov 2026 also needs the Revit link's tables, once:
# npx wrangler d1 execute rightfit-db --remote --file=migrations/0003_revit_link.sql
# and, for Preview in Revit (26 Nov 2026), once:
# npx wrangler d1 execute rightfit-db --remote --file=migrations/0006_revit_command.sql
# and, for the practice survey (26 Nov 2026), once:
# npx wrangler d1 execute rightfit-db --remote --file=migrations/0007_survey.sql
(cd engine && npx wrangler deploy -c wrangler.jsonc)   # the checks engine first: the site's Worker calls it by name
npm run deploy
# the project the review app has open, with its packages, files, reviews and BOQ lines (no prices):
# python3 web/scripts/import_project.py --owner <the consultant's Google address> --remote
```

Google needs an OAuth client of type Web application, with the redirect address `https://<the Worker's address>/api/auth/callback/google`. Secrets are typed in the terminal and never written in a file that Git sees.
