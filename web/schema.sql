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
  created_at text not null
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
