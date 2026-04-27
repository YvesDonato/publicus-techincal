<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import { pushState } from '$app/navigation';
  import { hydrateCachedFundingData } from '$lib/client/funding-cache';
  import {
    REVIEW_MATCH_THRESHOLD,
    createEmptyCompanyProfile,
    hasProfileSignals,
    loadCompanyProfile,
    scoreBenefitRecord,
    scoreGrantRecord,
    type CompanyProfile,
    type ScoredRecord
  } from '$lib/client/company-matching';
  import type { PageData } from './$types';

  type GenericRecord = Record<string, unknown>;
  type FieldMatch = {
    key: string;
    value: unknown;
  };
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
  type FundingPageData = PageData & {
    filters: {
      grantsCount: number;
      benefitsCount: number;
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
    benefits: {
      requested: number;
      count: number;
      records: GenericRecord[];
      source: string | null;
      endpoint: string;
      error: string | null;
    };
  };
  type ChartBar = {
    label: string;
    value: number;
    detail?: string;
  };
  type AnalyticsSummary = {
    amountBySource: ChartBar[];
    benefitCategoryBars: ChartBar[];
    benefitKnownAmountCount: number;
    benefitTotalAmount: number;
    combinedTotalAmount: number;
    datasetMixBars: ChartBar[];
    grantKnownAmountCount: number;
    grantProgramBars: ChartBar[];
    grantProvinceBars: ChartBar[];
    grantTotalAmount: number;
    trendBars: ChartBar[];
    totalBenefitRecords: number;
    totalGrantRecords: number;
    totalRecords: number;
  };

  let { data }: { data: FundingPageData } = $props();
  let cacheHydrated = $state(false);
  let profileHydrated = $state(false);
  let loadingAnalytics = $state(false);
  let profile = $state<CompanyProfile>(createEmptyCompanyProfile());
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
  const dateFields = [
    'agreement_start_date',
    'start_date',
    'end_date',
    'date',
    'created_at',
    'updated_at',
    'modified'
  ];
  const moneyFormatter = new Intl.NumberFormat('en-CA', {
    currency: 'CAD',
    maximumFractionDigits: 0,
    style: 'currency'
  });
  const compactMoneyFormatter = new Intl.NumberFormat('en-CA', {
    currency: 'CAD',
    maximumFractionDigits: 1,
    notation: 'compact',
    style: 'currency'
  });

  const profileHasSignals = $derived(hasProfileSignals(profile));
  const scoredGrantRecords = $derived(data.grantsResult.records.map((grant) => scoreGrantRecord(grant, profile)));
  const scoredBenefitRecords = $derived(data.benefits.records.map((record) => scoreBenefitRecord(record, profile)));
  const matchedGrantRecords = $derived(
    profileHasSignals
      ? scoredGrantRecords.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : []
  );
  const matchedBenefitRecords = $derived(
    profileHasSignals
      ? scoredBenefitRecords.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD)
      : []
  );
  const analytics = $derived(
    buildAnalytics(matchedGrantRecords, matchedBenefitRecords, data.filters.grantsCount, data.filters.benefitsCount)
  );
  const maxAmountBySource = $derived(getMaximumValue(analytics.amountBySource));
  const maxDatasetCount = $derived(getMaximumValue(analytics.datasetMixBars));
  const maxProvinceCount = $derived(getMaximumValue(analytics.grantProvinceBars));
  const maxBenefitCategoryCount = $derived(getMaximumValue(analytics.benefitCategoryBars));
  const maxGrantProgramAmount = $derived(getMaximumValue(analytics.grantProgramBars));
  const maxTrendCount = $derived(getMaximumValue(analytics.trendBars));
  const nextGrantsCount = $derived(Math.min(data.limits.maxCount, data.filters.grantsCount + data.limits.increment));
  const nextBenefitsCount = $derived(Math.min(data.limits.maxCount, data.filters.benefitsCount + data.limits.increment));
  const canLoadMoreAnalytics = $derived(
    data.filters.grantsCount < data.limits.maxCount || data.filters.benefitsCount < data.limits.maxCount
  );
  const cacheRequestKey = $derived(getFundingRequestKey(data));

  $effect(() => {
    if (!browser) {
      return;
    }

    const requestKey = cacheRequestKey;
    if (requestKey === lastHydratedRequestKey) {
      return;
    }

    void hydrateFunding(data, requestKey);
  });

  async function hydrateFunding(snapshot: FundingPageData, requestKey = getFundingRequestKey(snapshot)) {
    const sequence = ++hydrationSequence;
    cacheHydrated = false;
    profileHydrated = false;
    const [hydrated, nextProfile] = await Promise.all([hydrateCachedFundingData(snapshot), loadCompanyProfile()]);

    if (sequence !== hydrationSequence) {
      return;
    }

    const grantsResult = {
      ...hydrated.grantsResult,
      records: hydrated.grantsResult.records as GrantRecord[]
    };

    data = {
      ...hydrated,
      grants: grantsResult.records,
      grantsResult
    } as FundingPageData;
    profile = nextProfile;
    cacheHydrated = true;
    profileHydrated = true;
    lastHydratedRequestKey = requestKey;
    loadingAnalytics = false;
  }

  async function loadMoreAnalytics() {
    if (!browser || loadingAnalytics || !canLoadMoreAnalytics) {
      return;
    }

    const grantsCount = nextGrantsCount;
    const benefitsCount = nextBenefitsCount;
    const nextData = buildFundingSnapshot(grantsCount, benefitsCount);

    loadingAnalytics = true;
    pushState(liveViewRoute(grantsCount, benefitsCount), {});
    await hydrateFunding(nextData);
  }

  function buildFundingSnapshot(grantsCount: number, benefitsCount: number): FundingPageData {
    return {
      ...data,
      filters: {
        grantsCount,
        benefitsCount
      },
      grantsResult: {
        ...data.grantsResult,
        requested: grantsCount,
        endpoint: updateGrantsEndpoint(data.grantsResult.endpoint, grantsCount),
        error: grantsCount === data.filters.grantsCount ? data.grantsResult.error : null
      },
      benefits: {
        ...data.benefits,
        requested: benefitsCount,
        endpoint: updateBenefitsEndpoint(data.benefits.endpoint, benefitsCount),
        error: benefitsCount === data.filters.benefitsCount ? data.benefits.error : null
      }
    };
  }

  function getFundingRequestKey(payload: FundingPageData): string {
    return [
      payload.filters.grantsCount,
      payload.filters.benefitsCount,
      payload.grantsResult.endpoint,
      payload.benefits.endpoint
    ].join('|');
  }

  function updateGrantsEndpoint(endpoint: string, count: number): string {
    try {
      const url = new URL(endpoint);
      url.searchParams.set('limit', String(count));
      url.searchParams.set('offset', '0');
      url.searchParams.set('include_total', 'true');
      return url.toString();
    } catch {
      return endpoint;
    }
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

  function getRecordFieldValue(record: GenericRecord, candidates: string[]): string | null {
    const field = findField(record, candidates);
    return field ? valueToString(field.value) : null;
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

    return parseDateValue(valueToString(dateField.value));
  }

  function parseDateValue(value: string | null | undefined): number {
    if (!value) {
      return 0;
    }

    const parsed = new Date(value.includes('T') ? value : `${value}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function getGrantDateValue(grant: GrantRecord): number {
    return parseDateValue(grant.agreement_start_date);
  }

  function getGrantAmount(grant: GrantRecord): number | null {
    return parseMoney(grant.agreement_value);
  }

  function getGrantProgramLabel(grant: GrantRecord): string {
    return grant.prog_name_en?.trim() || grant.owner_org_title?.trim() || 'Program unavailable';
  }

  function getGrantProvinceLabel(grant: GrantRecord): string {
    return grant.recipient_province?.trim().toUpperCase() || 'Unknown';
  }

  function getBenefitCategoryLabel(record: GenericRecord): string {
    return getRecordFieldValue(record, subtitleFields) ?? getRecordFieldValue(record, titleFields) ?? 'Unclassified';
  }

  function getMonthKey(timestamp: number): string | null {
    if (timestamp <= 0) {
      return null;
    }

    const date = new Date(timestamp);
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
  }

  function formatMonthLabel(key: string): string {
    const [year, month] = key.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, 1));
    return new Intl.DateTimeFormat('en-CA', { month: 'short', year: '2-digit', timeZone: 'UTC' }).format(date);
  }

  function addToCountMap(map: Map<string, number>, label: string, value = 1) {
    const normalizedLabel = label.trim() || 'Unknown';
    map.set(normalizedLabel, (map.get(normalizedLabel) ?? 0) + value);
  }

  function topBarsFromMap(map: Map<string, number>, limit = 6): ChartBar[] {
    return [...map.entries()]
      .map(([label, value]) => ({ label, value }))
      .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label))
      .slice(0, limit);
  }

  function sum(values: number[]): number {
    return values.reduce((total, value) => total + value, 0);
  }

  function buildAnalytics(
    grants: ScoredRecord<GrantRecord>[],
    benefits: ScoredRecord<GenericRecord>[],
    requestedGrantsCount: number,
    requestedBenefitsCount: number
  ): AnalyticsSummary {
    const grantAmounts = grants.map((match) => match.amount).filter((value): value is number => value !== null);
    const benefitAmounts = benefits.map((match) => match.amount).filter((value): value is number => value !== null);
    const grantTotalAmount = sum(grantAmounts);
    const benefitTotalAmount = sum(benefitAmounts);
    const provinceCounts = new Map<string, number>();
    const benefitCategoryCounts = new Map<string, number>();
    const grantProgramAmounts = new Map<string, number>();
    const trendCounts = new Map<string, number>();

    for (const match of grants) {
      const grant = match.record;
      addToCountMap(provinceCounts, getGrantProvinceLabel(grant));
      addToCountMap(grantProgramAmounts, getGrantProgramLabel(grant), match.amount ?? 0);

      const monthKey = getMonthKey(getGrantDateValue(grant));
      if (monthKey) {
        addToCountMap(trendCounts, monthKey);
      }
    }

    for (const match of benefits) {
      const benefit = match.record;
      addToCountMap(benefitCategoryCounts, getBenefitCategoryLabel(benefit));

      const monthKey = getMonthKey(getGenericDateValue(benefit));
      if (monthKey) {
        addToCountMap(trendCounts, monthKey);
      }
    }

    return {
      amountBySource: [
        {
          label: 'Grant matches',
          value: grantTotalAmount,
          detail: `${formatCount(grantAmounts.length)} matches with amount`
        },
        {
          label: 'Benefit matches',
          value: benefitTotalAmount,
          detail: `${formatCount(benefitAmounts.length)} matches with amount`
        }
      ],
      benefitCategoryBars: topBarsFromMap(benefitCategoryCounts),
      benefitKnownAmountCount: benefitAmounts.length,
      benefitTotalAmount,
      combinedTotalAmount: grantTotalAmount + benefitTotalAmount,
      datasetMixBars: [
        {
          label: 'Grant matches',
          value: grants.length,
          detail: requestedGrantsCount > 0 ? 'Current analytics window' : 'No active scan'
        },
        {
          label: 'Benefit matches',
          value: benefits.length,
          detail: requestedBenefitsCount > 0 ? 'Current analytics window' : 'No active scan'
        }
      ],
      grantKnownAmountCount: grantAmounts.length,
      grantProgramBars: topBarsFromMap(grantProgramAmounts).filter((bar) => bar.value > 0),
      grantProvinceBars: topBarsFromMap(provinceCounts),
      grantTotalAmount,
      trendBars: [...trendCounts.entries()]
        .sort(([left], [right]) => left.localeCompare(right))
        .slice(-8)
        .map(([label, value]) => ({ label: formatMonthLabel(label), value })),
      totalBenefitRecords: benefits.length,
      totalGrantRecords: grants.length,
      totalRecords: grants.length + benefits.length
    };
  }

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : 'Unavailable';
  }

  function formatCompactMoney(value: number): string {
    return value > 0 ? compactMoneyFormatter.format(value) : 'No amount';
  }

  function formatMoney(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) && value > 0
      ? moneyFormatter.format(value)
      : 'No amount data';
  }

  function getBarWidth(value: number, maximum: number): number {
    if (value <= 0 || maximum <= 0) {
      return 0;
    }

    return Math.max(4, Math.min(100, (value / maximum) * 100));
  }

  function getVerticalBarHeight(value: number, maximum: number): number {
    if (value <= 0 || maximum <= 0) {
      return 0;
    }

    return Math.max(8, Math.min(100, (value / maximum) * 100));
  }

  function getMaximumValue(bars: ChartBar[]): number {
    return Math.max(0, ...bars.map((bar) => bar.value));
  }

  function liveViewRoute(grantsCount: number, benefitsCount: number): string {
    return `/dashboard/live-view?grantsCount=${grantsCount}&benefitsCount=${benefitsCount}`;
  }
</script>

<svelte:head>
  <title>Analytics | FundRadar</title>
  <meta name="description" content="Analyze company-profile funding matches in FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="analytics" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search analytics, benefits, or workspace pages..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end" aria-labelledby="analytics-heading">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Analytics</p>
            <h2 id="analytics-heading" class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Match Analytics
            </h2>
            <p class="m-0 max-w-2xl text-base leading-6 text-[#45464d]">
              Aggregate only company-profile matches from loaded grants and Business Benefits Finder records.
            </p>
          </div>
        </section>

        {#if !cacheHydrated || !profileHydrated}
          <section class="rounded-xl border border-[#c6c6cd] bg-white p-8 text-center" role="status">
            <h3 class="m-0 text-lg font-semibold text-[#191c1e]">Loading match analytics</h3>
            <p class="m-0 mt-2 text-sm leading-6 text-[#45464d]">Loading your company profile and preparing matched funding aggregates.</p>
          </section>
        {:else}
          {#if !profileHasSignals}
            <section class="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" role="status">
              <h3 class="m-0 font-semibold">Company profile needed for match analytics</h3>
              <p class="m-0 mt-2 leading-6">
                Analytics only displays records that match your company profile. Complete the profile to generate matched funding charts.
              </p>
            </section>
          {:else if analytics.totalRecords === 0}
            <section class="mb-6 rounded-xl border border-[#c6c6cd] bg-white p-4 text-sm text-[#45464d]" role="status">
              <h3 class="m-0 font-semibold text-[#191c1e]">No matches in the loaded analytics window</h3>
              <p class="m-0 mt-2 leading-6">
                Load more records or broaden the company profile keywords to find grant and benefit matches.
              </p>
            </section>
          {/if}

          {#if data.grantsResult.error || data.benefits.error}
            <section class="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="status">
              <h3 class="m-0 font-semibold">Some match analytics data is unavailable</h3>
              {#if data.grantsResult.error}
                <p class="m-0 mt-2 leading-6">Grants: {data.grantsResult.error}</p>
              {/if}
              {#if data.benefits.error}
                <p class="m-0 mt-2 leading-6">Benefits: {data.benefits.error}</p>
              {/if}
            </section>
          {/if}

          <section class="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-4" aria-label="Analytics summary">
            <article class="rounded-xl border border-[#c6c6cd] bg-[#131b2e] p-5 text-[#dae2fd] shadow-[0_4px_20px_rgba(0,0,0,0.04)] lg:col-span-2">
              <span class="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-white">
                <span class="material-symbols-outlined text-[14px]">analytics</span>
                Matched funding
              </span>
              <h3 class="m-0 font-[Public_Sans] text-4xl font-semibold text-white">{formatMoney(analytics.combinedTotalAmount)}</h3>
              <p class="m-0 mt-3 max-w-2xl text-sm leading-6 text-[#dae2fd]/80">
                Sum of parsed funding amounts across matched grant and benefit records. Matches without machine-readable amounts remain in counts but are excluded from value totals.
              </p>
            </article>
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Grant amount coverage</span>
              <strong class="block font-[Public_Sans] text-3xl font-semibold text-[#191c1e]">{formatCount(analytics.grantKnownAmountCount)}</strong>
              <span class="mt-2 block text-sm text-[#45464d]">matches with values</span>
            </article>
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Benefit amount coverage</span>
              <strong class="block font-[Public_Sans] text-3xl font-semibold text-[#191c1e]">{formatCount(analytics.benefitKnownAmountCount)}</strong>
              <span class="mt-2 block text-sm text-[#45464d]">matches with values</span>
            </article>
          </section>

          <section class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-2" aria-label="Funding analytics graphs">
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Funding value</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Known matched value by source</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">payments</span>
              </div>
              <div class="grid gap-4">
                {#each analytics.amountBySource as item (item.label)}
                  <div>
                    <div class="mb-2 flex justify-between gap-4 text-sm">
                      <span class="font-semibold text-[#191c1e]">{item.label}</span>
                      <span class="text-[#45464d]">{formatCompactMoney(item.value)}</span>
                    </div>
                    <div class="h-3 overflow-hidden rounded-full bg-[#eceef0]">
                      <div class="h-full rounded-full bg-emerald-600" style={`width: ${getBarWidth(item.value, maxAmountBySource)}%;`}></div>
                    </div>
                    {#if item.detail}
                      <p class="m-0 mt-1 text-xs leading-5 text-[#45464d]">{item.detail}</p>
                    {/if}
                  </div>
                {/each}
              </div>
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Dataset mix</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Matches by source</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">dataset</span>
              </div>
              <div class="grid gap-4">
                {#each analytics.datasetMixBars as item (item.label)}
                  <div>
                    <div class="mb-2 flex justify-between gap-4 text-sm">
                      <span class="font-semibold text-[#191c1e]">{item.label}</span>
                      <span class="text-[#45464d]">{formatCount(item.value)}</span>
                    </div>
                    <div class="h-3 overflow-hidden rounded-full bg-[#eceef0]">
                      <div class="h-full rounded-full bg-[#131b2e]" style={`width: ${getBarWidth(item.value, maxDatasetCount)}%;`}></div>
                    </div>
                    {#if item.detail}
                      <p class="m-0 mt-1 text-xs leading-5 text-[#45464d]">{item.detail}</p>
                    {/if}
                  </div>
                {/each}
              </div>
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Geography</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Grant matches by province</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">map</span>
              </div>
              {#if analytics.grantProvinceBars.length === 0}
                <p class="m-0 rounded-lg border border-[#c6c6cd] bg-[#f7f9fb] p-4 text-sm leading-6 text-[#45464d]">No matched grant province data is available.</p>
              {:else}
                <div class="grid gap-3">
                  {#each analytics.grantProvinceBars as item (item.label)}
                    <div class="grid grid-cols-[64px_1fr_48px] items-center gap-3">
                      <span class="truncate text-sm font-semibold text-[#191c1e]">{item.label}</span>
                      <div class="h-2.5 overflow-hidden rounded-full bg-[#eceef0]">
                        <div class="h-full rounded-full bg-emerald-600" style={`width: ${getBarWidth(item.value, maxProvinceCount)}%;`}></div>
                      </div>
                      <span class="text-right text-sm text-[#45464d]">{formatCount(item.value)}</span>
                    </div>
                  {/each}
                </div>
              {/if}
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Benefits</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Benefit matches by category</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">category</span>
              </div>
              {#if analytics.benefitCategoryBars.length === 0}
                <p class="m-0 rounded-lg border border-[#c6c6cd] bg-[#f7f9fb] p-4 text-sm leading-6 text-[#45464d]">No matched benefit category data is available.</p>
              {:else}
                <div class="grid gap-3">
                  {#each analytics.benefitCategoryBars as item (item.label)}
                    <div>
                      <div class="mb-1 flex justify-between gap-4 text-sm">
                        <span class="truncate font-semibold text-[#191c1e]">{item.label}</span>
                        <span class="text-[#45464d]">{formatCount(item.value)}</span>
                      </div>
                      <div class="h-2.5 overflow-hidden rounded-full bg-[#eceef0]">
                        <div class="h-full rounded-full bg-[#131b2e]" style={`width: ${getBarWidth(item.value, maxBenefitCategoryCount)}%;`}></div>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)] xl:col-span-2">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Grant programs</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Top matched grant programs by known value</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">leaderboard</span>
              </div>
              {#if analytics.grantProgramBars.length === 0}
                <p class="m-0 rounded-lg border border-[#c6c6cd] bg-[#f7f9fb] p-4 text-sm leading-6 text-[#45464d]">No matched grant program value data is available.</p>
              {:else}
                <div class="grid gap-3">
                  {#each analytics.grantProgramBars as item (item.label)}
                    <div>
                      <div class="mb-1 flex justify-between gap-4 text-sm">
                        <span class="truncate font-semibold text-[#191c1e]">{item.label}</span>
                        <span class="shrink-0 text-[#45464d]">{formatCompactMoney(item.value)}</span>
                      </div>
                      <div class="h-2.5 overflow-hidden rounded-full bg-[#eceef0]">
                        <div class="h-full rounded-full bg-emerald-600" style={`width: ${getBarWidth(item.value, maxGrantProgramAmount)}%;`}></div>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)] xl:col-span-2">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Timeline</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Dated matches by month</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">timeline</span>
              </div>
              {#if analytics.trendBars.length === 0}
                <p class="m-0 rounded-lg border border-[#c6c6cd] bg-[#f7f9fb] p-4 text-sm leading-6 text-[#45464d]">No dated matches are available for a monthly trend.</p>
              {:else}
                <div class="grid h-64 grid-cols-[repeat(8,minmax(0,1fr))] items-end gap-3 border-b border-[#c6c6cd] pb-2" aria-label="Monthly record trend">
                  {#each analytics.trendBars as item (item.label)}
                    <div class="flex h-full flex-col justify-end gap-2 text-center">
                      <span class="text-xs font-semibold text-[#45464d]">{formatCount(item.value)}</span>
                      <div class="flex min-h-32 items-end rounded-t bg-[#eceef0]">
                        <div
                          class="w-full rounded-t bg-emerald-600"
                          style={`height: ${getVerticalBarHeight(item.value, maxTrendCount)}%;`}
                          title={`${item.label}: ${formatCount(item.value)} matches`}
                        ></div>
                      </div>
                      <span class="text-xs text-[#45464d]">{item.label}</span>
                    </div>
                  {/each}
                </div>
              {/if}
            </article>
          </section>

          <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-label="Analytics record window">
            <div class="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <h3 class="m-0 text-lg font-semibold leading-tight text-[#191c1e]">Loaded match window</h3>
                <p class="m-0 mt-2 max-w-2xl text-sm leading-6 text-[#45464d]">
                  Graphs include the matched grant and benefit records available in the current analytics window.
                </p>
              </div>
              {#if canLoadMoreAnalytics}
                <button
                  class="rounded-lg border-2 border-[#c6c6cd] px-5 py-2.5 text-sm font-semibold text-[#0b1c30] transition hover:border-[#0b1c30] hover:bg-[#eceef0] disabled:cursor-wait disabled:opacity-60"
                  type="button"
                  disabled={loadingAnalytics}
                  onclick={loadMoreAnalytics}
                >
                  {loadingAnalytics ? 'Finding more matches' : 'Load more records for matches'}
                </button>
              {:else}
                <p class="m-0 text-sm leading-6 text-[#45464d]">The match analytics record window is at its limit.</p>
              {/if}
            </div>
          </section>
        {/if}
      </div>
    </main>
  </div>
</div>
