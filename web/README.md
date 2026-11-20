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
| `src/` | the page: sign-in, the terms, the projects, a project's team and the invitations |
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

The page opens at the address Vite prints. Google sign-in shows only when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.dev.vars`; Management opens only for the addresses in `ADMIN_EMAILS`, signed in with Google. `npm test` runs the rules' tests, and `npm run check` the TypeScript check.

## Online (Luca's Cloudflare account)

```bash
npx wrangler d1 create rightfit-db --location weur   # put the id it prints in wrangler.jsonc
npm run db:remote
npx wrangler secret put BETTER_AUTH_SECRET
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put ADMIN_EMAILS   # the Google addresses that open Management, separated by commas
npm run deploy
```

Google needs an OAuth client of type Web application, with the redirect address `https://<the Worker's address>/api/auth/callback/google`. Secrets are typed in the terminal and never written in a file that Git sees.
