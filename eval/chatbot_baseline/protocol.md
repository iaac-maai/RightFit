# Chatbot baseline

Protocol written on 10 Nov 2026, before any chatbot answer was seen. At the midterm on 6 Nov the jury asked how RightFit differs from a general chatbot. This test answers with numbers: the same packages go to general chatbots and to RightFit, and Luca judges every finding without knowing which system wrote it.

## Packages

P01 (pumps) and P02 (air handling unit with DX outdoor units). Luca wrote his reference answers on 28 Oct 2026, in `data/maf/reference/`. RightFit's findings are the problems its review page shows for each package: the checks only, not the AI suggestions tab.

## Runs

- Claude.ai and ChatGPT, each in a chat that keeps no memory (Claude incognito chat, ChatGPT temporary chat), outside any project;
- each package twice in each chatbot, in separate chats, to see whether the answer changes;
- the chatbot gets the files RightFit reads: the form and every attachment; if it refuses the .xls form, it gets the form saved as PDF;
- every answer is saved as plain text in `data/raw/chatbot_baseline/`, which stays on the laptop like the packages, one file per run (for example `P01_bot1_run1.txt`), with the date and the model name if the page shows it;

## Prompt

Pasted as it is, with nothing added:

    You are reviewing a material approval form (MAF) package for MEP equipment on a residential project in Bucharest, Romania, before the consultant signs it. The attached files are the form and its attachments.
    1. List every problem a reviewer should raise. For each one give the file, the page, a short quote from the document and the rule or requirement behind it.
    2. List what you could not check, and why.
    3. Give the answer: A (approved), B (approved with comments) or C (revise and resubmit), with the reasons.
    Use only what is in the documents and laws or standards you can name exactly. Do not guess values.

## Scoring

- each answer, and RightFit's findings for the same package, is split into single findings, and findings that say the same thing are merged;
- the findings go into one shuffled list with the source hidden, and Luca marks each one as a real problem, not a problem, or can't tell;
- every page reference and quote is checked against the file;
- for each system and package: real problems found, findings that are not problems, wrong pages or quotes, and the answer against what happened (P01 approved; P02 revisions 0 to 3 turned down because the client wanted a different brand of AHU);
- for each chatbot: how much its two runs differ, in findings and in the answer;
- the results go in `eval/chatbot_baseline/results.md`, good or bad;

## Limits

Two packages make a demonstration, not an evaluation; the test is repeated later on the locked packages of the second batch. Luca wrote the reference answers and also judges the findings; hiding the source is how we reduce that bias. RightFit's values for P01 and P02 are still unverified, so its findings are "would be" findings.
