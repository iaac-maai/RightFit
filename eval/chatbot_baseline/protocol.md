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

    You are reviewing a material approval form (MAF) package for MEP equipment on a building project in Romania, before the consultant signs it. The attached files are the form and its attachments.
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

## Changes of 13 Nov 2026, before any run

Made after reading how published work compares AI and human document review (e-discovery, contract review, reporting guides such as DECIDE-AI). No chatbot and no RightFit output had been seen when they were written.

- The prompt no longer says "residential project in Bucharest": the BOQ shows that P01 and P02 come from a sports building, so the prompt says "a building project in Romania".

1. Same form for every finding. Before Luca judges them, every finding (RightFit, each chatbot, and his own first review) is put in one form: what is wrong in at most 25 words, file, page, quote. The wording is only cut, never rewritten, so nothing is added. A finding that gives no page says "no page given"; this can still hint at the source, and the results say so.
2. Time. Luca's reference review of each test package is timed from opening the package to his answer: this is the time by hand. The time with RightFit is measured on five other packages, not used for accuracy, where Luca reviews in the app from the start and writes his answer from it. The same package is never timed twice, because the second look is faster anyway. Both are reported as medians, with the five-package limit stated.
3. A test set of unseen packages. P01 and P02 helped build the rules, so their results are a demonstration, not a test. From the second batch, at least 20 packages are drawn at random before any of them is read, with the revisions of one MAF kept together, and frozen in `eval/chatbot_baseline/test_set.csv` (package ids only). Three quarters of the second batch trained the page classifier; if the classifier is part of the run, its results are also given on the packages it did not train on. With fewer than 20 packages read by 3 Dec 2026, the results are called a demonstration and carry no confidence interval.
4. A second reviewer. A practising MEP consultant from outside the team judges the same blinded findings of at least five test packages. Agreement between the two is reported as Cohen's kappa, per kind of finding (missing document, value, rule). Where they disagree, Luca decides and writes why; a finding they still read differently is counted as contested, not hidden.
5. Scans apart. Every result is also given separately for packages whose PDFs have a text layer and for packages with scanned PDFs (`pdfs_without_text` in the batch 2 inventory).

Reporting, for each system (Luca by hand, RightFit, RightFit checked by Luca, each chatbot): the real problems found out of all the real problems any source found and Luca confirmed; the findings that are not problems; wrong pages or quotes; the answer A, B or C against Luca's. With 20 packages or more, 95 % confidence intervals come from a bootstrap that resamples whole packages, never single findings or pages.

What we will not claim: that RightFit is better than an engineer; that Luca's review finds everything (two expert reviewers agree on about 65 % in published e-discovery work); any figure from P01 and P02 as a test result; a number without its interval when there are 20 packages or more; script time as review time.
