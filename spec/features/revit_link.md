# Feature spec: the Revit link (MAF-37)

Status: built by Jeff on 26 Nov 2026. To agree with Sahil and Luca (see docs/decisions.md). The fit check's rules and the IS015 values were approved by Luca the same day.

## 1. What it does
The fit check in Revit (`spec/features/revit_fit_check.md`) and RightFit online (`spec/features/rightfit_online.md`) work on the same project but did not know about each other: the pump sets lived in a file on one computer, and what the check found stayed in Revit. The Revit link joins them.

- Revit gets the project's fit check data from the site: the pump sets with their status, the service space, the circuit. When Luca confirms a value, every linked Revit has it; nobody passes files around.
- Revit sends each check back: the room, the set, the verdict, every result with its rule, a picture of the RightFit 3D view, who ran it and when.
- The site shows the checks on the project's **Fit check** page, and the reviewers mark the set they choose; Revit shows that choice in its report.

Not in this feature: the makers' families (.rfa, .dwg, saved shapes) stay in the project folder on the computer that runs Revit; reading the Revit model on the site; checks run on the site. Those are later features.

## 2. Why not GitHub
The instructor suggested linking through GitHub. The repository is public, so project data can never go there; every check would be a commit; every reviewer would need git. GitHub keeps its own job: installing and updating the add-in (pyRevit installs an extension from its GitHub address). The data goes through the site, which already has the accounts, the roles, the locked projects and the private storage.

## 3. How a computer is linked (device sign-in)
Revit never sees a password. It is the same idea as signing in to a television:

1. In Revit, RightFit › Online › Connect asks the site for a link. The site answers with a short code (`ABCD-EFGH`, 8 letters and digits that can't be mixed up), a long secret only Revit keeps, and the address of the approval page. The link lasts 10 minutes.
2. Revit opens the approval page in the browser and shows the code. The person signs in to the site as usual, checks the code and the computer's name, and approves (or refuses).
3. Revit asks again with its secret, gets a token once, and keeps it in `%APPDATA%\RightFit\online.json`, outside the repository. The site keeps only the SHA-256 of the secret and of the token, as it does for invitations.
4. The token acts for that person, with their role in each project, nothing more. A locked project opens for the token only if the browser that approved it had the team password; changing the team password closes it again.
5. The site lists a person's linked computers on the Fit check page; unlinking one stops its token at once. Deleting the account deletes its links.

## 4. What travels

### Revit asks the site (token)
| Request | Answer | Who |
|---|---|---|
| `GET /api/revit/me` | the person and the projects whose forms they see | anyone linked |
| `GET /api/revit/projects/<id>/fitcheck` | the project's pump sets (`candidates.json`), its fit check settings (`project.json`) and the set the reviewers chose | members who see the forms |
| `POST /api/revit/projects/<id>/fitcheck/data` | stores `candidates.json` and `project.json` sent from the project folder | consultant and designer |
| `POST /api/revit/projects/<id>/runs` | stores one check | members who see the forms |

### A check, as Revit sends it
`action` (check, preview or swap), the set (id, maker, model, submitted), the room (name, length, width, height, area, doors, things in it), the verdict and whether it is confirmed, each result (check, result, would be, finding, rules with their status), the candidates' table for a Check Pump, the Revit file's name, the time on the computer, and an optional PNG of the RightFit 3D view (at most 2 MB). The site checks the shape and sizes of what it stores; values are the add-in's, built from the model and the project's data, and the site never changes them.

### The site's page (session, as every other page)
| Request | What |
|---|---|
| `GET /api/projects/<id>/fitcheck` | the sets online with their status, the latest 50 checks, the chosen set, whether this person may choose |
| `GET /api/projects/<id>/fitcheck/runs/<run>` and `.../<run>.png` | one check in full, and its picture |
| `POST /api/projects/<id>/fitcheck/choose` | a reviewer marks the chosen set (or clears it), with a note |
| `GET /api/revit/links`, `POST /api/revit/links/<id>/unlink` | the person's linked computers |
| `GET /api/revit/link/<code>`, `POST .../approve`, `POST .../deny` | the approval page |

## 5. Where it is kept
D1: `revit_link` (the 10-minute links), `revit_token` (one per linked computer, hashes only), `fit_run` (one row per check: who, when, which set, the verdict, a short summary), `fit_choice` (the chosen set of each project). R2, private: `projects/<id>/fitcheck/data.json` and `projects/<id>/fitcheck/runs/<run>.json` and `.png`. Everything goes in the activity log (`revit.linked`, `revit.unlinked`, `fitcheck.data_sent`, `fitcheck.run`, `fitcheck.chosen`).

## 6. In Revit
- A new Setup button, **Online**: Connect this computer, Link this project (pick the online project for the open project folder), Send project data, Get project data, Send waiting checks, Disconnect.
- Check Pump gets the project data from the site first when the project is linked (falls back to the last copy, then the project folder), and every Check Pump, Next Option and Swap sends its check. The report says "Sent to RightFit online" or "Kept on this computer, sent with the next check" when the site can't be reached. Waiting checks sit in `%APPDATA%\RightFit\outbox\`.
- The report shows the set the reviewers chose, and who chose it.
- HTTP through .NET (`System.Net`), as pyRevit's Python 2.7 has it; no new dependency.

## 7. Constitution
Unchanged: the checks stay in Revit and in `checks/space/`, deterministic, with no AI; a value keeps its source and status, and the site shows them; the chosen set is a person's decision, labelled with who and when; no project data in Git; every change is logged. New: the token is a second way into a person's account, so it is hashed, limited to what the person may already do, listed and revocable.

## 8. Tests
`web/worker/revit_link.test.ts`: codes, tokens, the bearer header, who may send data, runs and choose, what a run may hold. `tests/test_revit_online.py`: the check the add-in sends, the outbox, the project link in the settings.

## 9. From the site to Revit (MAF-37b)
Built by Jeff on 26 Nov 2026. A person on the Fit check page clicks **Preview in Revit** next to a pump set, and their own Revit, open and linked, shows that set in the pump's place within a few seconds, as Next Option does, and sends that check back to the page.

How the message travels: the site keeps it, and Revit picks it up. While a linked project folder is open, the add-in asks the site every 4 seconds, from a background thread, whether a message waits for its person; the site gives it once, to one of that person's linked computers, and Revit runs it through Revit's external event, the only safe way into the model from outside a button. Revit answers whether it worked, and the page shows the answer.

Why this and not a server inside Revit: pyRevit's Routes server listens on the whole network, not only on the computer, and does not pass the calling page's address to the add-in, and the browsers now ask the person before a site reaches their computer. The site already knows the person and their linked computers, so a message through it reaches only their own Revit, from any device (a phone, a Mac in the studio), with no new permission.

- A message is for its person's own linked computers only; another member's click never moves someone else's Revit.
- It waits 2 minutes; after that it expires, and the page says Revit did not answer (closed, not linked, or no project folder linked).
- Revit does only what Next Option does: a preview, drawn by RightFit and cleared by Clear, never a change to the project's own elements. It runs only on the online project linked to the open project folder, and only when the pump set was picked with Check Pump (or there is one pump set in the model).
- D1: `revit_command` (`web/migrations/0006_revit_command.sql`). Requests: `POST /api/projects/<id>/fitcheck/revit {setId}` and `GET /api/projects/<id>/fitcheck/revit/<message>` on the page; `GET /api/revit/commands` and `POST /api/revit/commands/<message>` with the token.
- Tests: `web/worker/revit_link.test.ts` (when a message expires, what it may ask), `tests/test_revit_online.py` (how Revit reads a message).
