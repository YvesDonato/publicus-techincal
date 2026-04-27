create extension if not exists vector with schema extensions;

create table if not exists public.opportunity_embeddings (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_id text not null,
  title text not null default '',
  body text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(1536) not null,
  content_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source, source_id)
);

create index if not exists opportunity_embeddings_source_idx
  on public.opportunity_embeddings (source);

create index if not exists opportunity_embeddings_embedding_hnsw_idx
  on public.opportunity_embeddings
  using hnsw (embedding vector_cosine_ops);

alter table public.opportunity_embeddings enable row level security;

drop policy if exists "Opportunity embeddings are readable by authenticated users" on public.opportunity_embeddings;
create policy "Opportunity embeddings are readable by authenticated users"
  on public.opportunity_embeddings
  for select
  to authenticated
  using (true);

create or replace function public.set_opportunity_embeddings_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_opportunity_embeddings_updated_at on public.opportunity_embeddings;
create trigger set_opportunity_embeddings_updated_at
  before update on public.opportunity_embeddings
  for each row execute function public.set_opportunity_embeddings_updated_at();

create or replace function public.match_opportunities(
  query_embedding vector(1536),
  match_source text default null,
  match_count int default 20
)
returns table (
  id uuid,
  source text,
  source_id text,
  title text,
  body text,
  metadata jsonb,
  similarity float
)
language sql
stable
as $$
  select
    opportunity_embeddings.id,
    opportunity_embeddings.source,
    opportunity_embeddings.source_id,
    opportunity_embeddings.title,
    opportunity_embeddings.body,
    opportunity_embeddings.metadata,
    1 - (opportunity_embeddings.embedding <=> query_embedding) as similarity
  from public.opportunity_embeddings
  where match_source is null or opportunity_embeddings.source = match_source
  order by opportunity_embeddings.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 100);
$$;
