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

  let { data }: { data: DashboardPageData } = $props();
  let preloadStarted = $state(false);
  let grantsPreload = $state<PreloadStatus>(createPreloadStatus());
  let benefitsPreload = $state<PreloadStatus>(createPreloadStatus());

  const MATCH_PRELOAD_TARGET = 50;
  const PRELOAD_BATCH_SIZE = 500;
  const overviewStats = [
    {
      label: 'Programs indexed',
      value: '200+',
      detail: 'Grants, loans, tax credits, and wage subsidies'
    },
    {
      label: 'Funding surfaced',
      value: '$50M+',
      detail: 'Matched public support tracked in one workspace'
    },
    {
      label: 'Profile stages',
      value: '3',
      detail: 'Company profile, ranked matches, application review'
    }
  ];

  const platformCards = [
    {
      icon: 'travel_explore',
      title: 'Centralized Discovery',
      copy: 'Browse Canadian government funding programs without moving between agency portals.'
    },
    {
      icon: 'rule_settings',
      title: 'Precision Matching',
      copy: 'Use company profile signals to identify programs that are realistic for your team to pursue.'
    },
    {
      icon: 'leaderboard',
      title: 'Ranked Pipeline',
      copy: 'Compare opportunities by fit, funding type, amount, sector, and application readiness.'
    }
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Build the company profile',
      detail: 'Capture sector, stage, location, team size, and funding goals before searching.'
    },
    {
      step: '02',
      title: 'Review eligible programs',
      detail: 'Move from a broad dataset into ranked grants, credits, subsidies, and support programs.'
    },
    {
      step: '03',
      title: 'Shortlist next actions',
      detail: 'Save promising records and move the strongest opportunities into application prep.'
    }
  ];

  const coverageItems = [
    { label: 'Grants', status: 'Open intake', tone: 'emerald' },
    { label: 'Tax credits', status: 'Profile dependent', tone: 'slate' },
    { label: 'Loans', status: 'Repayable', tone: 'slate' },
    { label: 'Wage subsidies', status: 'Hiring signals', tone: 'slate' }
  ];

  $effect(() => {
    if (!browser || preloadStarted) {
      return;
    }

    preloadStarted = true;
    void preloadDashboardFundingData();
  });

  async function preloadDashboardFundingData() {
    const profile = await loadCompanyProfile();

    await Promise.all([
      preloadGrantMatches(profile),
      preloadBenefitMatches(profile)
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

  function preloadLabel(status: PreloadStatus): string {
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

  function formatCount(value: number | null | undefined): string {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-CA') : '0';
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
              Overview
            </h2>
            <p class="m-0 max-w-3xl text-base leading-6 text-[#45464d]">
              FundRadar brings funding discovery, eligibility matching, and application prioritization into a single
              operating view.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" href="/dashboard/persona">
              Company Profile
            </a>
            <a class="rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0]" href="/dashboard/discovery">
              Grants and Contributions
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
                    Overview
                  </span>
                  <h3 id="platform-heading" class="m-0 mb-2 font-[Public_Sans] text-3xl font-semibold leading-tight text-[#dae2fd]">
                    Replace scattered program research with a managed funding pipeline.
                  </h3>
                  <p class="m-0 max-w-2xl text-sm leading-6 text-[#dae2fd]/80">
                    Concise status, direct entry points, and grounded workflow context help teams move from discovery
                    into application prep.
                  </p>
                </div>
                <a class="shrink-0 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700" href="/dashboard/discovery">
                  View Grants
                </a>
              </div>

              <div class="grid grid-cols-1 gap-px bg-[#c6c6cd] md:grid-cols-3">
                {#each platformCards as card (card.title)}
                  <div class="bg-white p-5">
                    <div class="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                      <span class="material-symbols-outlined">{card.icon}</span>
                    </div>
                    <h4 class="m-0 mb-2 text-lg font-semibold leading-snug text-[#191c1e]">{card.title}</h4>
                    <p class="m-0 text-sm leading-6 text-[#45464d]">{card.copy}</p>
                  </div>
                {/each}
              </div>
            </article>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="workflow-heading">
              <div class="mb-5 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <div>
                  <h3 id="workflow-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Recommended Workflow</h3>
                  <p class="m-0 mt-1 text-sm text-[#45464d]">A dashboard-first path from overview to application prep.</p>
                </div>
                <span class="material-symbols-outlined text-emerald-700">account_tree</span>
              </div>

              <div class="grid gap-4">
                {#each workflowSteps as item (item.step)}
                  <article class="grid gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-[4rem_1fr_auto] md:items-center">
                    <span class="font-[Public_Sans] text-2xl font-semibold text-emerald-700">{item.step}</span>
                    <div>
                      <h4 class="m-0 mb-1 text-base font-semibold text-[#191c1e]">{item.title}</h4>
                      <p class="m-0 text-sm leading-6 text-[#45464d]">{item.detail}</p>
                    </div>
                    <span class="material-symbols-outlined hidden text-slate-400 md:block">chevron_right</span>
                  </article>
                {/each}
              </div>
            </section>
          </section>

          <aside class="flex flex-col gap-6 lg:sticky lg:top-4 lg:col-span-4">
            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="preload-heading">
              <div class="mb-4 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <div>
                  <h3 id="preload-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Auto-loaded Matches</h3>
                  <p class="m-0 mt-1 text-sm text-[#45464d]">Dashboard cache warming for funding pages.</p>
                </div>
                <span class="material-symbols-outlined text-emerald-700">sync</span>
              </div>

              <div class="grid gap-3">
                <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div class="mb-2 flex items-start justify-between gap-3">
                    <div>
                      <h4 class="m-0 text-sm font-semibold text-[#191c1e]">Grants and Contributions</h4>
                      <p class="m-0 mt-1 text-xs font-semibold uppercase tracking-normal text-[#45464d]">
                        {preloadLabel(grantsPreload)}
                      </p>
                    </div>
                    <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                      {formatCount(grantsPreload.matches)} matches
                    </span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      class="h-full rounded-full bg-emerald-600 transition-all"
                      style={`width: ${Math.min(100, Math.round((grantsPreload.loaded / Math.max(1, grantsPreload.target)) * 100))}%`}
                    ></div>
                  </div>
                  <p class="m-0 mt-2 text-xs text-[#45464d]">
                    {formatCount(grantsPreload.loaded)} records cached
                  </p>
                </article>

                <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div class="mb-2 flex items-start justify-between gap-3">
                    <div>
                      <h4 class="m-0 text-sm font-semibold text-[#191c1e]">Business Benefits Finder</h4>
                      <p class="m-0 mt-1 text-xs font-semibold uppercase tracking-normal text-[#45464d]">
                        {preloadLabel(benefitsPreload)}
                      </p>
                    </div>
                    <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                      {formatCount(benefitsPreload.matches)} matches
                    </span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      class="h-full rounded-full bg-emerald-600 transition-all"
                      style={`width: ${Math.min(100, Math.round((benefitsPreload.loaded / Math.max(1, benefitsPreload.target)) * 100))}%`}
                    ></div>
                  </div>
                  <p class="m-0 mt-2 text-xs text-[#45464d]">
                    {formatCount(benefitsPreload.loaded)} records cached
                  </p>
                </article>
              </div>

              {#if grantsPreload.error || benefitsPreload.error}
                <p class="m-0 mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  One source returned a limited preload. The funding pages will retry when opened.
                </p>
              {/if}
            </section>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="coverage-heading">
              <div class="mb-4 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <h3 id="coverage-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Funding Coverage</h3>
                <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-emerald-700">Live</span>
              </div>

              <div class="grid gap-3">
                {#each coverageItems as item (item.label)}
                  <div class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
                    <div class="flex items-center gap-3">
                      <span
                        class={`h-2.5 w-2.5 rounded-full ${item.tone === 'emerald' ? 'bg-emerald-600' : 'bg-slate-400'}`}
                        aria-hidden="true"
                      ></span>
                      <span class="text-sm font-semibold text-[#191c1e]">{item.label}</span>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">{item.status}</span>
                  </div>
                {/each}
              </div>
            </section>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="next-heading">
              <div class="mb-4 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#131b2e] text-[#dae2fd]">
                  <span class="material-symbols-outlined">task_alt</span>
                </div>
                <div>
                  <h3 id="next-heading" class="m-0 text-base font-semibold text-[#191c1e]">Next best action</h3>
                  <p class="m-0 text-sm text-[#45464d]">Create or update your profile before ranking matches.</p>
                </div>
              </div>
              <a class="mb-3 block rounded-lg bg-emerald-700 px-4 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-emerald-800" href="/dashboard/persona">
                Continue to Profile
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
</div>
