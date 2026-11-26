-- 26 Nov 2026: from the site to Revit (spec/features/revit_link.md §9). For a database made before this date; a new one
-- gets it from schema.sql. Run once: npx wrangler d1 execute rightfit-db --remote --file=migrations/0006_revit_command.sql
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
