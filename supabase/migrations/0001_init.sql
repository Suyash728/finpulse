-- FinPulse initial schema. Single-user demo. Project has "auto-enable RLS" on: RLS with no policies, so only
-- the backend's service_role key (bypasses RLS) can read/write. Owner: Vaishnavi.
create extension if not exists pgcrypto;

create table if not exists uploads (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null check (kind in ('pdf', 'csv', 'sms')),
  filename    text,
  rows_total  int  not null default 0,
  rows_auto   int  not null default 0,          -- categorized by rule (no user touch)
  auto_rate   numeric(5,4) not null default 0,  -- rows_auto / rows_total
  reconciled  jsonb,                            -- {ok, opening, closing, computed_closing} (pdf only)
  created_at  timestamptz not null default now()
);

create table if not exists recurring (
  id            uuid primary key default gen_random_uuid(),
  merchant_norm text not null unique,
  category      text not null,
  amount        numeric(12,2) not null,
  prev_amount   numeric(12,2),
  cadence       text not null default 'monthly' check (cadence in ('weekly', 'monthly', 'yearly')),
  last_seen     date,
  status        text not null default 'active' check (status in ('active', 'changed', 'unused')),
  note          text,
  updated_at    timestamptz not null default now()
);

create table if not exists transactions (
  id            uuid primary key default gen_random_uuid(),
  upload_id     uuid references uploads(id) on delete cascade,
  date          date not null,
  amount        numeric(12,2) not null check (amount >= 0),
  direction     text not null check (direction in ('dr', 'cr')),
  raw_desc      text not null,
  merchant_norm text not null,
  category      text not null check (category in (
                  'Rent','Utilities','Groceries','Medical','EMI','Insurance','Education',
                  'Dining','Food Delivery','Shopping','Travel','Entertainment','Subscriptions',
                  'Fuel','Transfers','Income','Investments','Other')),
  cat_source    text not null check (cat_source in ('rule', 'ai', 'user')),
  confidence    numeric(4,3) not null default 0,
  needs_review  boolean not null default false,
  recurring_id  uuid references recurring(id) on delete set null,
  dedupe_key    text unique,                    -- date|amount|direction|raw_desc, avoids re-import dupes
  created_at    timestamptz not null default now()
);
create index if not exists transactions_merchant_norm_idx on transactions (merchant_norm);
create index if not exists transactions_date_idx on transactions (date);

create table if not exists category_rules (
  id               uuid primary key default gen_random_uuid(),
  match_type       text not null check (match_type in ('exact', 'normalized')),
  pattern          text not null,
  category         text not null,
  hits             int  not null default 0,
  created_from_txn uuid references transactions(id) on delete set null,
  created_at       timestamptz not null default now(),
  unique (match_type, pattern)
);

create table if not exists profile (
  id              int primary key default 1 check (id = 1),  -- single row
  monthly_income  numeric(12,2) not null default 0,
  fixed_costs     numeric(12,2) not null default 0,
  emergency_fund  numeric(12,2) not null default 0,
  email           text,
  budgets         jsonb not null default '{}'::jsonb,         -- {"Dining": 3000, ...}
  updated_at      timestamptz not null default now()
);
insert into profile (id) values (1) on conflict do nothing;

create table if not exists goals (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  target_amount numeric(12,2) not null,
  saved_amount  numeric(12,2) not null default 0,
  target_date   date not null,
  created_at    timestamptz not null default now()
);

create table if not exists nudges (
  id         uuid primary key default gen_random_uuid(),
  kind       text not null check (kind in ('drift', 'price_change', 'unused', 'essentials_over_income')),
  category   text,
  message    text not null,
  severity   text not null default 'info' check (severity in ('info', 'warn', 'alert')),
  month      text not null,                                   -- 'YYYY-MM'
  created_at timestamptz not null default now(),
  emailed_at timestamptz
);
