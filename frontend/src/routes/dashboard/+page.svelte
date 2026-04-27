<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import {
    hydrateProgressiveCachedBenefitsResult,
    hydrateProgressiveCachedGrantsResult,
    type HydrationProgress
  } from '$lib/client/funding-cache';
  import {
    REVIEW_MATCH_THRESHOLD,
    companyDisplayName,
    createEmptyCompanyProfile,
    hasProfileSignals,
    isCurrentlyAvailableRecord,
    loadCompanyProfile,
    scoreBenefitRecord,
    scoreGrantRecord,
    type CompanyProfile,
    type GenericRecord
  } from '$lib/client/company-matching';
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
  type DashboardPageData = PageData & {
    limits: {
      increment: number;
      maxCount: number;
    };
    grantsResult: {
      endpoint: string;
      records: GrantRecord[];
      error: string | null;
    };
    benefits: {
      endpoint: string;
      records: GenericRecord[];
      error: string | null;
    };
  };
  type PreloadStatus = {
    state: 'idle' | 'loading' | 'ready' | 'error';
    loaded: number;
    matches: number;
    target: number;
    error: string | null;
  };
  type WalkthroughStep = {
    icon: string;
    title: string;
    detail: string;
    checklist: string[];
  };

  const COMPANY_ONBOARDING_PENDING_STORAGE_KEY = 'publicus.companyProfileOnboarding.pending.v1';
  const companyProfileWalkthroughSteps: WalkthroughStep[] = [
    {
      icon: 'badge',
      title: 'Confirm company identity',
      detail: 'Start with the legal entity name, operating name, website, applicant type, and incorporation date.',
      checklist: ['Legal entity and DBA', 'Website', 'Applicant type']
    },
    {
      icon: 'location_on',
      title: 'Add jurisdiction and scale',
      detail: 'Set the company province, city, and current employee range so location and size-sensitive programs rank correctly.',
      checklist: ['Province or territory', 'Head office city', 'Employee range']
    },
    {
      icon: 'category',
      title: 'Choose sector signals',
      detail: 'Select the primary industry, sub-sector, keywords, and funding activities that describe what the company is trying to fund.',
      checklist: ['Industry and sub-sector', 'Funding keywords', 'Capital objectives']
    },
    {
      icon: 'task_alt',
      title: 'Save and review matches',
      detail: 'Save the profile to generate ranked grants and Business Benefits Finder matches from the dashboard data sources.',
      checklist: ['Target funding amount', 'Save profile', 'Review opportunity matches']
    }
  ];

  let { data }: { data: DashboardPageData } = $props();
  let preloadStarted = $state(false);
  let onboardingChecked = $state(false);
  let showCompanyProfileWalkthrough = $state(false);
  let companyProfileWalkthroughStep = $state(0);
  let grantsPreload = $state<PreloadStatus>(createPreloadStatus());
  let benefitsPreload = $state<PreloadStatus>(createPreloadStatus());
  let profile = $state<CompanyProfile>(createEmptyCompanyProfile());
  let profileHydrated = $state(false);

  const MATCH_PRELOAD_TARGET = 50;
  const PRELOAD_BATCH_SIZE = 500;
  const profileReady = $derived(profileHydrated && hasProfileSignals(profile));
  const applicantName = $derived(companyDisplayName(profile));
  const totalLoadedRecords = $derived(grantsPreload.loaded + benefitsPreload.loaded);
  const totalProfileMatches = $derived(grantsPreload.matches + benefitsPreload.matches);
  const scanBasisLabel = $derived(
    profileReady
      ? `Profile-driven matching active for ${applicantName}.`
      : profileHydrated
        ? 'Broad matching active until the company profile has more matching signals.'
        : 'Loading company profile before ranking matches.'
  );
  let overviewStats = $derived([
    {
      label: 'Grant matches',
      value: formatCount(grantsPreload.matches),
      detail: `${formatCount(grantsPreload.loaded)} Open Canada records loaded · ${statusLabel(grantsPreload)}`
    },
    {
      label: 'Business Benefits matches',
      value: formatCount(benefitsPreload.matches),
      detail: `${formatCount(benefitsPreload.loaded)} available Innovation Canada programs loaded · ${statusLabel(benefitsPreload)}`
    },
    {
      label: 'Total matches',
      value: formatCount(totalProfileMatches),
      detail: `${formatCount(grantsPreload.matches)} grants · ${formatCount(benefitsPreload.matches)} Business Benefits Finder`
    }
  ]);
  const sourceSummaries = $derived([
    {
      icon: 'account_balance',
      title: 'Grants and Contributions',
      href: '/dashboard/grants-contributions',
      loaded: grantsPreload.loaded,
      matches: grantsPreload.matches,
      status: statusLabel(grantsPreload),
      state: grantsPreload.state,
      detail: 'Open Canada records ranked against historical award signals.'
    },
    {
      icon: 'work',
      title: 'Business Benefits Finder',
      href: '/dashboard/business-benefits-finder',
      loaded: benefitsPreload.loaded,
      matches: benefitsPreload.matches,
      status: statusLabel(benefitsPreload),
      state: benefitsPreload.state,
      detail: 'Currently available Innovation Canada programs matched to the profile.'
    }
  ]);
  const routeCards = $derived([
    {
      icon: 'description',
      title: 'Opportunity Matches',
      href: '/dashboard/persona/matches',
      copy: `${formatCount(totalProfileMatches)} combined matches ready for ranked review.`
    },
    {
      icon: 'account_balance',
      title: 'Grants and Contributions',
      href: '/dashboard/grants-contributions',
      copy: `${formatCount(grantsPreload.matches)} grant matches from ${formatCount(grantsPreload.loaded)} loaded records.`
    },
    {
      icon: 'work',
      title: 'Business Benefits Finder',
      href: '/dashboard/business-benefits-finder',
      copy: `${formatCount(benefitsPreload.matches)} available benefit matches from Innovation Canada.`
    }
  ]);
  const nextAction = $derived(getNextAction(profileReady, profileHydrated, grantsPreload, benefitsPreload, totalProfileMatches));
  const nextActionCards = $derived([
    nextAction,
    {
      icon: 'analytics',
      title: 'Open Analytics',
      detail: 'Compare loaded grant and benefit matches by source, value, location, and timing.',
      href: '/dashboard/live-view',
      label: 'Open analytics'
    },
    {
      icon: 'tune',
      title: 'Tune Source Filters',
      detail: 'Review the underlying source pages when you need to broaden or inspect the loaded records.',
      href: '/dashboard/business-benefits-finder',
      label: 'Open benefits'
    }
  ]);
  const currentWalkthroughStep = $derived(
    companyProfileWalkthroughSteps[companyProfileWalkthroughStep] ?? companyProfileWalkthroughSteps[0]
  );
  const walkthroughProgressLabel = $derived(
    `Step ${companyProfileWalkthroughStep + 1} of ${companyProfileWalkthroughSteps.length}`
  );
  const walkthroughProgressPercent = $derived(
    `${Math.round(((companyProfileWalkthroughStep + 1) / companyProfileWalkthroughSteps.length) * 100)}%`
  );

  $effect(() => {
    if (!browser || preloadStarted) {
      return;
    }

    preloadStarted = true;
    void preloadDashboardFundingData();
  });

  $effect(() => {
    if (!browser || onboardingChecked) {
      return;
    }

    onboardingChecked = true;
    hydrateCompanyProfileWalkthrough();
  });

  async function preloadDashboardFundingData() {
    const loadedProfile = await loadCompanyProfile();
    profile = loadedProfile;
    profileHydrated = true;

    await Promise.all([
      preloadGrantMatches(loadedProfile),
      preloadBenefitMatches(loadedProfile)
    ]);
  }

  async function preloadGrantMatches(profile: CompanyProfile) {
    let requestedCount = 0;
    let previousRecordCount = -1;
    grantsPreload = {
      ...createPreloadStatus(),
      state: 'loading',
      target: data.limits.maxCount
    };

    while (grantsPreload.matches < MATCH_PRELOAD_TARGET && requestedCount < data.limits.maxCount) {
      requestedCount = Math.min(data.limits.maxCount, Math.max(requestedCount + PRELOAD_BATCH_SIZE, PRELOAD_BATCH_SIZE));
      const result = await hydrateProgressiveCachedGrantsResult(data.grantsResult.endpoint, requestedCount, {
        batchSize: Math.max(data.limits.increment, PRELOAD_BATCH_SIZE),
        onProgress: (progress) => {
          grantsPreload = statusFromProgress(grantsPreload, progress, data.limits.maxCount);
        }
      });
      const records = result.records as GrantRecord[];
      const matches = countGrantMatches(records, profile);

      grantsPreload = {
        state: result.error ? 'error' : 'loading',
        loaded: records.length,
        matches,
        target: data.limits.maxCount,
        error: result.error
      };

      if (result.error || records.length <= previousRecordCount) {
        break;
      }

      previousRecordCount = records.length;
    }

    grantsPreload = {
      ...grantsPreload,
      state: grantsPreload.error ? 'error' : 'ready'
    };
  }

  async function preloadBenefitMatches(profile: CompanyProfile) {
    let requestedCount = 0;
    let previousRecordCount = -1;
    benefitsPreload = {
      ...createPreloadStatus(),
      state: 'loading',
      target: data.limits.maxCount
    };

    while (benefitsPreload.matches < MATCH_PRELOAD_TARGET && requestedCount < data.limits.maxCount) {
      requestedCount = Math.min(data.limits.maxCount, Math.max(requestedCount + PRELOAD_BATCH_SIZE, PRELOAD_BATCH_SIZE));
      const result = await hydrateProgressiveCachedBenefitsResult(data.benefits.endpoint, requestedCount, {
        onProgress: (progress) => {
          benefitsPreload = statusFromProgress(benefitsPreload, progress, data.limits.maxCount);
        }
      });
      const records = result.records;
      const matches = countBenefitMatches(records, profile);

      benefitsPreload = {
        state: result.error ? 'error' : 'loading',
        loaded: records.length,
        matches,
        target: data.limits.maxCount,
        error: result.error
      };

      if (result.error || records.length <= previousRecordCount) {
        break;
      }

      previousRecordCount = records.length;
    }

    benefitsPreload = {
      ...benefitsPreload,
      state: benefitsPreload.error ? 'error' : 'ready'
    };
  }

  function countGrantMatches(records: GrantRecord[], profile: CompanyProfile): number {
    const scored = records.map((record) => scoreGrantRecord(record, profile));
    return hasProfileSignals(profile)
      ? scored.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD).length
      : scored.length;
  }

  function countBenefitMatches(records: GenericRecord[], profile: CompanyProfile): number {
    const scored = records.filter(isCurrentlyAvailableRecord).map((record) => scoreBenefitRecord(record, profile));
    return hasProfileSignals(profile)
      ? scored.filter((match) => match.matchScore >= REVIEW_MATCH_THRESHOLD).length
      : scored.length;
  }

  function createPreloadStatus(): PreloadStatus {
    return {
      state: 'idle',
      loaded: 0,
      matches: 0,
      target: 0,
      error: null
    };
  }

  function statusFromProgress(current: PreloadStatus, progress: HydrationProgress, maxCount: number): PreloadStatus {
    return {
      ...current,
      state: 'loading',
      loaded: progress.loaded,
      target: maxCount
    };
  }

  function statusLabel(status: PreloadStatus): string {
    if (status.state === 'ready') {
      return 'Ready';
    }

    if (status.state === 'error') {
      return 'Limited';
    }

    if (status.state === 'loading') {
      return 'Loading';
    }

    return 'Queued';
  }

  function getStatusToneClass(state: PreloadStatus['state']): string {
    if (state === 'ready') {
      return 'bg-emerald-50 text-emerald-700';
    }

    if (state === 'error') {
      return 'bg-amber-50 text-amber-800';
    }

    if (state === 'loading') {
      return 'bg-blue-50 text-blue-700';
    }

    return 'bg-slate-100 text-slate-600';
  }

  function getNextAction(
    hasProfile: boolean,
    profileLoaded: boolean,
    grantsStatus: PreloadStatus,
    benefitsStatus: PreloadStatus,
    matchCount: number
  ) {
    if (!profileLoaded) {
      return {
        icon: 'hourglass_top',
        title: 'Loading company profile',
        detail: 'Profile details are being loaded before FundRadar ranks source records.',
        href: '/dashboard/persona',
        label: 'Open profile'
      };
    }

    if (!hasProfile) {
      return {
        icon: 'business',
        title: 'Complete Company Profile',
        detail: 'Add industry, location, activities, and funding goals so the match counts become specific.',
        href: '/dashboard/persona',
        label: 'Update profile'
      };
    }

    if (grantsStatus.state === 'loading' || benefitsStatus.state === 'loading') {
      return {
        icon: 'sync',
        title: 'Review as results load',
        detail: `${formatCount(grantsStatus.loaded + benefitsStatus.loaded)} records are cached so far. Source pages will keep finding matches.`,
        href: '/dashboard/persona/matches',
        label: 'Review matches'
      };
    }

    if (matchCount > 0) {
      return {
        icon: 'task_alt',
        title: 'Review Opportunity Matches',
        detail: `${formatCount(matchCount)} profile matches are ready for shortlist and application review.`,
        href: '/dashboard/persona/matches',
        label: 'Open matches'
      };
    }

    return {
      icon: 'travel_explore',
      title: 'Open funding sources',
      detail: 'No profile matches are ready yet. Inspect source records or broaden company profile keywords.',
      href: '/dashboard/grants-contributions',
      label: 'Open grants'
    };
  }

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : '0';
  }

  function hydrateCompanyProfileWalkthrough() {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('onboarding') === 'company-profile';
    const pending = readStorageFlag(COMPANY_ONBOARDING_PENDING_STORAGE_KEY);

    if (requested) {
      writeStorageFlag(COMPANY_ONBOARDING_PENDING_STORAGE_KEY, true);
      removeOnboardingSearchParam(params);
    }

    if (requested || pending) {
      showCompanyProfileWalkthrough = true;
      companyProfileWalkthroughStep = 0;
    }
  }

  function completeCompanyProfileWalkthrough() {
    showCompanyProfileWalkthrough = false;
    writeStorageFlag(COMPANY_ONBOARDING_PENDING_STORAGE_KEY, false);
  }

  function advanceCompanyProfileWalkthrough() {
    companyProfileWalkthroughStep = Math.min(
      companyProfileWalkthroughSteps.length - 1,
      companyProfileWalkthroughStep + 1
    );
  }

  function retreatCompanyProfileWalkthrough() {
    companyProfileWalkthroughStep = Math.max(0, companyProfileWalkthroughStep - 1);
  }

  function readStorageFlag(key: string): boolean {
    try {
      return localStorage.getItem(key) === '1';
    } catch {
      return false;
    }
  }

  function writeStorageFlag(key: string, value: boolean) {
    try {
      if (value) {
        localStorage.setItem(key, '1');
      } else {
        localStorage.removeItem(key);
      }
    } catch {
      // localStorage can be unavailable in private windows or locked-down browsers.
    }
  }

  function removeOnboardingSearchParam(params: URLSearchParams) {
    params.delete('onboarding');
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`;
    window.history.replaceState(window.history.state, '', nextUrl);
  }
</script>

<svelte:head>
  <title>Overview | FundRadar</title>
  <meta
    name="description"
    content="FundRadar helps Canadian businesses discover, match, and rank government funding opportunities."
  />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="overview" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search pages, tools, or funding data..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <div class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Overview</p>
            <h2 class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Funding Overview
            </h2>
            <p class="m-0 max-w-3xl text-base leading-6 text-[#45464d]">
              Operational snapshot for {applicantName}. Match counts update while grants and Business Benefits Finder
              records load in this browser.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" href="/dashboard/persona/matches">
              Opportunity Matches
            </a>
            <a class="rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0]" href="/dashboard/persona">
              Company Profile
            </a>
          </div>
        </div>

        <section class="grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="FundRadar platform statistics">
          {#each overviewStats as stat (stat.label)}
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <p class="m-0 mb-3 text-xs font-semibold uppercase tracking-normal text-[#45464d]">{stat.label}</p>
              <strong class="mb-2 block font-[Public_Sans] text-4xl font-semibold leading-tight text-[#191c1e]">{stat.value}</strong>
              <p class="m-0 text-sm leading-6 text-[#45464d]">{stat.detail}</p>
            </article>
          {/each}
        </section>

        <div class="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
          <section class="flex flex-col gap-6 lg:col-span-8" aria-labelledby="platform-heading">
            <article class="overflow-hidden rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
              <div class="flex flex-col gap-6 bg-[#131b2e] p-6 md:flex-row md:items-end md:justify-between">
                <div>
                  <span class="mb-3 inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-white">
                    <span class="material-symbols-outlined text-[14px]">radar</span>
                    Funding summary
                  </span>
                  <h3 id="platform-heading" class="m-0 mb-2 font-[Public_Sans] text-3xl font-semibold leading-tight text-[#dae2fd]">
                    Funding scan for {applicantName}
                  </h3>
                  <p class="m-0 max-w-2xl text-sm leading-6 text-[#dae2fd]/80">
                    {scanBasisLabel} Current matches include {formatCount(grantsPreload.matches)} grants and
                    {formatCount(benefitsPreload.matches)} Business Benefits Finder programs.
                  </p>
                </div>
                <a class="shrink-0 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700" href={nextAction.href}>
                  {nextAction.label}
                </a>
              </div>

              <div class="grid grid-cols-1 gap-px bg-[#c6c6cd] md:grid-cols-3">
                {#each routeCards as card (card.title)}
                  <a class="bg-white p-5 no-underline transition hover:bg-[#f7f9fb]" href={card.href}>
                    <div class="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                      <span class="material-symbols-outlined">{card.icon}</span>
                    </div>
                    <h4 class="m-0 mb-2 text-lg font-semibold leading-snug text-[#191c1e]">{card.title}</h4>
                    <p class="m-0 text-sm leading-6 text-[#45464d]">{card.copy}</p>
                  </a>
                {/each}
              </div>
            </article>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="actions-heading">
              <div class="mb-5 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <div>
                  <h3 id="actions-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Next Actions</h3>
                  <p class="m-0 mt-1 text-sm text-[#45464d]">Use the highest-signal route based on current profile and source status.</p>
                </div>
                <span class="material-symbols-outlined text-emerald-700">task_alt</span>
              </div>

              <div class="grid gap-4">
                {#each nextActionCards as item, index (item.title)}
                  <a
                    class={`grid gap-4 rounded-lg border p-4 no-underline transition hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] md:grid-cols-[3rem_1fr_auto] md:items-center ${
                      index === 0 ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'
                    }`}
                    href={item.href}
                  >
                    <span class={`flex h-10 w-10 items-center justify-center rounded-lg ${index === 0 ? 'bg-emerald-700 text-white' : 'bg-white text-emerald-700'}`}>
                      <span class="material-symbols-outlined">{item.icon}</span>
                    </span>
                    <div>
                      <h4 class="m-0 mb-1 text-base font-semibold text-[#191c1e]">{item.title}</h4>
                      <p class="m-0 text-sm leading-6 text-[#45464d]">{item.detail}</p>
                    </div>
                    <span class="material-symbols-outlined hidden text-slate-400 md:block">chevron_right</span>
                  </a>
                {/each}
              </div>
            </section>
          </section>

          <aside class="flex flex-col gap-6 lg:sticky lg:top-4 lg:col-span-4">
            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="coverage-heading">
              <div class="mb-4 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <h3 id="coverage-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Source Health</h3>
                <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-emerald-700">Auto-load</span>
              </div>

              <div class="grid gap-3">
                {#each sourceSummaries as item (item.title)}
                  <a class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 no-underline transition hover:bg-white" href={item.href}>
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex min-w-0 items-start gap-3">
                        <span class="material-symbols-outlined mt-0.5 text-emerald-700">{item.icon}</span>
                        <div class="min-w-0">
                          <span class="block text-sm font-semibold text-[#191c1e]">{item.title}</span>
                          <span class="block text-xs leading-5 text-[#45464d]">{item.detail}</span>
                        </div>
                      </div>
                      <span class={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-normal ${getStatusToneClass(item.state)}`}>
                        {item.status}
                      </span>
                    </div>
                    <dl class="m-0 grid grid-cols-2 gap-2">
                      <div class="rounded-lg bg-white px-3 py-2">
                        <dt class="text-[11px] font-black uppercase tracking-normal text-[#45464d]">Matches</dt>
                        <dd class="m-0 text-lg font-semibold text-[#006c49]">{formatCount(item.matches)}</dd>
                      </div>
                      <div class="rounded-lg bg-white px-3 py-2">
                        <dt class="text-[11px] font-black uppercase tracking-normal text-[#45464d]">Loaded</dt>
                        <dd class="m-0 text-lg font-semibold text-[#191c1e]">{formatCount(item.loaded)}</dd>
                      </div>
                    </dl>
                  </a>
                {/each}
              </div>
            </section>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="next-heading">
              <div class="mb-4 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#131b2e] text-[#dae2fd]">
                  <span class="material-symbols-outlined">{nextAction.icon}</span>
                </div>
                <div>
                  <h3 id="next-heading" class="m-0 text-base font-semibold text-[#191c1e]">Next best action</h3>
                  <p class="m-0 text-sm text-[#45464d]">{nextAction.detail}</p>
                </div>
              </div>
              <a class="mb-3 block rounded-lg bg-emerald-700 px-4 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-emerald-800" href={nextAction.href}>
                {nextAction.label}
              </a>
              <a class="block rounded-lg border border-[#c6c6cd] px-4 py-2.5 text-center text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0]" href="/dashboard/live-view">
                Open Analytics
              </a>
            </section>
          </aside>
        </div>
      </div>
    </main>
  </div>

  {#if showCompanyProfileWalkthrough}
    <div class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b1c30]/55 p-4 backdrop-blur-sm" role="presentation">
      <div
        aria-labelledby="company-profile-walkthrough-heading"
        aria-modal="true"
        class="w-full max-w-[560px] rounded-xl border border-[#c6c6cd] bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.22)]"
        role="dialog"
      >
        <div class="mb-5 flex items-start gap-3">
          <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-emerald-700 text-white">
            <span class="material-symbols-outlined">{currentWalkthroughStep.icon}</span>
          </span>
          <div>
            <p class="m-0 mb-1 text-xs font-black uppercase tracking-normal text-emerald-700">
              Required company profile setup
            </p>
            <h3 id="company-profile-walkthrough-heading" class="m-0 font-[Public_Sans] text-2xl font-semibold leading-tight text-[#191c1e]">
              {currentWalkthroughStep.title}
            </h3>
          </div>
        </div>

        <div class="mb-5">
          <div class="mb-2 flex items-center justify-between text-xs font-black uppercase tracking-normal text-[#45464d]">
            <span>{walkthroughProgressLabel}</span>
            <span>{walkthroughProgressPercent}</span>
          </div>
          <div class="h-2 overflow-hidden rounded-full bg-[#e0e3e5]">
            <span class="block h-full rounded-full bg-emerald-700 transition-all" style={`width: ${walkthroughProgressPercent}`}></span>
          </div>
        </div>

        <p class="m-0 text-base leading-7 text-[#45464d]">{currentWalkthroughStep.detail}</p>

        <ul class="my-5 grid list-none gap-2 p-0">
          {#each currentWalkthroughStep.checklist as item (item)}
            <li class="flex items-center gap-2 rounded-lg bg-[#f2f4f6] px-3 py-2 text-sm font-semibold text-[#191c1e]">
              <span class="material-symbols-outlined text-[18px] text-emerald-700">check_circle</span>
              <span>{item}</span>
            </li>
          {/each}
        </ul>

        <p class="m-0 mb-5 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
          Complete this walkthrough to continue into your company profile.
        </p>

        <div class="flex flex-wrap justify-end gap-2 border-t border-[#e0e3e5] pt-5">
            <button
              class="rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={companyProfileWalkthroughStep === 0}
              type="button"
              onclick={retreatCompanyProfileWalkthrough}
            >
              Back
            </button>
            {#if companyProfileWalkthroughStep < companyProfileWalkthroughSteps.length - 1}
              <button
                class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800"
                type="button"
                onclick={advanceCompanyProfileWalkthrough}
              >
                Next
              </button>
            {:else}
              <a
                class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white no-underline transition hover:bg-emerald-800"
                href="/dashboard/persona?onboarding=1"
                onclick={completeCompanyProfileWalkthrough}
              >
                Start Company Profile
              </a>
            {/if}
        </div>
      </div>
    </div>
  {/if}
</div>
