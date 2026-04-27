create extension if not exists pgcrypto;

create table if not exists public.company_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  legal_entity_name text not null default '',
  doing_business_as text,
  business_number text,
  incorporation_date date,
  website text,
  province text,
  city text,
  company_type text not null default 'for-profit',
  employee_range text not null default '11-50',
  industry text,
  sub_sector text,
  keywords text,
  funding_need numeric(14, 2),
  funding_objectives text[] not null default '{}'::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint company_profiles_user_unique unique (user_id),
  constraint company_profiles_company_type_check check (
    company_type in ('for-profit', 'nonprofit', 'academic', 'public-sector')
  ),
  constraint company_profiles_employee_range_check check (
    employee_range in ('1-10', '11-50', '51-200', '200+')
  ),
  constraint company_profiles_province_check check (
    province is null
    or province in ('AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT')
  ),
  constraint company_profiles_funding_need_check check (
    funding_need is null or funding_need >= 0
  ),
  constraint company_profiles_funding_objectives_check check (
    funding_objectives <@ array[
      'research',
      'hiring',
      'equipment',
      'export',
      'facilities',
      'sustainability'
    ]::text[]
  )
);

create index if not exists company_profiles_user_id_idx
  on public.company_profiles (user_id);

create index if not exists company_profiles_industry_idx
  on public.company_profiles (industry);

create index if not exists company_profiles_province_idx
  on public.company_profiles (province);

create or replace function public.set_company_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_company_profiles_updated_at on public.company_profiles;
create trigger set_company_profiles_updated_at
  before update on public.company_profiles
  for each row execute function public.set_company_profiles_updated_at();

alter table public.company_profiles enable row level security;

drop policy if exists "Company profiles are readable by owner" on public.company_profiles;
create policy "Company profiles are readable by owner"
  on public.company_profiles
  for select
  using ((select auth.uid()) = user_id);

drop policy if exists "Company profiles are insertable by owner" on public.company_profiles;
create policy "Company profiles are insertable by owner"
  on public.company_profiles
  for insert
  with check ((select auth.uid()) = user_id);

drop policy if exists "Company profiles are updateable by owner" on public.company_profiles;
create policy "Company profiles are updateable by owner"
  on public.company_profiles
  for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Company profiles are deletable by owner" on public.company_profiles;
create policy "Company profiles are deletable by owner"
  on public.company_profiles
  for delete
  using ((select auth.uid()) = user_id);
