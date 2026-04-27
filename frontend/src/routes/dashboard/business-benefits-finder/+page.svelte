<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import {
    hydrateProgressiveCachedBenefitsResult,
    type HydrationProgress
  } from '$lib/client/funding-cache';
  import {
    fetchBusinessBenefitsFeedState,
    getBusinessBenefitsFeedMarker,
    readStoredBusinessBenefitsFeedState,
    readStoredStringList,
    shouldRefreshBusinessBenefitsCache,
    writeStoredBusinessBenefitsFeedState,
    writeStoredStringList
  } from '$lib/client/business-benefits-updates';
  import {
    LIKELY_MATCH_THRESHOLD,
    REVIEW_MATCH_THRESHOLD,
    companyDisplayName,
    createEmptyCompanyProfile,
    hasProfileSignals,
    isCurrentlyAvailableRecord,
    loadCompanyProfile,
    scoreBenefitRecord,
    sortScoredRecords,
    type CompanyProfile,
    type GenericRecord,
    type ScoredRecord
  } from '$lib/client/company-matching';
  import {
    applySemanticScore,
    fetchSemanticScoresForMatches,
    getSemanticRecordId,
    type SemanticScoreMap
  } from '$lib/client/semantic-scoring';
  import type { PageData } from './$types';

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
  type PresenceFilter = 'all' | 'hasAmount' | 'hasDate';
  type FilterFieldOption = {
    key: string;
    label: string;
    count: number;
  };

  let { data }: { data: BenefitsPageData } = $props();
  let cacheHydrated = $state(false);
  let loadingBenefits = $state(true);
  let profileHydrated = $state(false);
  let searchQuery = $state('');
  let selectedFieldKey = $state('all');
  let presenceFilter = $state<PresenceFilter>('all');
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
  let newLikelyBenefitCount = $state(0);

  const MATCH_PAGE_SIZE = 50;
  const MATCH_LOAD_TIMEOUT_MS = 12000;
  const RECORD_SCAN_BATCH_SIZE = 500;
  const DEFAULT_BACKEND_API_URL = '';
  const LIKELY_BENEFIT_REFS_STORAGE_KEY = 'fundradar.businessBenefitsFinderLikelyRefs.v1';
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
    'status',
    'category'
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

  const profileHasSignals = $derived(hasProfileSignals(profile));
  const applicantName = $derived(companyDisplayName(profile));
  const currentBenefitRecords = $derived(data.benefits.records.filter(isCurrentlyAvailableRecord));
  const availableFilterFields = $derived(getAvailableFilterFields(currentBenefitRecords));
  const ruleScoredBenefitRecords = $derived(currentBenefitRecords.map((record) => scoreBenefitRecord(record, profile)));
  const scoredBenefitRecords = $derived(
    ruleScoredBenefitRecords.map((match, index) =>
      applySemanticScore(match, semanticScores[getSemanticRecordId(match.record, 'business-benefits', index)])
    )
  );
  const profileMatchedBenefitRecords = $derived(
    profileHasSignals
      ? scoredBenefitRecords.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : scoredBenefitRecords
  );
  const autoMatchedBenefitRecords = $derived(
    profileHasSignals && !showAllLoadedRecords ? profileMatchedBenefitRecords : scoredBenefitRecords
  );
  const filteredBenefitMatches = $derived(filterBenefitMatches(autoMatchedBenefitRecords));
  const sortedBenefitMatches = $derived(sortScoredRecords(filteredBenefitMatches, sourceOrder, getGenericDateValue));
  const visibleBenefitMatches = $derived(sortedBenefitMatches.slice(0, matchDisplayTarget));
  const meaningfulMatchCount = $derived(profileMatchedBenefitRecords.length);
  const canLoadMoreMatches = $derived(
    cacheHydrated &&
      !loadingBenefits &&
      !data.benefits.error &&
      (sortedBenefitMatches.length > visibleBenefitMatches.length || data.benefits.records.length < data.limits.maxCount)
  );
  const cacheRequestKey = $derived([data.limits.maxCount, data.benefits.endpoint].join('|'));
  const hasActiveFilters = $derived(
    searchQuery.trim() !== '' || selectedFieldKey !== 'all' || presenceFilter !== 'all' || showAllLoadedRecords
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

  async function hydratePage(snapshot: BenefitsPageData, requestKey: string) {
    const sequence = ++hydrationSequence;
    loadingBenefits = true;
    cacheHydrated = false;
    profileHydrated = false;
    loadProgress = {
      loaded: 0,
      target: snapshot.limits.maxCount,
      fromCache: false,
      done: false
    };

    const [nextProfile, feedState] = await Promise.all([
      loadCompanyProfile(),
      fetchBusinessBenefitsFeedState(getBackendApiUrl(snapshot.benefits.endpoint))
    ]);
    if (sequence !== hydrationSequence) {
      return;
    }

    const previousFeedState = readStoredBusinessBenefitsFeedState();
    const forceBenefitsRefresh = shouldRefreshBusinessBenefitsCache(previousFeedState, feedState);
    const canReportNewFeedMatches = forceBenefitsRefresh && getBusinessBenefitsFeedMarker(previousFeedState) !== null;
    profile = nextProfile;
    profileHydrated = true;
    const benefitsHydrated = await withLoadingTimeout(
      loadBenefitMatchesUntil(snapshot, nextProfile, MATCH_PAGE_SIZE, sequence, forceBenefitsRefresh)
    );

    if (sequence !== hydrationSequence) {
      return;
    }

    if (feedState && (!forceBenefitsRefresh || benefitsHydrated)) {
      writeStoredBusinessBenefitsFeedState(feedState);
    }
    if (benefitsHydrated) {
      updateLikelyBenefitNotice(nextProfile, canReportNewFeedMatches);
    }
    matchDisplayTarget = MATCH_PAGE_SIZE;
    cacheHydrated = true;
    loadingBenefits = false;
    lastHydratedRequestKey = requestKey;
    void hydrateSemanticBenefitScores(nextProfile, sequence);
  }

  async function loadMoreBenefitMatches() {
    if (!browser || loadingBenefits || data.benefits.error) {
      return;
    }

    const nextTarget = matchDisplayTarget + MATCH_PAGE_SIZE;
    if (sortedBenefitMatches.length >= nextTarget) {
      matchDisplayTarget = nextTarget;
      return;
    }

    const sequence = ++hydrationSequence;
    loadingBenefits = true;
    await withLoadingTimeout(loadBenefitMatchesUntil(data, profile, nextTarget, sequence));

    if (sequence !== hydrationSequence) {
      return;
    }

    matchDisplayTarget = nextTarget;
    loadingBenefits = false;
    void hydrateSemanticBenefitScores(profile, sequence);
  }

  async function loadBenefitMatchesUntil(
    snapshot: BenefitsPageData,
    currentProfile: CompanyProfile,
    targetMatches: number,
    sequence: number,
    forceRefresh = false
  ) {
    let records = forceRefresh ? [] : snapshot.benefits.records;
    let previousRecordCount = -1;
    let shouldForceRefresh = forceRefresh;

    while (
      getAutoMatchCount(records, currentProfile) < targetMatches &&
      records.length < snapshot.limits.maxCount &&
      sequence === hydrationSequence
    ) {
      const requestedCount = Math.min(
        snapshot.limits.maxCount,
        Math.max(records.length + RECORD_SCAN_BATCH_SIZE, RECORD_SCAN_BATCH_SIZE)
      );
      const benefits = await hydrateProgressiveCachedBenefitsResult(snapshot.benefits.endpoint, requestedCount, {
        forceRefresh: shouldForceRefresh,
        onProgress: (progress) => {
          if (sequence === hydrationSequence) {
            loadProgress = {
              ...progress,
              target: snapshot.limits.maxCount
            };
          }
        }
      });
      shouldForceRefresh = false;

      if (sequence !== hydrationSequence) {
        return;
      }

      records = benefits.records;
      applyBenefitsResult(snapshot, benefits);

      if (benefits.error || records.length <= previousRecordCount) {
        return;
      }

      previousRecordCount = records.length;
    }

    if (records.length === 0) {
      const benefits = await hydrateProgressiveCachedBenefitsResult(snapshot.benefits.endpoint, RECORD_SCAN_BATCH_SIZE, {
        forceRefresh: shouldForceRefresh
      });

      if (sequence === hydrationSequence) {
        applyBenefitsResult(snapshot, benefits);
      }
    }
  }

  function withLoadingTimeout(task: Promise<void>): Promise<boolean> {
    return Promise.race([
      task.then(() => true),
      new Promise<boolean>((resolve) => {
        window.setTimeout(() => resolve(false), MATCH_LOAD_TIMEOUT_MS);
      })
    ]);
  }

  function applyBenefitsResult(snapshot: BenefitsPageData, benefits: BenefitsPageData['benefits']) {
    data = {
      ...snapshot,
      filters: {
        benefitsCount: benefits.records.length
      },
      benefits
    };
  }

  async function hydrateSemanticBenefitScores(currentProfile: CompanyProfile, sequence: number) {
    const ruleMatches = data.benefits.records
      .filter(isCurrentlyAvailableRecord)
      .map((record) => scoreBenefitRecord(record, currentProfile));
    const candidates = hasProfileSignals(currentProfile)
      ? ruleMatches.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : ruleMatches;
    const scores = await fetchSemanticScoresForMatches(
      getBackendApiUrl(data.benefits.endpoint),
      currentProfile,
      candidates,
      'business-benefits'
    );

    if (sequence === hydrationSequence) {
      semanticScores = {
        ...semanticScores,
        ...scores
      };
    }
  }

  function getAutoMatchCount(records: GenericRecord[], currentProfile: CompanyProfile): number {
    const currentRecords = records.filter(isCurrentlyAvailableRecord);
    const scored = currentRecords.map((record) => scoreBenefitRecord(record, currentProfile));

    if (hasProfileSignals(currentProfile) && !showAllLoadedRecords) {
      return scored.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD).length;
    }

    return scored.length;
  }

  function updateLikelyBenefitNotice(currentProfile: CompanyProfile, canReportNewFeedMatches: boolean) {
    const currentLikelyRefs = data.benefits.records
      .filter(isCurrentlyAvailableRecord)
      .map((record) => scoreBenefitRecord(record, currentProfile))
      .filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD)
      .map((match) => getBenefitRecordRef(match.record))
      .filter((value): value is string => value !== null);
    const previousLikelyRefs = readStoredStringList(LIKELY_BENEFIT_REFS_STORAGE_KEY);
    const previousSet = new Set(previousLikelyRefs);

    newLikelyBenefitCount =
      canReportNewFeedMatches && previousLikelyRefs.length > 0
        ? currentLikelyRefs.filter((ref) => !previousSet.has(ref)).length
        : 0;
    writeStoredStringList(LIKELY_BENEFIT_REFS_STORAGE_KEY, currentLikelyRefs);
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

  function valueToSearchText(value: unknown): string {
    if (!valueIsPresent(value)) {
      return '';
    }

    if (Array.isArray(value)) {
      return value.map(valueToSearchText).join(' ');
    }

    if (typeof value === 'object') {
      return Object.entries(value as GenericRecord)
        .map(([key, nestedValue]) => `${key} ${valueToSearchText(nestedValue)}`)
        .join(' ');
    }

    return valueToString(value);
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

  function getRecordKey(match: ScoredRecord<GenericRecord>, index: number): string {
    const keyField = findField(match.record, idFields);
    return keyField ? `${keyField.key}-${valueToString(keyField.value)}-${index}` : `record-${index}`;
  }

  function getBenefitRecordRef(record: GenericRecord): string | null {
    const keyField = findField(record, idFields);
    if (keyField) {
      return `${keyField.key}:${valueToString(keyField.value)}`;
    }

    const title = getRecordFieldValue(record, titleFields);
    const sponsor = getRecordFieldValue(record, subtitleFields);
    return title ? `title:${title}|${sponsor ?? ''}` : null;
  }

  function getBackendApiUrl(endpoint: string): string {
    try {
      return new URL(endpoint).origin;
    } catch {
      return DEFAULT_BACKEND_API_URL;
    }
  }

  function getRecordFieldValue(record: GenericRecord, candidates: string[]): string | null {
    const field = findField(record, candidates);
    return field ? valueToString(field.value) : null;
  }

  function getRecordFieldSearchValue(record: GenericRecord, candidates: string[]): string {
    const field = findField(record, candidates);
    return field ? valueToSearchText(field.value) : '';
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

  function getAvailableFilterFields(records: GenericRecord[]): FilterFieldOption[] {
    const keyCounts = new Map<string, { label: string; count: number }>();

    for (const record of records) {
      for (const [key, value] of Object.entries(record)) {
        if (!valueIsPresent(value)) {
          continue;
        }

        const normalizedKey = key.toLowerCase();
        const current = keyCounts.get(normalizedKey);

        keyCounts.set(normalizedKey, {
          label: current?.label ?? formatFieldLabel(key),
          count: (current?.count ?? 0) + 1
        });
      }
    }

    return [...keyCounts.entries()]
      .map(([key, value]) => ({ key, label: value.label, count: value.count }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
      .slice(0, 30);
  }

  function getRecordSearchText(record: GenericRecord): string {
    const genericText = Object.entries(record)
      .map(([key, value]) => `${formatFieldLabel(key)} ${key} ${valueToSearchText(value)}`)
      .join(' ');
    const displayedText = [
      getRecordFieldSearchValue(record, titleFields),
      getRecordFieldSearchValue(record, subtitleFields),
      getRecordFieldSearchValue(record, amountFields),
      getRecordFieldSearchValue(record, locationFields),
      getRecordFieldSearchValue(record, dateFields)
    ].join(' ');

    return `${displayedText} ${genericText}`.toLowerCase();
  }

  function recordMatchesField(record: GenericRecord, fieldKey: string): boolean {
    if (fieldKey === 'all') {
      return true;
    }

    return Object.entries(record).some(([key, value]) => key.toLowerCase() === fieldKey && valueIsPresent(value));
  }

  function recordMatchesPresenceFilter(record: GenericRecord, filter: PresenceFilter): boolean {
    if (filter === 'hasAmount') {
      return getGenericAmount(record) !== null;
    }

    if (filter === 'hasDate') {
      return getGenericDateValue(record) > 0;
    }

    return true;
  }

  function recordMatchesSearch(record: GenericRecord, query: string, fieldKey: string, match: ScoredRecord<GenericRecord>): boolean {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return true;
    }

    if (fieldKey !== 'all') {
      return Object.entries(record).some(
        ([key, value]) => key.toLowerCase() === fieldKey && valueToSearchText(value).toLowerCase().includes(normalizedQuery)
      );
    }

    return `${getRecordSearchText(record)} ${match.reasons.join(' ')} ${match.statusLabel}`.toLowerCase().includes(normalizedQuery);
  }

  function filterBenefitMatches(matches: ScoredRecord<GenericRecord>[]): ScoredRecord<GenericRecord>[] {
    return matches.filter(
      (match) =>
        recordMatchesField(match.record, selectedFieldKey) &&
        recordMatchesPresenceFilter(match.record, presenceFilter) &&
        recordMatchesSearch(match.record, searchQuery, selectedFieldKey, match)
    );
  }

  function clearBenefitFilters() {
    searchQuery = '';
    selectedFieldKey = 'all';
    presenceFilter = 'all';
    showAllLoadedRecords = false;
  }

  function getGenericAmount(record: GenericRecord): number | null {
    for (const [key, value] of Object.entries(record)) {
      if (/amount|funding|contribution|grant|loan|value/i.test(key)) {
        const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
        if (Number.isFinite(parsed) && parsed > 0) {
          return parsed;
        }
      }
    }

    return null;
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

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : 'Unavailable';
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
  <title>Business Benefits Finder | FundRadar</title>
  <meta name="description" content="Browse currently available Business Benefits Finder records matched to your company profile." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="benefits" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search benefits, programs, or workspace pages..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end" aria-labelledby="benefits-heading">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Current Opportunity Feed</p>
            <h2 id="benefits-heading" class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Business Benefits Finder
            </h2>
            <p class="m-0 max-w-3xl text-base leading-6 text-[#45464d]">
              Auto-loaded Innovation Canada programs filtered to currently available opportunities for {applicantName}.
            </p>
          </div>
        </section>

        <section class="mb-6 grid grid-cols-1 gap-4 md:max-w-sm" aria-label="Business benefit match summary">
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">Profile matches</span>
            <strong class="mt-1 block font-[Public_Sans] text-3xl font-semibold text-[#191c1e]">{formatCount(meaningfulMatchCount)}</strong>
          </article>
        </section>

        {#if !profileHydrated || !cacheHydrated}
          <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" role="status">
            <div class="mx-auto max-w-2xl text-center">
              <span class="material-symbols-outlined mb-3 rounded-xl bg-emerald-50 p-3 text-3xl text-emerald-700">radar</span>
              <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Loading current opportunities</h3>
              <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">
                Searching Business Benefits Finder records for company-profile matches, then caching results in this browser.
              </p>
              <div class="mt-5 h-3 overflow-hidden rounded-full bg-[#eceef0]">
                <div class="h-full rounded-full bg-emerald-600 transition-all" style={`width: ${progressPercent}%;`}></div>
              </div>
              <p class="m-0 mt-3 text-sm font-semibold text-[#45464d]">
                {loadProgress.fromCache ? 'Using cached benefit records.' : 'Searching the benefit record index.'}
              </p>
            </div>
          </section>
        {:else}
          {#if !profileHasSignals}
            <section class="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
              <h3 class="m-0 font-semibold">Company profile needed for auto-filtering</h3>
              <p class="m-0 mt-2 leading-6">
                Add industry, location, keywords, and funding needs to rank currently available opportunities for your company.
                <a class="font-semibold text-amber-950 underline" href="/dashboard/persona">Complete Company Profile</a>
              </p>
            </section>
          {/if}

          {#if newLikelyBenefitCount > 0}
            <section class="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950" role="status">
              <h3 class="m-0 font-semibold">New likely opportunities found</h3>
              <p class="m-0 mt-2 leading-6">
                The Business Benefits Finder feed changed, so FundRadar refreshed the cache and found {newLikelyBenefitCount}
                newly likely {newLikelyBenefitCount === 1 ? 'match' : 'matches'} for {applicantName}.
              </p>
            </section>
          {/if}

          <section class="rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <div class="flex flex-col justify-between gap-4 border-b border-[#c6c6cd] p-5 md:flex-row md:items-end">
              <div>
                <h3 class="m-0 text-2xl font-semibold leading-tight text-[#191c1e]">Available opportunity matches</h3>
                <p class="m-0 mt-2 max-w-2xl text-sm leading-6 text-[#45464d]">
                  Current programs are ranked by profile keywords, applicant type, location signals, and funding context.
                </p>
              </div>
              <span class="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                {loadingBenefits ? 'Loading' : 'Ready'}
              </span>
            </div>

            <div class="p-5">
              {#if !data.benefits.error}
                <section class="mb-4 rounded-xl border border-[#c6c6cd] bg-[#f7f9fb] p-4" aria-label="Business benefit search and filters">
                  <div class="grid gap-3 lg:grid-cols-[minmax(240px,1fr)_minmax(180px,260px)_minmax(180px,240px)_auto] lg:items-end">
                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Search records</span>
                      <input
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm text-[#191c1e] outline-none transition placeholder:text-[#76777d] focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        type="search"
                        bind:value={searchQuery}
                        placeholder="Search titles, descriptions, profile reasons, keys, or values"
                      />
                    </label>

                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Record field</span>
                      <select
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm font-semibold text-[#191c1e] outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        bind:value={selectedFieldKey}
                      >
                        <option value="all">All available fields</option>
                        {#each availableFilterFields as field (field.key)}
                          <option value={field.key}>{field.label}</option>
                        {/each}
                      </select>
                    </label>

                    <label class="block">
                      <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Presence</span>
                      <select
                        class="h-11 w-full rounded-lg border border-[#c6c6cd] bg-white px-3 text-sm font-semibold text-[#191c1e] outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        bind:value={presenceFilter}
                      >
                        <option value="all">Any record</option>
                        <option value="hasAmount">Has amount</option>
                        <option value="hasDate">Has date</option>
                      </select>
                    </label>

                    <button
                      class="h-11 rounded-lg border-2 border-[#c6c6cd] px-4 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      disabled={!hasActiveFilters}
                      onclick={clearBenefitFilters}
                    >
                      Clear filters
                    </button>
                  </div>

                  <label class="mt-4 flex cursor-pointer items-center gap-2 text-sm font-semibold text-[#45464d]">
                    <input class="h-4 w-4 rounded border-[#c6c6cd] text-emerald-700 focus:ring-emerald-700" type="checkbox" bind:checked={showAllLoadedRecords} />
                    Show all currently available records instead of only profile matches.
                  </label>
                </section>
              {/if}

              {#if data.benefits.error}
                <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="status">
                  <h3 class="m-0 font-semibold">Business Benefits Finder unavailable</h3>
                  <p class="m-0 mt-2 leading-6">{data.benefits.error}</p>
                </section>
              {:else if data.benefits.records.length === 0}
                <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                  <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No business benefit records returned</h3>
                  <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">No programs are available for this selection.</p>
                </section>
              {:else if visibleBenefitMatches.length === 0}
                <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
                  <h3 class="m-0 text-lg font-semibold text-[#191c1e]">No available records match these filters</h3>
                  <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">Show all available records or adjust the search and field filters.</p>
                </section>
              {:else}
                <div class="grid gap-3" role="table" aria-label="Business Benefits Finder records">
                  {#each visibleBenefitMatches as match, index (getRecordKey(match, index))}
                    {@const record = match.record}
                    <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition hover:border-[#76777d] hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
                      <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                        <div class="min-w-0">
                          <span class="mb-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-normal {getToneClass(match.statusTone)}">
                            {match.matchScore}% · {match.statusLabel}
                          </span>
                          <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">
                            {getRecordFieldValue(record, subtitleFields) ?? 'Available program'}
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

                      <div class="mt-4 rounded-lg bg-[#f7f9fb] p-3">
                        <p class="m-0 text-xs font-semibold uppercase tracking-normal text-[#45464d]">Why it matched</p>
                        <ul class="m-0 mt-2 grid gap-1 pl-4 text-sm leading-5 text-[#45464d]">
                          {#each match.reasons.slice(0, 2) as reason}
                            <li>{reason}</li>
                          {/each}
                        </ul>
                      </div>

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

              {#if !data.benefits.error}
                <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#c6c6cd] pt-4">
                  <p class="m-0 text-sm leading-6 text-[#45464d]">
                    Showing matching current opportunities found so far.
                  </p>
                  <div class="flex flex-wrap gap-3">
                    {#if canLoadMoreMatches}
                      <button
                        class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-wait disabled:opacity-60"
                        type="button"
                        disabled={loadingBenefits}
                        onclick={loadMoreBenefitMatches}
                      >
                        {loadingBenefits ? 'Finding more matches' : 'Load another 50 matches'}
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
