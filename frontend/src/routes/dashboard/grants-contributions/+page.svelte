<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import {
    type CachedGrantsResult,
    hydrateProgressiveCachedGrantsResult,
    type HydrationProgress
  } from '$lib/client/funding-cache';
  import {
    REVIEW_MATCH_THRESHOLD,
    companyDisplayName,
    createEmptyCompanyProfile,
    hasProfileSignals,
    loadCompanyProfile,
    parseMoney,
    scoreGrantRecord,
    sortScoredRecords,
    type CompanyProfile,
    type ScoredRecord
  } from '$lib/client/company-matching';
  import {
    applySemanticScore,
    fetchSemanticScoresForMatches,
    getSemanticRecordId,
    type SemanticScoreMap
  } from '$lib/client/semantic-scoring';
  import type { PageData } from './$types';

  type GrantRecord = {
    _id: number;
    ref_number: string | null;
    recipient_legal_name: string | null;
    agreement_value: string | null;
    agreement_start_date: string | null;
    agreement_end_date: string | null;
    agreement_title_en?: string | null;
    description_en?: string | null;
    expected_results_en?: string | null;
    prog_name_en: string | null;
    prog_purpose_en?: string | null;
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
  let loadingGrants = $state(true);
  let profileHydrated = $state(false);
  let searchQuery = $state('');
  let selectedProvince = $state('all');
  let minAmount = $state('');
  let maxAmount = $state('');
  let showAllLoadedRecords = $state(false);
  let matchDisplayTarget = $state(50);
  let loadProgress = $state<HydrationProgress>({
    loaded: 0,
    target: 0,
    fromCache: false,
    done: false
  });
  let profile = $state<CompanyProfile>(createEmptyCompanyProfile());
  let semanticScores = $state<SemanticScoreMap>({});
  let hydrationSequence = 0;
  let lastHydratedRequestKey = $state<string | null>(null);

  const MATCH_PAGE_SIZE = 50;
  const MATCH_LOAD_TIMEOUT_MS = 12000;
  const RECORD_SCAN_BATCH_SIZE = 500;
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

  const profileHasSignals = $derived(hasProfileSignals(profile));
  const applicantName = $derived(companyDisplayName(profile));
  const provinceOptions = $derived(getProvinceOptions(data.grantsResult.records));
  const ruleScoredGrantRecords = $derived(data.grantsResult.records.map((grant) => scoreGrantRecord(grant, profile)));
  const scoredGrantRecords = $derived(
    ruleScoredGrantRecords.map((match, index) =>
      applySemanticScore(match, semanticScores[getSemanticRecordId(match.record, 'grants', index)])
    )
  );
  const profileMatchedGrantRecords = $derived(
    profileHasSignals
      ? scoredGrantRecords.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : scoredGrantRecords
  );
  const autoMatchedGrantRecords = $derived(
    profileHasSignals && !showAllLoadedRecords ? profileMatchedGrantRecords : scoredGrantRecords
  );
  const filteredGrantMatches = $derived(filterGrantMatches(autoMatchedGrantRecords));
  const sortedGrantMatches = $derived(sortScoredRecords(filteredGrantMatches, sourceOrder, getGrantDateValueFromRecord));
  const visibleGrantMatches = $derived(sortedGrantMatches.slice(0, matchDisplayTarget));
  const meaningfulMatchCount = $derived(profileMatchedGrantRecords.length);
  const canLoadMoreMatches = $derived(
    cacheHydrated &&
      !loadingGrants &&
      !data.grantsResult.error &&
      (sortedGrantMatches.length > visibleGrantMatches.length || data.grantsResult.records.length < data.limits.maxCount)
  );
  const cacheRequestKey = $derived([data.limits.maxCount, data.grantsResult.endpoint].join('|'));
  const filtersActive = $derived(
    searchQuery.trim().length > 0 ||
      selectedProvince !== 'all' ||
      minAmount.trim().length > 0 ||
      maxAmount.trim().length > 0 ||
      showAllLoadedRecords
  );
  const progressPercent = $derived(getProgressPercent(loadProgress.loaded, loadProgress.target));

  $effect(() => {
    if (!browser) {
      return;
    }

    const requestKey = cacheRequestKey;
    if (requestKey === lastHydratedRequestKey) {
      return;
    }

    void hydratePage(data, requestKey);
  });

  async function hydratePage(snapshot: GrantsPageData, requestKey: string) {
    const sequence = ++hydrationSequence;
    loadingGrants = true;
    cacheHydrated = false;
    profileHydrated = false;
    loadProgress = {
      loaded: 0,
      target: snapshot.limits.maxCount,
      fromCache: false,
      done: false
    };

    const nextProfile = await loadCompanyProfile();
    if (sequence !== hydrationSequence) {
      return;
    }

    profile = nextProfile;
    profileHydrated = true;
    await withLoadingTimeout(loadGrantMatchesUntil(snapshot, nextProfile, MATCH_PAGE_SIZE, sequence));

    if (sequence !== hydrationSequence) {
      return;
    }

    matchDisplayTarget = MATCH_PAGE_SIZE;
    cacheHydrated = true;
    loadingGrants = false;
    lastHydratedRequestKey = requestKey;
    void hydrateSemanticGrantScores(nextProfile, sequence);
  }

  async function loadMoreGrantMatches() {
    if (!browser || loadingGrants || data.grantsResult.error) {
      return;
    }

    const nextTarget = matchDisplayTarget + MATCH_PAGE_SIZE;
    if (sortedGrantMatches.length >= nextTarget) {
      matchDisplayTarget = nextTarget;
      return;
    }

    const sequence = ++hydrationSequence;
    loadingGrants = true;
    await withLoadingTimeout(loadGrantMatchesUntil(data, profile, nextTarget, sequence));

    if (sequence !== hydrationSequence) {
      return;
    }

    matchDisplayTarget = nextTarget;
    loadingGrants = false;
    void hydrateSemanticGrantScores(profile, sequence);
  }

  async function loadGrantMatchesUntil(
    snapshot: GrantsPageData,
    currentProfile: CompanyProfile,
    targetMatches: number,
    sequence: number
  ) {
    let records = snapshot.grantsResult.records;
    let previousRecordCount = -1;

    while (
      getAutoMatchCount(records, currentProfile) < targetMatches &&
      records.length < snapshot.limits.maxCount &&
      sequence === hydrationSequence
    ) {
      const requestedCount = Math.min(
        snapshot.limits.maxCount,
        Math.max(records.length + RECORD_SCAN_BATCH_SIZE, RECORD_SCAN_BATCH_SIZE)
      );
      const result = await hydrateProgressiveCachedGrantsResult(snapshot.grantsResult.endpoint, requestedCount, {
        batchSize: Math.max(snapshot.limits.increment, RECORD_SCAN_BATCH_SIZE),
        onProgress: (progress) => {
          if (sequence === hydrationSequence) {
            loadProgress = {
              ...progress,
              target: snapshot.limits.maxCount
            };
          }
        }
      });

      if (sequence !== hydrationSequence) {
        return;
      }

      records = result.records as GrantRecord[];
      applyGrantsResult(snapshot, { ...result, records });

      if (result.error || records.length <= previousRecordCount) {
        return;
      }

      previousRecordCount = records.length;
    }

    if (records.length === 0) {
      const result = await hydrateProgressiveCachedGrantsResult(snapshot.grantsResult.endpoint, RECORD_SCAN_BATCH_SIZE, {
        batchSize: Math.max(snapshot.limits.increment, RECORD_SCAN_BATCH_SIZE)
      });

      if (sequence === hydrationSequence) {
        applyGrantsResult(snapshot, { ...result, records: result.records as GrantRecord[] });
      }
    }
  }

  function withLoadingTimeout(task: Promise<void>): Promise<void> {
    return Promise.race([
      task,
      new Promise<void>((resolve) => {
        window.setTimeout(resolve, MATCH_LOAD_TIMEOUT_MS);
      })
    ]);
  }

  function applyGrantsResult(snapshot: GrantsPageData, result: CachedGrantsResult) {
    const records = result.records as GrantRecord[];
    data = {
      ...snapshot,
      filters: {
        grantsCount: records.length
      },
      grants: records,
      grantsResult: {
        ...result,
        records
      }
    };
  }

  async function hydrateSemanticGrantScores(currentProfile: CompanyProfile, sequence: number) {
    const ruleMatches = data.grantsResult.records.map((grant) => scoreGrantRecord(grant, currentProfile));
    const candidates = hasProfileSignals(currentProfile)
      ? ruleMatches.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : ruleMatches;
    const scores = await fetchSemanticScoresForMatches(
      getBackendApiUrl(data.grantsResult.endpoint),
      currentProfile,
      candidates,
      'grants'
    );

    if (sequence === hydrationSequence) {
      semanticScores = {
        ...semanticScores,
        ...scores
      };
    }
  }

  function getAutoMatchCount(records: GrantRecord[], currentProfile: CompanyProfile): number {
    const scored = records.map((grant) => scoreGrantRecord(grant, currentProfile));

    if (hasProfileSignals(currentProfile) && !showAllLoadedRecords) {
      return scored.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD).length;
    }

    return scored.length;
  }

  function valueIsPresent(value: unknown): boolean {
    return value !== null && value !== undefined && value !== '';
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

  function normalizeSearchValue(value: unknown): string {
    return valueIsPresent(value) ? String(value).trim().toLowerCase() : '';
  }

  function getGrantSearchText(grant: GrantRecord): string {
    return [
      grant.recipient_legal_name,
      grant.prog_name_en,
      grant.prog_purpose_en,
      grant.agreement_title_en,
      grant.description_en,
      grant.expected_results_en,
      grant.owner_org_title,
      grant.recipient_city,
      grant.recipient_province,
      grant.ref_number
    ]
      .map(normalizeSearchValue)
      .filter(Boolean)
      .join(' ');
  }

  function parseFilterAmount(value: string): number | null {
    const trimmed = value.trim();

    if (!trimmed) {
      return null;
    }

    const parsed = Number(trimmed.replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  }

  function getProvinceOptions(records: GrantRecord[]): string[] {
    return [...new Set(records.map((grant) => grant.recipient_province?.trim()).filter(Boolean) as string[])].sort(
      (left, right) => left.localeCompare(right)
    );
  }

  function filterGrantMatches(matches: ScoredRecord<GrantRecord>[]): ScoredRecord<GrantRecord>[] {
    const query = searchQuery.trim().toLowerCase();
    const minimum = parseFilterAmount(minAmount);
    const maximum = parseFilterAmount(maxAmount);

    return matches.filter((match) => {
      const grant = match.record;
      const text = `${getGrantSearchText(grant)} ${match.reasons.join(' ')} ${match.statusLabel}`.toLowerCase();

      if (query && !text.includes(query)) {
        return false;
      }

      if (selectedProvince !== 'all' && grant.recipient_province?.trim() !== selectedProvince) {
        return false;
      }

      const amount = parseMoney(grant.agreement_value);

      if (minimum !== null && (amount === null || amount < minimum)) {
        return false;
      }

      if (maximum !== null && (amount === null || amount > maximum)) {
        return false;
      }

      return true;
    });
  }

  function resetGrantFilters() {
    searchQuery = '';
    selectedProvince = 'all';
    minAmount = '';
    maxAmount = '';
    showAllLoadedRecords = false;
  }

  function getGrantKey(match: ScoredRecord<GrantRecord>, index: number): string | number {
    return match.record._id ?? match.record.ref_number ?? `grant-${index}`;
  }

  function getBackendApiUrl(endpoint: string): string {
    try {
      return new URL(endpoint, window.location.origin).origin;
    } catch {
      return '';
    }
  }

  function getGrantDateValueFromRecord(grant: GrantRecord): number {
    if (!grant.agreement_start_date) {
      return 0;
    }

    const parsed = new Date(`${grant.agreement_start_date}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function getProgressPercent(loaded: number, target: number): number {
    if (target <= 0) {
      return 0;
    }

    return Math.max(4, Math.min(100, Math.round((loaded / target) * 100)));
  }

  function getToneClass(tone: 'likely' | 'review' | 'low'): string {
    if (tone === 'likely') {
      return 'bg-emerald-50 text-emerald-700';
    }

    if (tone === 'review') {
      return 'bg-amber-50 text-amber-800';
    }

    return 'bg-slate-100 text-slate-600';
  }
</script>

<svelte:head>
  <title>Grants and Contributions | FundRadar</title>
  <meta name="description" content="Browse historical grants and contributions matched to your company profile." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="grants" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search grants, recipients, programs, or workspace pages..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end" aria-labelledby="grants-heading">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Grants and Contributions</p>
            <h2 id="grants-heading" class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Grants and Contributions
            </h2>
            <p class="m-0 max-w-3xl text-base leading-6 text-[#45464d]">
              Auto-loaded Open Canada award records filtered to historical recipients and programs similar to {applicantName}.
            </p>
          </div>
        </section>

        <section class="mb-6 grid grid-cols-1 gap-4 md:max-w-sm" aria-label="Grant match summary">
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Profile matches</span>
            <strong class="mt-1 block font-[Public_Sans] text-3xl font-semibold text-[#191c1e]">{formatCount(meaningfulMatchCount)}</strong>
          </article>
        </section>

        {#if !profileHydrated || !cacheHydrated}
          <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" role="status">
            <div class="mx-auto max-w-2xl text-center">
              <span class="material-symbols-outlined mb-3 rounded-xl bg-emerald-50 p-3 text-3xl text-emerald-700">manage_search</span>
              <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Loading similar historical businesses</h3>
              <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">
                Searching Open Canada grant records for company-profile matches, then caching results in this browser.
              </p>
              <div class="mt-5 h-3 overflow-hidden rounded-full bg-[#eceef0]">
                <div class="h-full rounded-full bg-emerald-600 transition-all" style={`width: ${progressPercent}%;`}></div>
              </div>
              <p class="m-0 mt-3 text-sm font-semibold text-[#45464d]">
                {loadProgress.fromCache ? 'Using cached funding records.' : 'Searching the funding record index.'}
              </p>
            </div>
          </section>
        {:else}
          {#if !profileHasSignals}
            <section class="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
              <h3 class="m-0 font-semibold">Company profile needed for auto-filtering</h3>
              <p class="m-0 mt-2 leading-6">
                Add industry, location, keywords, and funding needs to filter historical records to businesses similar to yours.
                <a class="font-semibold text-amber-950 underline" href="/dashboard/persona">Complete Company Profile</a>
              </p>
            </section>
          {/if}

          <section class="rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <div class="flex flex-col justify-between gap-4 border-b border-[#c6c6cd] p-5 md:flex-row md:items-end">
              <div>
                <h3 class="m-0 text-2xl font-semibold leading-tight text-[#191c1e]">Similar historical recipients</h3>
                <p class="m-0 mt-2 max-w-2xl text-sm leading-6 text-[#45464d]">
                  Awarded grant records are ranked by profile keywords, location, applicant type, and funding size.
                </p>
              </div>
              <span class="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                {loadingGrants ? 'Loading' : 'Ready'}
              </span>
            </div>

            <div class="p-5">
              {#if !data.grantsResult.error}
                <section class="mb-5 rounded-xl border border-[#c6c6cd] bg-[#f7f9fb] p-4" aria-label="Search and filter grant matches">
                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(220px,1fr)_180px_150px_150px_auto] lg:items-end">
                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Search matches</span>
                      <input
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm text-[#191c1e] outline-none transition placeholder:text-[#76777d] focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        type="search"
                        bind:value={searchQuery}
                        placeholder="Recipient, program, city, reference..."
                      />
                    </label>

                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Province</span>
                      <select
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm text-[#191c1e] outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        bind:value={selectedProvince}
                      >
                        <option value="all">All provinces</option>
                        {#each provinceOptions as province}
                          <option value={province}>{province}</option>
                        {/each}
                      </select>
                    </label>

                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Min amount</span>
                      <input
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm text-[#191c1e] outline-none transition placeholder:text-[#76777d] focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        type="text"
                        inputmode="decimal"
                        bind:value={minAmount}
                        placeholder="$0"
                      />
                    </label>

                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Max amount</span>
                      <input
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm text-[#191c1e] outline-none transition placeholder:text-[#76777d] focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        type="text"
                        inputmode="decimal"
                        bind:value={maxAmount}
                        placeholder="No limit"
                      />
                    </label>

                    <button
                      class="h-11 rounded-lg border-2 border-[#c6c6cd] px-4 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      disabled={!filtersActive}
                      onclick={resetGrantFilters}
                    >
                      Reset
                    </button>
                  </div>

                  <label class="mt-4 flex cursor-pointer items-center gap-2 text-sm font-semibold text-[#45464d]">
                    <input class="h-4 w-4 rounded border-[#c6c6cd] text-emerald-700 focus:ring-emerald-700" type="checkbox" bind:checked={showAllLoadedRecords} />
                    Show all loaded historical records instead of only profile matches.
                  </label>
                </section>
              {/if}

              {#if data.grantsResult.error}
                <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="status">
                  <h3 class="m-0 font-semibold">Grants unavailable</h3>
                  <p class="m-0 mt-2 leading-6">{data.grantsResult.error}</p>
                </section>
              {:else if data.grantsResult.records.length === 0}
                <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                  <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No grants returned</h3>
                  <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">No Open Canada grant records are available for this selection.</p>
                </section>
              {:else if visibleGrantMatches.length === 0}
                <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                  <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No similar historical records</h3>
                  <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">Show all loaded records or adjust the search, province, and amount filters.</p>
                </section>
              {:else}
                <section class="grid grid-cols-1 gap-4 md:grid-cols-2" aria-label="Matched grant records">
                  {#each visibleGrantMatches as match, index (getGrantKey(match, index))}
                    {@const grant = match.record}
                    <article class="group flex flex-col rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition hover:border-[#76777d] hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
                      <div class="mb-4 flex items-start justify-between gap-4">
                        <div class="min-w-0">
                          <span class="mb-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-normal {getToneClass(match.statusTone)}">
                            {match.matchScore}% · {match.statusLabel}
                          </span>
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
                          <span class="text-xs font-semibold uppercase tracking-normal text-[#76777d]">Awarded value</span>
                        </div>
                      </div>

                      <dl class="grid grid-cols-1 gap-3 border-t border-[#c6c6cd] pt-4 sm:grid-cols-2">
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
                      </dl>

                      <div class="mt-4 border-t border-[#c6c6cd] pt-4">
                        <p class="m-0 text-xs font-semibold uppercase tracking-normal text-[#45464d]">Why it matched</p>
                        <ul class="m-0 mt-2 grid gap-1 pl-4 text-sm leading-5 text-[#45464d]">
                          {#each match.reasons.slice(0, 2) as reason}
                            <li>{reason}</li>
                          {/each}
                        </ul>
                      </div>
                    </article>
                  {/each}
                </section>
              {/if}

              {#if !data.grantsResult.error}
                <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#c6c6cd] pt-4">
                  <p class="m-0 text-sm leading-6 text-[#45464d]">
                    Showing matching grant records found so far.
                  </p>
                  <div class="flex flex-wrap gap-3">
                    {#if canLoadMoreMatches}
                      <button
                        class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-wait disabled:opacity-60"
                        type="button"
                        disabled={loadingGrants}
                        onclick={loadMoreGrantMatches}
                      >
                        {loadingGrants ? 'Finding more matches' : 'Load another 50 matches'}
                      </button>
                    {/if}
                    <a class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] no-underline transition hover:border-[#0b1c30] hover:bg-[#eceef0]" href="/dashboard/persona">
                      Update Company Profile
                    </a>
                  </div>
                </div>
              {/if}
            </div>
          </section>
        {/if}
      </div>
    </main>
  </div>
</div>
