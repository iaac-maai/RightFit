# How we plan and build RightFit

From 26 Nov 2026 to the final presentation on 17 Dec, the work is planned in GitHub issues and built one issue per working session, each session with an agent and an effort chosen for its kind of task. Nothing reaches `main` before the checks in section 6. Luca set this up on 26 Nov 2026; Sahil and Jeff join once they agree [O].

## 1. Where things live

| What | Where |
|---|---|
| What RightFit is, its principles and features | `spec/constitution/`; on scope, `roadmap.md` wins |
| The backlog | GitHub issues on `iaac-maai/RightFit` |
| Status, priority and the agent profile of each issue | The team's private GitHub Projects board |
| Decisions and scope changes | `docs/decisions.md` |

Each roadmap row carries the number of its issue, and each issue names its roadmap row (MAF-xx).

## 2. Issues

- **One issue is one task a session finishes in one sitting**: hours, not days. A roadmap feature is a parent issue and its tasks are sub-issues.
- **Every issue has four parts:** Goal, Done when, Files or area, Notes (what not to touch, open questions).
- **The repository is public.** An issue never holds client or project names, people's names, prices, package contents or anything from `data/raw/`.
- **Labels** give the kind of work (`feature`, `bug`, `research`, `data`, `docs`, `eval`) and the area (`checks`, `ingest`, `app`, `web`, `engine`, `revit`, `course`). `waiting-on-luca` marks what only Luca can do: approve a rule, confirm values, label data, answer a question. `team: to discuss` marks Sahil's and Jeff's issues until they agree to them.
- **Milestones** are the IAAC dates: 3 Dec 2026 (features and tests, comparison against the non-AI method), 10 Dec 2026 (proof of concept, limits and ethics check), 14 Dec 2026 (interface, testing in realistic conditions, narrative draft), 17 Dec 2026 (final presentation), and After the course.
- **Priority**, set on the board:

| Priority | Meaning |
|---|---|
| P0 | The next IAAC deliverable fails without it |
| P1 | Needed for the next deliverable |
| P2 | Makes the final result better |
| P3 | After the course |

## 3. The board

The board is private to the team. Its columns are Backlog, Ready, In progress, Waiting on Luca and Done. Each issue has a priority, a model, an effort and whether it may run in workflow mode (section 5).

## 4. Sessions

- **The control session** keeps the backlog. Every day it gives a short triage: what finished, what waits on Luca, what starts today and how much capacity is left. Luca says yes or no to the list.
- **One session per issue.** On Luca's yes, the control session starts a session for each Ready issue, named `#<issue> P<priority> · <short title>`. For now at most two sessions write code at the same time.
- **Each session works in its own copy** of the repository (a git worktree) on a branch `issue-<number>-<slug>`. Sessions never write in each other's copy or in the main folder.
- **The brief comes from the issue**: goal, done when, files, plus `AGENTS.md`.

## 5. Which agent for which task

| Task | Model | Effort |
|---|---|---|
| Engineering rules in `checks/`, reading the law | Opus 5.5 | max |
| A new spec, the plan of a feature, design | Opus 5.5 | xhigh |
| Evaluation, the comparison against the non-AI method | Opus 5.5 | xhigh |
| A feature with a spec and tests (`web/`, `engine/` and the like) | Opus 5.5 | high |
| A bug with the steps that show it | Opus 5.5 | high |
| The control session (backlog, triage) | Opus 5.5 | high |
| Research: laws, makers' documents | Sonnet 5.5 | high |
| Docs, READMEs, keeping the roadmap current, writing issues | Sonnet 5.5 | medium |
| Searching the code, scans, status reports | Haiku 5.5 | low |

**Workflow mode** (in Claude Code, a session that splits its task across several agents working in parallel) runs only on an issue Luca approves. It suits a large feature with a finished spec that splits into independent parts, for example `web/`, `engine/` and their tests, or an audit of the whole repository. It never runs on engineering rules in `checks/` or on anything that needs Luca's engineering judgement.

## 6. Before anything reaches `main`

1. **Tests:** `pytest`, plus `npm test` in `web/` when `web/` changed. Failing tests are never committed.
2. **The public repository scan** of the added lines: no name from the local names list, no prices, no client data, and no wording saying a tool wrote the work.
3. **A code review** (`/code-review`): medium, or high when the change touches `checks/`, sign-in, roles or project data in `web/`.
4. **Then the session merges its branch into `main`, pushes, and closes its issue** (`Closes #<issue>` in the commit message). There are no pull requests.
5. **RightFit online then updates itself** when the change touches `web/` or the code the checks engine is built from (`app/engine.py`, `app/review_core.py`, `app/booster.py`, `checks/maf/`, `checks/pumps/`). GitHub runs `npm test`, `npm run check` and the engine's build, applies the new migrations in `web/migrations/` (each runs once), deploys the engine, then the site (`.github/workflows/online.yml`). A teammate's pull request gets the same tests before it is merged. A new migration takes the next number and the same change goes into `web/schema.sql`; a migration that already ran is never edited.

Some changes wait for Luca's word before they reach `main`. These are changes to `checks/`, `data/maf/rules.csv`, `data/space/rules.csv`, the reference answers in `data/maf/reference/` and the legal documents in `web/legal/`.

Before 3, 10 and 17 Dec, Luca runs a full review (`/code-review ultra`) of everything changed since the last one.

## 7. Who decides

| Person | Decides |
|---|---|
| Luca | Priorities, what starts, rules and reference answers, anything in the list of section 6 |
| The control session | Nothing on its own: it proposes the triage, writes and closes issues, and starts sessions on Luca's yes |
| Sahil and Jeff | Their own issues, once they agree to this way of working [O] |

Changes to this file are recorded in `docs/decisions.md`.
