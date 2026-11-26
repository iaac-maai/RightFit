-- The D1 database of RightFit online (spec/features/rightfit_online.md, section 7).
-- Run once: npm run db:local (on the laptop) or npm run db:remote (online). Running it again changes nothing.

-- Accounts, as Better Auth 1.7.17 expects them: people, sessions, sign-in links (password or Google), verifications
create table if not exists "user" ("id" text not null primary key, "name" text not null, "email" text not null unique, "emailVerified" integer not null, "image" text, "createdAt" date not null, "updatedAt" date not null);
create table if not exists "session" ("id" text not null primary key, "expiresAt" date not null, "token" text not null unique, "createdAt" date not null, "updatedAt" date not null, "ipAddress" text, "userAgent" text, "userId" text not null references "user" ("id") on delete cascade);
create table if not exists "account" ("id" text not null primary key, "accountId" text not null, "providerId" text not null, "userId" text not null references "user" ("id") on delete cascade, "accessToken" text, "refreshToken" text, "idToken" text, "accessTokenExpiresAt" date, "refreshTokenExpiresAt" date, "scope" text, "password" text, "createdAt" date not null, "updatedAt" date not null);
create table if not exists "verification" ("id" text not null primary key, "identifier" text not null, "value" text not null, "expiresAt" date not null, "createdAt" date not null, "updatedAt" date not null);
create index if not exists "session_userId_idx" on "session" ("userId");
create index if not exists "account_userId_idx" on "account" ("userId");
create index if not exists "verification_identifier_idx" on "verification" ("identifier");

-- The terms and privacy note each person accepted, by version
create table if not exists consent ("userId" text not null references "user" ("id") on delete cascade, "termsVersion" text not null, "acceptedAt" text not null, primary key ("userId", "termsVersion"));

-- A project space, opened by a consultant
create table if not exists project (
  id text primary key,
  name text not null,
  country text not null check (country in ('RO', 'ES')),
  created_by text not null,  -- the user who opened it
  created_at text not null,
  dpa_version text not null,     -- the data processing agreement the consultant accepted for their organisation
  dpa_accepted_by text not null, -- that consultant's user id
  dpa_accepted_at text not null,
  locked integer not null default 0  -- 1: the project's data opens only with the team password as well
);

-- A person in a project, with their role there; invited_by is the member who brought them in (empty for the
-- consultant who opened the project)
create table if not exists member (
  id text primary key,
  project_id text not null references project (id) on delete cascade,
  user_id text not null references "user" ("id") on delete cascade,
  role text not null check (role in ('consultant', 'designer', 'site_supervisor', 'client', 'contractor', 'subcontractor')),
  company text not null default '',
  invited_by text,
  joined_at text not null,
  unique (project_id, user_id)
);
create index if not exists member_user_idx on member (user_id);

-- An invitation: the link holds a secret token, the table only its SHA-256, so the database alone can't join anyone
create table if not exists invitation (
  id text primary key,
  project_id text not null references project (id) on delete cascade,
  email text not null,       -- lower case
  role text not null check (role in ('consultant', 'designer', 'site_supervisor', 'client', 'contractor', 'subcontractor')),
  company text not null default '',
  invited_by text not null,  -- the member who sent it
  token_hash text not null unique,
  created_at text not null,
  expires_at text not null,
  state text not null default 'pending' check (state in ('pending', 'accepted', 'declined', 'withdrawn'))
);
create index if not exists invitation_project_idx on invitation (project_id, state);
create index if not exists invitation_email_idx on invitation (email, state);

-- What happened, for the people who run RightFit and for accountability: who did what, when, in which project.
-- Kept 12 months (worker/admin.ts deletes older rows). It names people by user id, never by email.
create table if not exists event (
  id integer primary key autoincrement,
  at text not null,
  actor text,                -- the user id who did it; empty when RightFit did it
  project_id text,
  action text not null,      -- for example project.opened, invitation.sent, member.joined, admin.member_removed
  detail text not null default '{}'
);
create index if not exists event_at_idx on event (at);
create index if not exists event_project_idx on event (project_id, at);

-- The project's own data, imported from the laptop by web/scripts/import_project.py: its MAF packages, the files of
-- each (kept in the private R2 bucket under projects/<project>/packages/<code>/), RightFit's draft review of the packages
-- already read (in R2, projects/<project>/reviews/<code>.json) and the lines of its BOQ, never the prices
create table if not exists package (
  project_id text not null references project (id) on delete cascade,
  code text not null,                -- P01, P02 ...
  form_no text not null,
  revision integer not null default 0,
  discipline text not null default '',
  items text not null default '[]',  -- the products on the form, as JSON
  files integer not null default 0,
  pages integer,
  letter text,                       -- RightFit's draft answer (A, B or C), for a package already read
  label text,
  problems integer,
  questions integer,
  to_confirm integer,
  readings integer,
  reviewed_at text,                  -- when that draft was made, on the laptop
  imported_at text not null,
  uploaded_by text references "user" (id) on delete set null, -- added on the site, not imported from the laptop
  uploaded_at text,
  primary key (project_id, code)
);
create table if not exists package_file (
  project_id text not null references project (id) on delete cascade,
  code text not null,
  name text not null,
  size integer not null,
  pages integer,
  sha text,                          -- the first 16 characters of the file's SHA-256: the same file in two packages
  primary key (project_id, code, name)
);
create index if not exists package_file_sha_idx on package_file (sha);
-- The answer a form got, as a reviewer records it (MAF-36c), apart from RightFit's draft letter; kept apart from
-- package, so an import from the laptop never loses it
create table if not exists form_answer (
  project_id text not null references project (id) on delete cascade,
  code text not null,
  answer text not null check (answer in ('A', 'B', 'C')),
  answered_by text references "user" ("id") on delete set null,
  answered_at text not null,
  primary key (project_id, code)
);
create table if not exists boq_line (
  project_id text not null references project (id) on delete cascade,
  file text not null,
  sheet text not null,               -- the BOQ's own chapters, one sheet each
  row integer not null,              -- the row as in Excel
  nr text,
  text text not null,
  unit text,
  qty text,
  producer text,
  standards text,
  primary key (project_id, file, sheet, row)
);
create index if not exists boq_line_sheet_idx on boq_line (project_id, sheet);

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

-- A message from the Fit check page for the person's own linked Revit: it waits 2 minutes, one computer takes it, and
-- Revit answers whether it worked.
create table if not exists revit_command (
  id text primary key,
  user_id text not null references "user" ("id") on delete cascade,
  project_id text not null references project (id) on delete cascade,
  kind text not null check (kind in ('preview')),
  set_id text not null,
  set_label text not null default '',
  created_at text not null,
  state text not null default 'waiting' check (state in ('waiting', 'taken', 'done', 'failed', 'expired')),
  taken_by text,                     -- the revit_token that took it
  taken_at text,
  done_at text,
  message text not null default ''   -- Revit's answer, or why it could not
);
create index if not exists revit_command_user_idx on revit_command (user_id, state, created_at);

-- One anonymous answer: the day it was sent (not the time), the survey's version, the answers as JSON. Nothing about
-- the person, their browser or their address.
create table if not exists survey_response (
  id text primary key,
  day text not null,
  version text not null,
  answers text not null
);
