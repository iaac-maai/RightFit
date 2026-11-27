# Feature spec: the practice survey (MAF-38)

Status: built by Jeff on 26 Nov 2026, after Rasha (instructor) suggested showing how much time and money the tool saves. To agree with Sahil and Luca (see docs/decisions.md). Its questions were revised with Luca on 27 Nov 2026, before it went online (version 2026-11-27).

## 1. Why
To say what RightFit saves, we need to know how the work goes today without it. The team measures its own time with and without RightFit on real forms (the comparison for 3 Dec); the survey asks people who prepare and review material approval forms for a living how long a review takes them, how often forms come back, what a return delays, and what equipment that does not fit costs on site. The site shows both, each labelled with where it comes from: "as reported by N people" for the survey, "measured by the team" for the comparison. A survey answer is a person's own estimate and is never shown as a measurement (constitution, mission.md §5: never invent data; predictions are not warnings).

## 2. Who answers, and what is kept
- Anyone with the link, without an account: https://rightfit.hackathon-team6-cubicasa-app.workers.dev/survey . About 3 minutes, up to 16 questions (some follow from an earlier answer), in English.
- Anonymous: no name, email, company, IP address or browser data is stored. The answer row keeps the day it was sent (not the time), the survey's version and the answers.
- The free-text question asks not to name people or companies; its answers are shown only to the people who run RightFit (admins), in case someone does.
- Consent is a required tick: 18 or older, answers used for RightFit, a student project at IAAC.
- Spam: the page only takes answers sent from RightFit's own page, has a hidden field that robots fill in, and a browser remembers it answered. No count of answers per person is possible without storing something about them, so a few duplicates are accepted and said in the results.

## 3. The questions (version 2026-11-27)
1. Your role (one): MEP engineer who reviews submittals; MEP designer; architect; main contractor; subcontractor or supplier; client or project manager; other.
2. Where you mostly work (one): Spain, Romania, Lebanon, France, Italy, United Kingdom, elsewhere in Europe, Middle East, elsewhere.
3. Years in the industry (one): under 2, 2 to 5, 5 to 10, over 10.
4. With material approval forms (submittals) you (one): review them, prepare them, both, neither.
5. Equipment submittals reviewed or prepared in a typical month (one, unless "neither"): 1 to 5, 6 to 15, 16 to 40, over 40, don't know.
6. Your own working time to review one equipment submittal, such as a pump set, not the days it waits (one, for those who review): under 15 min, 15 to 30 min, 30 to 60 min, 1 to 2 h, 2 to 4 h, over 4 h, don't know.
7. Your own working time to prepare one (one, for those who prepare): under 30 min, 30 to 60 min, 1 to 2 h, 2 to 4 h, half a day to a day, over a day, don't know.
8. At the first submission, out of 10 submittals, how many get C, revise and resubmit (0 to 10, optional).
9. Rounds a submittal usually needs until it is approved (one): 1, 2, 3, 4 or more, don't know.
10. When one is returned, how long it usually delays the item (one): under 3 days, 3 to 7 days, 1 to 2 weeks, 2 to 4 weeks, over a month, don't know.
11. The most common reasons for a return (up to 3): missing documents or certificates; expired or wrong certificate or declaration; a data sheet for a range, not the exact model; data does not meet the specification; wrong size or does not fit the space; does not meet the code; clashes with other approved items or trades; wrong model or variant; not the brand or model the client or design asked for; other.
12. In the last 3 projects, approved equipment that did not fit once on site, for space, access or connections (one): never, once, a few times, often, not applicable.
13. If it happened, roughly what fixing one case cost (one): under €1,000; €1,000 to 5,000; €5,000 to 20,000; €20,000 to 100,000; over €100,000; don't know.
14. How useful it would be to have a submittal's documents and data checked before review (1 not useful to 5 very useful).
15. How useful it would be to see, before approval, whether the equipment fits in the building model (1 to 5).
16. Anything else (free text, 500 characters at most, optional).

The introduction says what the survey asks about and does not describe the tool, so that the two usefulness questions are not answered out of courtesy.

## 4. Results
**Live results, at the top of `/survey`, for everyone who opens it** (since 27 Nov 2026). The page asks `GET /api/survey/live` again every 5 seconds while it is on screen, and at once after a person sends, so a new answer shows within seconds. It shows sums only, never a comment or one person's answers. First, large, the two headline numbers:
- **Time lost per submittal**, in days: for each person who answered both, the extra rounds (rounds until approval minus the first) times the delay each return causes; the average, the lowest and the highest, and how many answered. "4 or more" rounds or "over a month" make it "at least".
- **Money lost per misfit on site**: the average cost of fixing one case of approved equipment that did not fit once on site, with the lowest and highest range chosen.
Then, smaller:
- for the ranges (own time to review one submittal, own time to prepare one, rounds until approval, delay per return, cost of fixing one misfit): the average, the lowest and the highest range chosen, and how many answered. The average counts each range at its middle; an open range ("Over 4 hours", "4 or more", "Over €100,000") counts at its lower bound and makes the average "at least"; "Don't know" counts nowhere. The middles are in `MIDDLES` in `web/worker/survey_rules.ts`; they only turn people's ranges into one number;
- C at the first submission: the average, lowest and highest out of 10;
- how many of those it applies to saw approved equipment not fit on site in their last 3 projects;
- the two usefulness scores, as an average out of 5;
- the three most common reasons, and who answered, by role.
The panel says these are people's own estimates, not measurements, and how the averages are worked out. It shows what today's work costs as people report it, not what RightFit saves: the survey asks no one what a tool would save, and the panel never says "saved". Showing the results before a person answers can sway their answers; the team chose to show them anyway (docs/decisions.md, 27 Nov 2026).

**The answers are dropdowns**: one dropdown per question; the reasons (up to 3) open as a dropdown list with ticks.

`/survey/results`, for anyone signed in to RightFit: how many answered, and for each question the count of each answer and its share; for the number of C answers out of 10 the median and the middle half. The comments and a CSV of every answer are for admins only. Each result says "as reported by N people, from <first day> to <last day>", and that answers are estimates.

## 5. Where it is kept
D1: `survey_response` (`web/migrations/0007_survey.sql`): id, the day, the version, the answers as JSON. The questions live in one place, `web/worker/survey_rules.ts`, which checks every answer and sums the results; the page asks the site for them.

## 6. Tests
`web/worker/survey_rules.test.ts`: an answer outside the options is refused, consent is required, the comment is cut to 500 characters, the robot field refuses, the sums and the median are right.
