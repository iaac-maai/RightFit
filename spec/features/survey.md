# Feature spec: the practice survey (MAF-38)

Status: built by Jeff on 26 Nov 2026, after Rasha (instructor) suggested showing how much time and money the tool saves. To agree with Sahil and Luca (see docs/decisions.md).

## 1. Why
To say what RightFit saves, we need to know how the work goes today without it. The team measures its own time with and without RightFit on real forms (the comparison for 3 Dec); the survey asks people who prepare and review material approval forms for a living how long a review takes them, how often forms come back, what a return delays, and what equipment that does not fit costs on site. The site shows both, each labelled with where it comes from: "as reported by N people" for the survey, "measured by the team" for the comparison. A survey answer is a person's own estimate and is never shown as a measurement (constitution, mission.md §5: never invent data; predictions are not warnings).

## 2. Who answers, and what is kept
- Anyone with the link, without an account: https://rightfit.hackathon-team6-cubicasa-app.workers.dev/survey . About 3 minutes, 12 questions, in English.
- Anonymous: no name, email, company, IP address or browser data is stored. The answer row keeps the day it was sent (not the time), the survey's version and the answers.
- The free-text question asks not to name people or companies; its answers are shown only to the people who run RightFit (admins), in case someone does.
- Consent is a required tick: 18 or older, answers used for RightFit, a student project at IAAC.
- Spam: the page only takes answers sent from RightFit's own page, has a hidden field that robots fill in, and a browser remembers it answered. No count of answers per person is possible without storing something about them, so a few duplicates are accepted and said in the results.

## 3. The questions (version 2026-11-26)
1. Your role (one): MEP engineer who reviews submittals; MEP designer; architect; main contractor; subcontractor or supplier; client or project manager; other.
2. Where you mostly work (one): Spain, Romania, Lebanon, France, Italy, United Kingdom, elsewhere in Europe, Middle East, elsewhere.
3. Years in the industry (one): under 2, 2 to 5, 5 to 10, over 10.
4. With material approval forms (submittals) you (one): review them, prepare them, both, neither.
5. Time to review one equipment submittal, such as a pump set, from opening it to the answer (one): under 15 min, 15 to 30 min, 30 to 60 min, 1 to 2 h, 2 to 4 h, over 4 h, don't know.
6. Out of 10 submittals, how many are returned for corrections or resubmission (0 to 10, optional).
7. When one is returned, how long it usually delays the item (one): under 3 days, 3 to 7 days, 1 to 2 weeks, 2 to 4 weeks, over a month, don't know.
8. The most common reasons for a return (any): missing documents or certificates; data does not meet the specification; wrong size or does not fit the space; does not meet the code; clashes with other approved items or trades; wrong model or variant; other.
9. Approved equipment that did not fit or work once on site (one): never, once, a few times, often.
10. If it happened, roughly what fixing one case cost (one): under €1,000; €1,000 to 5,000; €5,000 to 20,000; €20,000 to 100,000; over €100,000; don't know.
11. How useful a tool would be that checks a submittal before review and shows whether the equipment fits in the building model (1 not useful to 5 very useful).
12. Anything else (free text, 500 characters at most, optional).

## 4. Results
`/survey/results`, for anyone signed in to RightFit: how many answered, and for each question the count of each answer and its share; for question 6 the median and the middle half. The comments and a CSV of every answer are for admins only. Each result says "as reported by N people, from <first day> to <last day>", and that answers are estimates.

## 5. Where it is kept
D1: `survey_response` (`web/migrations/0007_survey.sql`): id, the day, the version, the answers as JSON. The questions live in one place, `web/worker/survey_rules.ts`, which checks every answer and sums the results; the page asks the site for them.

## 6. Tests
`web/worker/survey_rules.test.ts`: an answer outside the options is refused, consent is required, the comment is cut to 500 characters, the robot field refuses, the sums and the median are right.
