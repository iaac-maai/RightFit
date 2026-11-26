-- 26 Nov 2026: the practice survey (spec/features/survey.md). For a database made before this date; a new one gets it
-- from schema.sql. Run once: npx wrangler d1 execute rightfit-db --remote --file=migrations/0007_survey.sql
-- One anonymous answer: the day it was sent (not the time), the survey's version, the answers as JSON. Nothing about
-- the person, their browser or their address.
create table if not exists survey_response (
  id text primary key,
  day text not null,
  version text not null,
  answers text not null
);
