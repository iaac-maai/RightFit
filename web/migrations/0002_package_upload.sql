-- 22 Nov 2026: a package can be added online, its files sent from the browser into the private bucket. For a database
-- made before this date; a new one gets it from schema.sql. A package with uploaded_by came from the site, not from the
-- laptop, so an import from the laptop leaves it as it is.
alter table package add column uploaded_by text references "user" (id) on delete set null;
alter table package add column uploaded_at text;
