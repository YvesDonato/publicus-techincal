create extension if not exists pgcrypto;

create table if not exists public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  status text not null default 'running',
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  records_seen integer not null default 0,
  records_upserted integer not null default 0,
  records_deactivated integer not null default 0,
  records_failed integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ingestion_runs_source_check check (
    source in ('grants', 'business-benefits')
  ),
  constraint ingestion_runs_status_check check (
    status in ('running', 'succeeded', 'failed', 'canceled')
  ),
  constraint ingestion_runs_counts_check check (
    records_seen >= 0
    and records_upserted >= 0
    and records_deactivated >= 0
    and records_failed >= 0
  ),
  constraint ingestion_runs_completed_at_check check (
    completed_at is null or completed_at >= started_at
  )
);

create table if not exists public.source_records (
  id uuid primary key default gen_random_uuid(),
  ingestion_run_id uuid references public.ingestion_runs(id) on delete set null,
  source text not null,
  source_id text not null,
  source_url text,
  resource_metadata jsonb not null default '{}'::jsonb,
  raw_record jsonb not null,
  title text not null default '',
  sponsor text,
  description text,
  province text,
  city text,
  amount numeric(14, 2),
  start_date date,
  end_date date,
  deadline_date date,
  status text,
  is_active boolean not null default true,
  content_hash text not null,
  fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint source_records_source_source_id_unique unique (source, source_id),
  constraint source_records_source_check check (
    source in ('grants', 'business-benefits')
  ),
  constraint source_records_source_id_length_check check (char_length(source_id) <= 512),
  constraint source_records_source_url_length_check check (
    source_url is null
    or (
      char_length(source_url) <= 2048
      and source_url ~* '^https?://'
    )
  ),
  constraint source_records_title_length_check check (char_length(title) <= 500),
  constraint source_records_sponsor_length_check check (sponsor is null or char_length(sponsor) <= 300),
  constraint source_records_province_length_check check (province is null or char_length(province) <= 120),
  constraint source_records_city_length_check check (city is null or char_length(city) <= 160),
  constraint source_records_amount_check check (amount is null or amount >= 0),
  constraint source_records_content_hash_length_check check (char_length(content_hash) <= 128)
);

create index if not exists ingestion_runs_source_idx
  on public.ingestion_runs (source);

create index if not exists ingestion_runs_status_idx
  on public.ingestion_runs (status);

create index if not exists ingestion_runs_source_status_started_at_idx
  on public.ingestion_runs (source, status, started_at desc);

create index if not exists source_records_source_idx
  on public.source_records (source);

create index if not exists source_records_ingestion_run_id_idx
  on public.source_records (ingestion_run_id);

create index if not exists source_records_active_idx
  on public.source_records (source, updated_at desc)
  where is_active;

create index if not exists source_records_province_idx
  on public.source_records (province);

create index if not exists source_records_start_date_idx
  on public.source_records (start_date);

create index if not exists source_records_end_date_idx
  on public.source_records (end_date);

create index if not exists source_records_deadline_date_idx
  on public.source_records (deadline_date);

create index if not exists source_records_raw_record_gin_idx
  on public.source_records using gin (raw_record);

create index if not exists source_records_search_gin_idx
  on public.source_records using gin (
    to_tsvector(
      'english',
      coalesce(title, '') || ' ' ||
      coalesce(sponsor, '') || ' ' ||
      coalesce(description, '')
    )
  );

create or replace function public.set_ingestion_runs_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_ingestion_runs_updated_at on public.ingestion_runs;
create trigger set_ingestion_runs_updated_at
  before update on public.ingestion_runs
  for each row execute function public.set_ingestion_runs_updated_at();

create or replace function public.set_source_records_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_source_records_updated_at on public.source_records;
create trigger set_source_records_updated_at
  before update on public.source_records
  for each row execute function public.set_source_records_updated_at();

alter table public.ingestion_runs enable row level security;
alter table public.source_records enable row level security;

drop policy if exists "Ingestion runs are publicly readable" on public.ingestion_runs;
create policy "Ingestion runs are publicly readable"
  on public.ingestion_runs
  for select
  using (true);

drop policy if exists "Source records are publicly readable" on public.source_records;
create policy "Source records are publicly readable"
  on public.source_records
  for select
  using (true);
