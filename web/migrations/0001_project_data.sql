-- 20 Nov 2026: the project's own data online. For a database made before this date; a new one gets it from schema.sql.
alter table project add column locked integer not null default 0;

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
  primary key (project_id, code)
);
create table if not exists package_file (
  project_id text not null references project (id) on delete cascade,
  code text not null,
  name text not null,
  size integer not null,
  pages integer,
  primary key (project_id, code, name)
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
