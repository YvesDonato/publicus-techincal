<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import { pushState } from '$app/navigation';
  import { hydrateCachedGrantsResult } from '$lib/client/funding-cache';
  import type { PageData } from './$types';

  type GrantRecord = {
    _id: number;
    ref_number: string | null;
    recipient_legal_name: string | null;
    agreement_value: string | null;
    agreement_start_date: string | null;
    agreement_end_date: string | null;
    prog_name_en: string | null;
    owner_org_title: string | null;
    recipient_city: string | null;
    recipient_province: string | null;
  };

  type GrantsPageData = PageData & {
    filters: {
      grantsCount: number;
    };
    limits: {
      increment: number;
      maxCount: number;
    };
    grants: GrantRecord[];
    grantsResult: {
      requested: number;
      count: number;
      records: GrantRecord[];
      total: number | null;
      endpoint: string;
      error: string | null;
    };
  };
  type SortMode = 'score' | 'amount' | 'newest';

  let { data }: { data: GrantsPageData } = $props();
  let cacheHydrated = $state(false);
  let loadingGrants = $state(false);
  let hydrationSequence = 0;
  let lastHydratedRequestKey = $state<string | null>(null);

  const sourceOrder: SortMode = 'score';
  const moneyFormatter = new Intl.NumberFormat('en-CA', {
    currency: 'CAD',
    maximumFractionDigits: 0,
    style: 'currency'
  });
  const dateFormatter = new Intl.DateTimeFormat('en-CA', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });

  const visibleGrantRecords = $derived(sortGrantRecords(data.grantsResult.records, sourceOrder));
  const nextGrantsCount = $derived(Math.min(data.limits.maxCount, data.filters.grantsCount + data.limits.increment));
  const canLoadMoreGrants = $derived(data.filters.grantsCount < data.limits.maxCount);
  const cacheRequestKey = $derived(getGrantsRequestKey(data));

  $effect(() => {
    if (!browser) {
      return;
    }

    const requestKey = cacheRequestKey;
    if (requestKey === lastHydratedRequestKey) {
      return;
    }

    void hydrateGrants(data, requestKey);
  });

  async function hydrateGrants(snapshot: GrantsPageData, requestKey = getGrantsRequestKey(snapshot)) {
    const sequence = ++hydrationSequence;
    const result = await hydrateCachedGrantsResult(snapshot.grantsResult.endpoint, snapshot.filters.grantsCount);

    if (sequence !== hydrationSequence) {
      return;
    }

    const records = result.records as GrantRecord[];
    data = {
      ...snapshot,
      grants: records,
      grantsResult: {
        ...result,
        records
      }
    };
    cacheHydrated = true;
    lastHydratedRequestKey = requestKey;
    loadingGrants = false;
  }

  async function loadMoreGrants() {
    if (!browser || loadingGrants || !canLoadMoreGrants) {
      return;
    }

    const grantsCount = nextGrantsCount;
    const nextData = buildGrantsSnapshot(grantsCount);

    loadingGrants = true;
    pushState(grantsRoute(grantsCount), {});
    await hydrateGrants(nextData);
  }

  function buildGrantsSnapshot(grantsCount: number): GrantsPageData {
    return {
      ...data,
      filters: {
        grantsCount
      },
      grantsResult: {
        ...data.grantsResult,
        requested: grantsCount,
        endpoint: updateGrantsEndpoint(data.grantsResult.endpoint, grantsCount),
        error: grantsCount === data.filters.grantsCount ? data.grantsResult.error : null
      }
    };
  }

  function getGrantsRequestKey(payload: GrantsPageData): string {
    return [payload.filters.grantsCount, payload.grantsResult.endpoint].join('|');
  }

  function updateGrantsEndpoint(endpoint: string, count: number): string {
    try {
      const url = new URL(endpoint);
      url.searchParams.set('limit', String(count));
      url.searchParams.set('offset', '0');
      return url.toString();
    } catch {
      return endpoint;
    }
  }

  function valueIsPresent(value: unknown): boolean {
    return value !== null && value !== undefined && value !== '';
  }

  function parseMoney(value: unknown): number | null {
    if (!valueIsPresent(value)) {
      return null;
    }

    const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function formatMoney(value: unknown): string {
    const parsed = parseMoney(value);
    return parsed === null ? 'Value unavailable' : moneyFormatter.format(parsed);
  }

  function formatDate(value: string | null | undefined): string {
    if (!value) {
      return 'Date unavailable';
    }

    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
  }

  function formatLocation(city: string | null | undefined, province: string | null | undefined): string {
    return [city, province].filter(Boolean).join(', ') || 'Location unavailable';
  }

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : 'Unavailable';
  }

  function getGrantKey(grant: GrantRecord, index: number): string | number {
    return grant._id ?? grant.ref_number ?? `grant-${index}`;
  }

  function getGrantDateValue(grant: GrantRecord): number {
    if (!grant.agreement_start_date) {
      return 0;
    }

    const parsed = new Date(`${grant.agreement_start_date}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function sortGrantRecords(records: GrantRecord[], mode: SortMode): GrantRecord[] {
    if (mode === 'amount') {
      return [...records].sort(
        (left, right) => (parseMoney(right.agreement_value) ?? 0) - (parseMoney(left.agreement_value) ?? 0)
      );
    }

    if (mode === 'newest') {
      return [...records].sort((left, right) => getGrantDateValue(right) - getGrantDateValue(left));
    }

    return records;
  }

  function grantsRoute(count: number): string {
    return `/dashboard/discovery?count=${count}`;
  }
</script>

<svelte:head>
  <title>Discovery | FundRadar</title>
  <meta name="description" content="Browse grant discovery records in FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="discovery" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search grants, programs, or workspace pages..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end" aria-labelledby="grants-heading">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Discovery</p>
            <h2 id="grants-heading" class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Discovery
            </h2>
            <p class="m-0 max-w-2xl text-base leading-6 text-[#45464d]">
              Review grants and contributions in the same FundRadar workspace theme.
            </p>
          </div>

        </section>

        <section class="rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
          <div class="flex flex-col justify-between gap-4 border-b border-[#c6c6cd] p-5 md:flex-row md:items-end">
            <div>
              <h3 class="m-0 text-2xl font-semibold leading-tight text-[#191c1e]">Grant records</h3>
              <p class="m-0 mt-2 max-w-2xl text-sm leading-6 text-[#45464d]">
                Browse grants and expand the list when you need more coverage.
              </p>
            </div>
            <span class="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
              {cacheHydrated && !loadingGrants ? 'Ready' : 'Loading'}
            </span>
          </div>

          <div class="p-5">
            {#if !cacheHydrated}
              <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                <h3 class="m-0 text-lg font-semibold text-[#191c1e]">Loading grants</h3>
                <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">Preparing the latest saved grant records.</p>
              </section>
            {:else if data.grantsResult.error}
              <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="status">
                <h3 class="m-0 font-semibold">Grants unavailable</h3>
                <p class="m-0 mt-2 leading-6">{data.grantsResult.error}</p>
              </section>
            {:else if visibleGrantRecords.length === 0}
              <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No grants returned</h3>
                <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">No grants are available for this selection.</p>
              </section>
            {:else}
              <section class="grid grid-cols-1 gap-4 md:grid-cols-2" aria-label="Grant records">
                {#each visibleGrantRecords as grant, index (getGrantKey(grant, index))}
                  <article class="group flex flex-col rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition hover:border-[#76777d] hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
                    <div class="mb-4 flex items-start justify-between gap-4">
                      <div class="min-w-0">
                        <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">
                          {grant.prog_name_en ?? 'Grant / Contribution'}
                        </span>
                        <h3 class="m-0 text-lg font-semibold leading-snug text-[#191c1e] transition group-hover:text-emerald-700">
                          {grant.recipient_legal_name ?? 'Recipient unavailable'}
                        </h3>
                        <p class="m-0 mt-1 text-sm leading-5 text-[#45464d]">{grant.owner_org_title ?? 'Organization unavailable'}</p>
                      </div>
                      <div class="shrink-0 text-right">
                        <strong class="block font-[Public_Sans] text-2xl font-semibold text-[#191c1e]">{formatMoney(grant.agreement_value)}</strong>
                      </div>
                    </div>

                    <dl class="mt-auto grid grid-cols-1 gap-3 border-t border-[#c6c6cd] pt-4 sm:grid-cols-2">
                      <div>
                        <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Period</dt>
                        <dd class="m-0 mt-1 text-sm leading-5 text-[#191c1e]">
                          {formatDate(grant.agreement_start_date)} to {formatDate(grant.agreement_end_date)}
                        </dd>
                      </div>
                      <div>
                        <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Location</dt>
                        <dd class="m-0 mt-1 text-sm leading-5 text-[#191c1e]">{formatLocation(grant.recipient_city, grant.recipient_province)}</dd>
                      </div>
                      <div class="sm:col-span-2">
                        <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Reference</dt>
                        <dd class="m-0 mt-1 break-words text-sm leading-5 text-[#191c1e]">{grant.ref_number ?? 'Reference unavailable'}</dd>
                      </div>
                    </dl>
                  </article>
                {/each}
              </section>
            {/if}

            {#if cacheHydrated && !data.grantsResult.error}
              <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#c6c6cd] pt-4">
                {#if canLoadMoreGrants}
                  <button
                    class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-wait disabled:opacity-60"
                    type="button"
                    disabled={loadingGrants}
                    onclick={loadMoreGrants}
                  >
                    {loadingGrants ? 'Loading more grants' : 'Load more grants'}
                  </button>
                  <p class="m-0 text-sm leading-6 text-[#45464d]">Request more grant records.</p>
                {:else}
                  <p class="m-0 text-sm leading-6 text-[#45464d]">The grant record window is at its limit.</p>
                {/if}
              </div>
            {/if}
          </div>
        </section>
      </div>
    </main>
  </div>
</div>
