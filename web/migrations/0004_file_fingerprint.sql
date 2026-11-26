-- 26 Nov 2026: the fingerprint of every file (MAF-36b), the first 16 characters of its SHA-256, so the same file in two
-- packages is recognised. For a database made before this date; a new one gets it from schema.sql. Files imported
-- before it get their fingerprint at the next import from the laptop.
alter table package_file add column sha text;
create index if not exists package_file_sha_idx on package_file (sha);
