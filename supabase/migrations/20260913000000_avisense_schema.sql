-- Avisense schema (v3).
--
-- Safe to run on a fresh Supabase project and on a database created by the
-- older 0001-0003 migrations: every statement is idempotent and additive.
-- Older tables that v3 no longer uses (predictions, models, model_registry,
-- prediction_stats, drift_metrics, ...) are left in place. See the end of the
-- file for an optional cleanup.
--
-- Security model: the API calls Supabase with the anon key plus the signed-in
-- user's access token, so the row-level security policies below are the only
-- thing standing between users. Every table is owner-scoped.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- profiles: one row per auth user
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  full_name text,
  organization_name text,
  role text not null default 'engineer',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.profiles add column if not exists organization_name text;

-- The 0003 trigger inserted into a column that did not exist, which made every
-- sign-up fail. This version matches the table.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name, organization_name)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'organization_name'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Users who signed up while the trigger was broken have no profile, and
-- engines.owner_id references profiles. Backfill them.
insert into public.profiles (id, email)
select u.id, u.email from auth.users u
where not exists (select 1 from public.profiles p where p.id = u.id);

-- ---------------------------------------------------------------------------
-- engines
-- ---------------------------------------------------------------------------
create table if not exists public.engines (
  id uuid primary key default gen_random_uuid(),
  engine_id text not null,
  model text,
  serial_number text,
  aircraft_registration text,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  status text not null default 'active',
  metadata jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (engine_id, owner_id)
);
-- Latest assessment, denormalized so the fleet view is one query.
alter table public.engines add column if not exists health jsonb;
alter table public.engines alter column owner_id set default auth.uid();

-- ---------------------------------------------------------------------------
-- telemetry: one row per engine cycle
-- ---------------------------------------------------------------------------
create table if not exists public.telemetry (
  id uuid primary key default gen_random_uuid(),
  engine_id uuid not null references public.engines (id) on delete cascade,
  source text,
  created_at timestamptz not null default now()
);

alter table public.telemetry
  add column if not exists cycle integer,
  add column if not exists setting_1 double precision,
  add column if not exists setting_2 double precision,
  add column if not exists setting_3 double precision,
  add column if not exists sensor_1 double precision,
  add column if not exists sensor_2 double precision,
  add column if not exists sensor_3 double precision,
  add column if not exists sensor_4 double precision,
  add column if not exists sensor_5 double precision,
  add column if not exists sensor_6 double precision,
  add column if not exists sensor_7 double precision,
  add column if not exists sensor_8 double precision,
  add column if not exists sensor_9 double precision,
  add column if not exists sensor_10 double precision,
  add column if not exists sensor_11 double precision,
  add column if not exists sensor_12 double precision,
  add column if not exists sensor_13 double precision,
  add column if not exists sensor_14 double precision,
  add column if not exists sensor_15 double precision,
  add column if not exists sensor_16 double precision,
  add column if not exists sensor_17 double precision,
  add column if not exists sensor_18 double precision,
  add column if not exists sensor_19 double precision,
  add column if not exists sensor_20 double precision,
  add column if not exists sensor_21 double precision;

-- v2 rows have no cycle number and are ignored by v3 (NULLs never collide here).
create unique index if not exists telemetry_engine_cycle_key on public.telemetry (engine_id, cycle);

-- ---------------------------------------------------------------------------
-- assessments: saved model outputs
-- ---------------------------------------------------------------------------
create table if not exists public.assessments (
  id uuid primary key default gen_random_uuid(),
  engine_id uuid not null references public.engines (id) on delete cascade,
  cycle integer not null,
  status text not null check (status in ('healthy', 'watch', 'critical')),
  rul double precision not null,
  rul_low double precision not null,
  rul_high double precision not null,
  failure_probability double precision not null check (failure_probability between 0 and 1),
  summary text,
  contributions jsonb,
  model_version text not null,
  created_by uuid references public.profiles (id) default auth.uid(),
  created_at timestamptz not null default now()
);
create index if not exists assessments_engine_created_idx on public.assessments (engine_id, created_at desc);

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_engines_updated_at on public.engines;
create trigger trg_engines_updated_at
  before update on public.engines
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.engines enable row level security;
alter table public.telemetry enable row level security;
alter table public.assessments enable row level security;

-- True when the engine belongs to the calling user.
create or replace function public.owns_engine(target uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.engines e where e.id = target and e.owner_id = auth.uid());
$$;

drop policy if exists "profiles_select_self" on public.profiles;
drop policy if exists "profiles_insert_self" on public.profiles;
drop policy if exists "profiles_update_self" on public.profiles;
create policy "profiles_select_self" on public.profiles for select using (auth.uid() = id);
create policy "profiles_insert_self" on public.profiles for insert with check (auth.uid() = id);
create policy "profiles_update_self" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "engines_select_owner" on public.engines;
drop policy if exists "engines_insert_owner" on public.engines;
drop policy if exists "engines_update_owner" on public.engines;
drop policy if exists "engines_delete_owner" on public.engines;
create policy "engines_select_owner" on public.engines for select using (owner_id = auth.uid());
create policy "engines_insert_owner" on public.engines for insert with check (owner_id = auth.uid());
create policy "engines_update_owner" on public.engines for update using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy "engines_delete_owner" on public.engines for delete using (owner_id = auth.uid());

drop policy if exists "telemetry_select_owner" on public.telemetry;
drop policy if exists "telemetry_insert_owner" on public.telemetry;
drop policy if exists "telemetry_delete_owner" on public.telemetry;
create policy "telemetry_select_owner" on public.telemetry for select using (public.owns_engine(engine_id));
create policy "telemetry_insert_owner" on public.telemetry for insert with check (public.owns_engine(engine_id));
create policy "telemetry_delete_owner" on public.telemetry for delete using (public.owns_engine(engine_id));

drop policy if exists "assessments_select_owner" on public.assessments;
drop policy if exists "assessments_insert_owner" on public.assessments;
create policy "assessments_select_owner" on public.assessments for select using (public.owns_engine(engine_id));
create policy "assessments_insert_owner" on public.assessments
  for insert with check (public.owns_engine(engine_id) and created_by = auth.uid());

grant select, insert, update, delete on public.engines to authenticated;
grant select, insert, delete on public.telemetry to authenticated;
grant select, insert on public.assessments to authenticated;
grant select, insert, update on public.profiles to authenticated;
revoke all on public.engines, public.telemetry, public.assessments from anon;

-- ---------------------------------------------------------------------------
-- Optional cleanup of v2 tables (not run automatically; review before use)
-- ---------------------------------------------------------------------------
-- drop table if exists public.prediction_feedback, public.model_comparison,
--   public.drift_metrics, public.prediction_stats, public.model_registry,
--   public.predictions, public.models cascade;
