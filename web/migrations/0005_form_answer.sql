-- 26 Nov 2026: the answer a form got (MAF-36c), as a reviewer records it, apart from RightFit's draft letter. Its own
-- table, so an import from the laptop, which replaces the packages it brought, never loses it. For a database made
-- before this date; a new one gets it from schema.sql.
create table if not exists form_answer (
  project_id text not null references project (id) on delete cascade,
  code text not null,                -- the package: P01, P02 ...
  answer text not null check (answer in ('A', 'B', 'C')),
  answered_by text references "user" ("id") on delete set null,
  answered_at text not null,
  primary key (project_id, code)
);
