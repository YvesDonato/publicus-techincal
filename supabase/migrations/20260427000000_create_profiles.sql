create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  organization_name text,
  title text,
  avatar_url text,
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "Profiles are readable by owner" on public.profiles;
create policy "Profiles are readable by owner"
  on public.profiles
  for select
  using ((select auth.uid()) = id);

drop policy if exists "Profiles are insertable by owner" on public.profiles;
create policy "Profiles are insertable by owner"
  on public.profiles
  for insert
  with check ((select auth.uid()) = id);

drop policy if exists "Profiles are updateable by owner" on public.profiles;
create policy "Profiles are updateable by owner"
  on public.profiles
  for update
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

create or replace function public.handle_new_user_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (
    id,
    email,
    full_name,
    organization_name,
    title,
    avatar_url
  )
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'organization_name',
    new.raw_user_meta_data ->> 'title',
    coalesce(new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture')
  )
  on conflict (id) do update
    set
      email = excluded.email,
      updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile
  after insert on auth.users
  for each row execute function public.handle_new_user_profile();
