<script lang="ts">
  import { browser } from '$app/environment';
  import { pushState } from '$app/navigation';
  import { hydrateCachedBenefitsResult } from '$lib/client/funding-cache';
  import type { PageData } from './$types';

  type GenericRecord = Record<string, unknown>;
  type FieldMatch = {
    key: string;
    value: unknown;
  };
  type BenefitsPageData = PageData & {
    filters: {
      benefitsCount: number;
    };
    limits: {
      increment: number;
      maxCount: number;
    };
    benefits: {
      requested: number;
      count: number;
      records: GenericRecord[];
      source: string | null;
      endpoint: string;
      error: string | null;
    };
  };
  type SortMode = 'score' | 'amount' | 'newest';

  let { data }: { data: BenefitsPageData } = $props();
  let cacheHydrated = $state(false);
  let loadingBenefits = $state(false);
  let hydrationSequence = 0;
  let lastHydratedRequestKey = $state<string | null>(null);

  const titleFields = [
    'title',
    'project_title',
    'project_name',
    'name',
    'company_name',
    'business_name',
    'recipient_legal_name',
    'organization_name',
    'applicant_name'
  ];
  const subtitleFields = [
    'program',
    'program_name',
    'program_name_en',
    'funding_program',
    'stream',
    'sector',
    'industry',
    'status'
  ];
  const amountFields = ['amount', 'funding_amount', 'approved_amount', 'agreement_value', 'contribution'];
  const locationFields = ['location', 'city', 'province', 'region', 'country'];
  const dateFields = [
    'agreement_start_date',
    'start_date',
    'end_date',
    'date',
    'created_at',
    'updated_at',
    'modified'
  ];
  const idFields = ['_id', 'id', 'record_id', 'project_id', 'application_id', 'token', 'reference'];
  const highlightedFields = new Set([
    ...titleFields,
    ...subtitleFields,
    ...amountFields,
    ...locationFields,
    ...dateFields,
    ...idFields
  ]);
  const sourceOrder: SortMode = 'score';

  const visibleBenefitRecords = $derived(sortGenericRecords(data.benefits.records, sourceOrder));
  const nextBenefitsCount = $derived(Math.min(data.limits.maxCount, data.filters.benefitsCount + data.limits.increment));
  const canLoadMoreBenefits = $derived(data.filters.benefitsCount < data.limits.maxCount);
  const cacheRequestKey = $derived(getBenefitsRequestKey(data));

  $effect(() => {
    if (!browser) {
      return;
    }

    const requestKey = cacheRequestKey;
    if (requestKey === lastHydratedRequestKey) {
      return;
    }

    void hydrateBenefits(data, requestKey);
  });

  async function hydrateBenefits(snapshot: BenefitsPageData, requestKey = getBenefitsRequestKey(snapshot)) {
    const sequence = ++hydrationSequence;
    const benefits = await hydrateCachedBenefitsResult(snapshot.benefits.endpoint, snapshot.filters.benefitsCount);

    if (sequence !== hydrationSequence) {
      return;
    }

    data = {
      ...snapshot,
      benefits
    };
    cacheHydrated = true;
    lastHydratedRequestKey = requestKey;
    loadingBenefits = false;
  }

  async function loadMoreBenefits() {
    if (!browser || loadingBenefits || !canLoadMoreBenefits) {
      return;
    }

    const benefitsCount = nextBenefitsCount;
    const nextData = buildBenefitsSnapshot(benefitsCount);

    loadingBenefits = true;
    pushState(benefitsRoute(benefitsCount), {});
    await hydrateBenefits(nextData);
  }

  function buildBenefitsSnapshot(benefitsCount: number): BenefitsPageData {
    return {
      ...data,
      filters: {
        benefitsCount
      },
      benefits: {
        ...data.benefits,
        requested: benefitsCount,
        endpoint: updateBenefitsEndpoint(data.benefits.endpoint, benefitsCount),
        error: benefitsCount === data.filters.benefitsCount ? data.benefits.error : null
      }
    };
  }

  function getBenefitsRequestKey(payload: BenefitsPageData): string {
    return [payload.filters.benefitsCount, payload.benefits.endpoint].join('|');
  }

  function updateBenefitsEndpoint(endpoint: string, count: number): string {
    try {
      const url = new URL(endpoint);
      const segments = url.pathname.split('/');
      const firstIndex = segments.lastIndexOf('first');

      if (firstIndex >= 0 && firstIndex + 1 < segments.length) {
        segments[firstIndex + 1] = String(count);
        url.pathname = segments.join('/');
      } else {
        url.searchParams.set('limit', String(count));
      }

      return url.toString();
    } catch {
      return endpoint;
    }
  }

  function valueIsPresent(value: unknown): boolean {
    return value !== null && value !== undefined && value !== '';
  }

  function valueToString(value: unknown): string {
    if (!valueIsPresent(value)) {
      return 'Unavailable';
    }

    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }

    if (typeof value === 'object') {
      return JSON.stringify(value);
    }

    return String(value);
  }

  function findField(record: GenericRecord, candidates: string[]): FieldMatch | null {
    const normalizedEntries = Object.entries(record).map(([key, value]) => ({
      key,
      normalizedKey: key.toLowerCase(),
      value
    }));

    for (const candidate of candidates) {
      const normalizedCandidate = candidate.toLowerCase();
      const match = normalizedEntries.find(
        (entry) => entry.normalizedKey === normalizedCandidate && valueIsPresent(entry.value)
      );

      if (match) {
        return { key: match.key, value: match.value };
      }
    }

    return null;
  }

  function getRecordKey(record: GenericRecord, index: number): string {
    const keyField = findField(record, idFields);
    return keyField ? `${keyField.key}-${valueToString(keyField.value)}-${index}` : `record-${index}`;
  }

  function getRecordFieldValue(record: GenericRecord, candidates: string[]): string | null {
    const field = findField(record, candidates);
    return field ? valueToString(field.value) : null;
  }

  function formatFieldLabel(key: string): string {
    return key
      .replace(/^_+/, '')
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }

  function getDetailEntries(record: GenericRecord): [string, unknown][] {
    const fallbackEntries = Object.entries(record).filter(([, value]) => valueIsPresent(value));
    const detailEntries = fallbackEntries.filter(([key]) => !highlightedFields.has(key.toLowerCase()));

    return (detailEntries.length > 0 ? detailEntries : fallbackEntries).slice(0, 6);
  }

  function parseMoney(value: unknown): number | null {
    if (!valueIsPresent(value)) {
      return null;
    }

    const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function getGenericAmount(record: GenericRecord): number | null {
    const amountField = findField(record, amountFields);
    return amountField ? parseMoney(amountField.value) : null;
  }

  function getGenericDateValue(record: GenericRecord): number {
    const dateField = findField(record, dateFields);

    if (!dateField) {
      return 0;
    }

    const value = valueToString(dateField.value);
    const parsed = new Date(value.includes('T') ? value : `${value}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function sortGenericRecords(records: GenericRecord[], mode: SortMode): GenericRecord[] {
    if (mode === 'amount') {
      return [...records].sort((left, right) => (getGenericAmount(right) ?? 0) - (getGenericAmount(left) ?? 0));
    }

    if (mode === 'newest') {
      return [...records].sort((left, right) => getGenericDateValue(right) - getGenericDateValue(left));
    }

    return records;
  }

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : 'Unavailable';
  }

  function benefitsRoute(count: number): string {
    return `/live-view?count=${count}`;
  }
</script>

<svelte:head>
  <title>Analytics | FundRadar</title>
  <meta name="description" content="Browse Business Benefits Finder analytics records in FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="fundradar-dashboard flex h-screen overflow-hidden bg-[#f7f9fb] text-[#191c1e]">
  <nav class="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50 md:flex" aria-label="Workspace navigation">
    <div class="flex h-full flex-col gap-2 p-4">
      <div class="mb-4 flex items-center gap-3 px-2 py-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 font-bold text-white">FR</div>
        <div>
          <h1 class="m-0 font-[Public_Sans] text-xl font-black leading-none tracking-normal text-slate-900">FundRadar</h1>
          <span class="text-xs text-slate-500">Enterprise Funding</span>
        </div>
      </div>

      <div class="flex flex-1 flex-col gap-1">
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/dashboard">
          <span class="material-symbols-outlined">explore</span>
          <span>Discovery</span>
        </a>
        <a class="flex items-center gap-3 rounded-md bg-emerald-50 px-3 py-2.5 text-emerald-700" href="/live-view" aria-current="page">
          <span class="material-symbols-outlined text-emerald-600">insert_chart</span>
          <span>Analytics</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/persona">
          <span class="material-symbols-outlined">business_center</span>
          <span>Company Profile</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/persona/matches">
          <span class="material-symbols-outlined">description</span>
          <span>Opportunity Matches</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/settings">
          <span class="material-symbols-outlined">settings</span>
          <span>Settings</span>
        </a>
      </div>

      <div class="my-4 px-2">
        <a class="block w-full rounded-lg bg-emerald-600 py-2.5 text-center font-semibold text-white hover:bg-emerald-700" href="/persona/matches">
          Find Funding
        </a>
      </div>
    </div>
  </nav>

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <header class="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div class="flex max-w-md flex-1 items-center">
        <div class="relative hidden w-full md:block">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-slate-400">search</span>
          <span class="block w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-sm text-slate-500">
            Analytics records
          </span>
        </div>
        <span class="block text-lg font-bold text-slate-900 md:hidden">FundRadar</span>
      </div>

      <div class="ml-4 flex items-center gap-2 md:gap-4">
        <a class="hidden rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0] sm:inline-flex" href="/dashboard">
          Discovery
        </a>
        <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Notifications">
          <span class="material-symbols-outlined">notifications</span>
        </button>
        <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Help">
          <span class="material-symbols-outlined">help_outline</span>
        </button>
        <div class="ml-2 flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-emerald-700 text-xs font-black text-white">
          FR
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end" aria-labelledby="benefits-heading">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Analytics</p>
            <h2 id="benefits-heading" class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Analytics
            </h2>
            <p class="m-0 max-w-2xl text-base leading-6 text-[#45464d]">
              Review Business Benefits Finder records in the same FundRadar workspace theme.
            </p>
          </div>

          <dl class="grid grid-cols-2 gap-3" aria-label="Business benefit record counts">
            <div class="rounded-xl border border-[#c6c6cd] bg-white px-4 py-3 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Requested</dt>
              <dd class="m-0 mt-1 font-[Public_Sans] text-2xl font-semibold text-[#191c1e]">{formatCount(data.benefits.requested)}</dd>
            </div>
            <div class="rounded-xl border border-[#c6c6cd] bg-white px-4 py-3 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Returned</dt>
              <dd class="m-0 mt-1 font-[Public_Sans] text-2xl font-semibold text-[#191c1e]">{formatCount(data.benefits.count)}</dd>
            </div>
          </dl>
        </section>

        <section class="rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
          <div class="flex flex-col justify-between gap-4 border-b border-[#c6c6cd] p-5 md:flex-row md:items-end">
            <div>
              <h3 class="m-0 text-2xl font-semibold leading-tight text-[#191c1e]">Loaded business benefit records</h3>
              <p class="m-0 mt-2 max-w-2xl text-sm leading-6 text-[#45464d]">
                Source: <span class="break-words font-semibold text-[#191c1e]">{data.benefits.source ?? data.benefits.endpoint}</span>
              </p>
            </div>
            <span class="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
              {cacheHydrated && !loadingBenefits ? 'Synced' : 'Loading'}
            </span>
          </div>

          <div class="p-5">
            {#if !cacheHydrated}
              <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                <h3 class="m-0 text-lg font-semibold text-[#191c1e]">Loading cached benefits</h3>
                <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">Checking local storage before contacting the backend.</p>
              </section>
            {:else if data.benefits.error}
              <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="status">
                <h3 class="m-0 font-semibold">Business Benefits Finder unavailable</h3>
                <p class="m-0 mt-2 leading-6">{data.benefits.error}</p>
              </section>
            {:else if visibleBenefitRecords.length === 0}
              <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No business benefit records returned</h3>
                <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">The Business Benefits Finder endpoint returned an empty record set.</p>
              </section>
            {:else}
              <div class="grid gap-3" role="table" aria-label="Business Benefits Finder records">
                {#each visibleBenefitRecords as record, index (getRecordKey(record, index))}
                  <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition hover:border-[#76777d] hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
                    <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                      <div class="min-w-0">
                        <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">
                          {getRecordFieldValue(record, subtitleFields) ?? 'Record details'}
                        </span>
                        <h3 class="m-0 text-lg font-semibold leading-snug text-[#191c1e]">
                          {getRecordFieldValue(record, titleFields) ?? `Business benefit record ${index + 1}`}
                        </h3>
                      </div>

                      {#if getRecordFieldValue(record, amountFields)}
                        <strong class="shrink-0 font-[Public_Sans] text-xl font-semibold text-[#191c1e]">{getRecordFieldValue(record, amountFields)}</strong>
                      {/if}
                    </div>

                    {#if getRecordFieldValue(record, locationFields)}
                      <p class="m-0 mt-2 text-sm leading-5 text-[#45464d]">{getRecordFieldValue(record, locationFields)}</p>
                    {/if}

                    <dl class="mt-4 grid grid-cols-1 gap-3 border-t border-[#c6c6cd] pt-4 md:grid-cols-3">
                      {#each getDetailEntries(record) as [key, value] (key)}
                        <div>
                          <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">{formatFieldLabel(key)}</dt>
                          <dd class="m-0 mt-1 break-words text-sm leading-5 text-[#191c1e]">{valueToString(value)}</dd>
                        </div>
                      {/each}
                    </dl>
                  </article>
                {/each}
              </div>
            {/if}

            {#if cacheHydrated && !data.benefits.error}
              <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#c6c6cd] pt-4">
                {#if canLoadMoreBenefits}
                  <button
                    class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-wait disabled:opacity-60"
                    type="button"
                    disabled={loadingBenefits}
                    onclick={loadMoreBenefits}
                  >
                    {loadingBenefits ? 'Loading more benefits' : 'Load more benefits'}
                  </button>
                  <p class="m-0 text-sm leading-6 text-[#45464d]">Loads {formatCount(nextBenefitsCount)} business benefit records on this route.</p>
                {:else}
                  <p class="m-0 text-sm leading-6 text-[#45464d]">Benefits count is at the maximum of {formatCount(data.limits.maxCount)}.</p>
                {/if}
              </div>
            {/if}
          </div>
        </section>
      </div>
    </main>
  </div>
</div>

<style>
  .fundradar-dashboard {
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  }

  .material-symbols-outlined {
    display: inline-block;
    overflow-wrap: normal;
    direction: ltr;
    font-family: "Material Symbols Outlined";
    font-feature-settings: "liga";
    font-style: normal;
    font-variation-settings:
      "FILL" 0,
      "wght" 400,
      "GRAD" 0,
      "opsz" 24;
    font-weight: normal;
    letter-spacing: normal;
    line-height: 1;
    text-transform: none;
    white-space: nowrap;
    -webkit-font-feature-settings: "liga";
    -webkit-font-smoothing: antialiased;
  }
</style>
