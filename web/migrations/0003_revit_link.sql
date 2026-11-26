-- 26 Nov 2026: the Revit link (spec/features/revit_link.md). For a database made before this date; a new one gets
-- it from schema.sql. Run once: npx wrangler d1 execute rightfit-db --remote --file=migrations/0003_revit_link.sql

-- The Revit link (spec/features/revit_link.md). A link waits 10 minutes for its approval on the site; the table keeps
-- only the SHA-256 of the secret Revit holds. user_code is what the person checks (ABCD-EFGH).
create table if not exists revit_link (
  user_code text primary key,
  device_hash text not null unique,
  computer text not null,
  created_at text not null,
  expires_at text not null,
  state text not null default 'pending' check (state in ('pending', 'approved', 'denied', 'used')),
  user_id text references "user" ("id") on delete cascade,
  team_hash text,                    -- the team password's hash, when the approving browser had it
  approved_at text
);
-- One linked computer: its token acts for one person, only its SHA-256 is kept, and unlinking stops it at once
create table if not exists revit_token (
  id text primary key,
  user_id text not null references "user" ("id") on delete cascade,
  token_hash text not null unique,
  computer text not null,
  team_hash text,                    -- opens locked projects while the team password stays the same
  created_at text not null,
  last_used_at text,
  revoked_at text
);
create index if not exists revit_token_user_idx on revit_token (user_id);
-- One check sent from Revit; the whole check and its picture are in the private bucket under
-- projects/<project>/fitcheck/runs/<id>.json and .png
create table if not exists fit_run (
  id text primary key,
  project_id text not null references project (id) on delete cascade,
  user_id text references "user" ("id") on delete set null,
  at text not null,                  -- when the site received it
  action text not null check (action in ('check', 'preview', 'swap')),
  set_id text not null default '',
  set_label text not null,
  submitted integer not null default 0,
  verdict text not null,
  confirmed integer not null default 0,  -- 1: on verified values; 0: what the check would say
  room text not null default '',
  model_file text not null default '',
  ran_at text not null default '',   -- the time on the computer that ran it
  counts text not null default '{}', -- how many results of each kind, as JSON
  computer text not null default '',
  has_image integer not null default 0
);
create index if not exists fit_run_project_idx on fit_run (project_id, at);
-- The set the reviewers chose for the project, with who and when
create table if not exists fit_choice (
  project_id text primary key references project (id) on delete cascade,
  set_id text not null,
  set_label text not null,
  note text not null default '',
  chosen_by text references "user" ("id") on delete set null,
  chosen_at text not null
);
