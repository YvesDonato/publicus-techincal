<script lang="ts">
  import { browser } from '$app/environment';
  import OpportunityForceGraph, { type OpportunityForceLink, type OpportunityForceNode } from '$lib/OpportunityForceGraph.svelte';
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import {
    fetchBusinessBenefitsFeedState,
    readStoredBusinessBenefitsFeedState,
    shouldRefreshBusinessBenefitsCache,
    writeStoredBusinessBenefitsFeedState
  } from '$lib/client/business-benefits-updates';
  import {
    companyDisplayName,
    createEmptyCompanyProfile,
    hasProfileSignals,
    loadCompanyProfile,
    type CompanyProfile,
    type GenericRecord,
    type GrantRecordLike
  } from '$lib/client/company-matching';
  import {
    applyOpportunitySemanticScore,
    createDefaultOpportunityProfile,
    getOpportunityBenefitRef as getMatchedOpportunityBenefitRef,
    getOpportunityDeadlineValue as getMatchedOpportunityDeadlineValue,
    getOpportunityRecordRef as getMatchedOpportunityRecordRef,
    getOpportunitySponsor as getMatchedOpportunitySponsor,
    getOpportunityTitle as getMatchedOpportunityTitle,
    isCurrentlyAvailableOpportunity,
    scoreOpportunityBenefitRecord,
    scoreOpportunityGrantRecord,
    sortOpportunityBenefitMatches,
    type OpportunityBenefitMatch
  } from '$lib/client/opportunity-matches';
  import {
    hydrateCachedGrantsResult,
    hydrateProgressiveCachedBenefitsResult,
    type HydrationProgress
  } from '$lib/client/funding-cache';
  import {
    fetchSemanticScoresForMatches,
    getSemanticRecordId,
    type SemanticScoreMap
  } from '$lib/client/semantic-scoring';
  import { onMount } from 'svelte';

  const DEFAULT_BACKEND_API_URL = '';
  const BENEFIT_RECORD_WINDOW = 100;
  const HISTORICAL_GRANT_RECORD_WINDOW = 500;
  const GRAPH_MATCH_LIMIT = 25;
  const SHORTLIST_STORAGE_KEY = 'publicus.shortlistedOpportunityRefs';
  const pageShellClass =
    'flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]';

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

  let profile = $state<CompanyProfile>(createEmptyCompanyProfile());
  let grants = $state<GrantRecordLike[]>([]);
  let records = $state<GenericRecord[]>([]);
  let semanticScores = $state<SemanticScoreMap>({});
  let selectedNodeId = $state<string | null>(null);
  let savedOpportunityRefs = $state<string[]>([]);
  let shortlistHydrated = $state(false);
  let loading = $state(true);
  let loadingSemanticScores = $state(false);
  let error = $state<string | null>(null);
  let progress = $state<HydrationProgress | null>(null);
  let graphPanelElement = $state<HTMLDivElement | null>(null);
  let isGraphFullscreen = $state(false);

  const applicantName = $derived(companyDisplayName(profile));
  const historicalGrantMatches = $derived(grants.map((grant) => scoreOpportunityGrantRecord(grant, profile)));
  const activeRecords = $derived(records.filter(isCurrentlyAvailableOpportunity));
  const ruleMatches = $derived(
    activeRecords.map((record) => scoreOpportunityBenefitRecord(record, profile, historicalGrantMatches))
  );
  const benefitMatches = $derived(
    ruleMatches.map((match, index) =>
      applyOpportunitySemanticScore(match, semanticScores[getSemanticRecordId(match.record, 'business-benefits', index)])
    )
  );
  const sortedMatches = $derived(sortOpportunityBenefitMatches(benefitMatches, 'score'));
  const graphMatches = $derived(sortedMatches.slice(0, GRAPH_MATCH_LIMIT));
  const graphNodes = $derived(buildGraphNodes(applicantName, graphMatches));
  const graphLinks = $derived(buildGraphLinks(graphMatches));
  const savedOpportunityRefSet = $derived(new Set(savedOpportunityRefs));
  const selectedMatch = $derived(
    selectedNodeId && selectedNodeId !== 'company'
      ? graphMatches.find((match) => getGraphMatchId(match) === selectedNodeId) ?? null
      : null
  );
  const selectedOpportunityRef = $derived(selectedMatch ? getOpportunityRef(selectedMatch.record) : null);
  const selectedSaved = $derived(selectedOpportunityRef ? savedOpportunityRefSet.has(selectedOpportunityRef) : false);

  onMount(() => {
    savedOpportunityRefs = readSavedOpportunityRefs();
    shortlistHydrated = true;
    void hydrateGraphView();

    document.addEventListener('fullscreenchange', syncGraphFullscreenState);

    return () => {
      document.removeEventListener('fullscreenchange', syncGraphFullscreenState);
    };
  });

  $effect(() => {
    if (!browser || !shortlistHydrated) {
      return;
    }

    persistSavedOpportunityRefs(savedOpportunityRefs);
  });

  async function hydrateGraphView() {
    loading = true;
    error = null;
    progress = null;

    const loadedProfile = await loadCompanyProfile();
    const opportunityProfile = hasProfileSignals(loadedProfile) ? loadedProfile : createDefaultOpportunityProfile();
    profile = opportunityProfile;

    const feedState = await fetchBusinessBenefitsFeedState(DEFAULT_BACKEND_API_URL);
    const previousFeedState = readStoredBusinessBenefitsFeedState();
    const forceRefresh = shouldRefreshBusinessBenefitsCache(previousFeedState, feedState);
    const grantsEndpoint = buildGrantsEndpoint(HISTORICAL_GRANT_RECORD_WINDOW);
    const benefitsEndpoint = buildBenefitsEndpoint(BENEFIT_RECORD_WINDOW);
    const [grantsResult, benefitsResult] = await Promise.all([
      hydrateCachedGrantsResult(grantsEndpoint, HISTORICAL_GRANT_RECORD_WINDOW),
      hydrateProgressiveCachedBenefitsResult(benefitsEndpoint, BENEFIT_RECORD_WINDOW, {
        forceRefresh,
        onProgress: (nextProgress) => {
          progress = nextProgress;
        }
      })
    ]);

    if (feedState) {
      writeStoredBusinessBenefitsFeedState(feedState);
    }

    grants = grantsResult.records as GrantRecordLike[];
    records = benefitsResult.records;
    error = benefitsResult.error ?? grantsResult.error;
    loading = false;
    void hydrateSemanticScores(opportunityProfile, benefitsResult.records, grantsResult.records as GrantRecordLike[]);
  }

  async function hydrateSemanticScores(
    loadedProfile: CompanyProfile,
    loadedRecords: GenericRecord[],
    loadedGrants: GrantRecordLike[]
  ) {
    const historicalMatches = loadedGrants.map((grant) => scoreOpportunityGrantRecord(grant, loadedProfile));
    const activeLoadedRecords = loadedRecords.filter(isCurrentlyAvailableOpportunity);
    const matches = activeLoadedRecords.map((record) => scoreOpportunityBenefitRecord(record, loadedProfile, historicalMatches));

    if (matches.length === 0) {
      return;
    }

    loadingSemanticScores = true;
    const scores = await fetchSemanticScoresForMatches(DEFAULT_BACKEND_API_URL, loadedProfile, matches, 'business-benefits');
    semanticScores = {
      ...semanticScores,
      ...scores
    };
    loadingSemanticScores = false;
  }

  function buildBenefitsEndpoint(count: number): string {
    return `${DEFAULT_BACKEND_API_URL}/api/business-benefits/first/${count}`;
  }

  function buildGrantsEndpoint(count: number): string {
    const params = new URLSearchParams({
      limit: count.toString(),
      include_total: 'false'
    });

    return `${DEFAULT_BACKEND_API_URL}/api/grants?${params.toString()}`;
  }

  function buildGraphNodes(companyName: string, matches: OpportunityBenefitMatch[]): OpportunityForceNode[] {
    return [
      {
        id: 'company',
        label: companyName,
        kind: 'company',
        score: 100,
        color: '#0b1c30'
      },
      ...matches.map((match) => {
        return {
          id: getGraphMatchId(match),
          label: getOpportunityTitle(match),
          kind: 'opportunity' as const,
          score: match.matchScore,
          color: getMatchColor(match.matchScore),
          sponsor: getOpportunitySponsor(match),
          fundingLabel: getFundingLabel(match),
          deadlineLabel: getDeadlineLabel(match),
          statusLabel: match.statusLabel,
          reasons: match.reasons
        };
      })
    ];
  }

  function buildGraphLinks(matches: OpportunityBenefitMatch[]): OpportunityForceLink[] {
    return matches.map((match) => {
      const similarity = Math.max(0.05, match.matchScore / 100);

      return {
        source: 'company',
        target: getGraphMatchId(match),
        similarity,
        distance: scoreToDistance(match.matchScore)
      };
    });
  }

  function scoreToDistance(score: number): number {
    return Math.max(70, Math.min(330, 70 + (100 - score) * 3.1));
  }

  function getMatchColor(score: number): string {
    if (score >= 90) return '#006c49';
    if (score >= 75) return '#10b981';
    if (score >= 55) return '#d97706';
    return '#64748b';
  }

  function getGraphMatchId(match: OpportunityBenefitMatch): string {
    return `match:${hashString(getBenefitMatchRef(match) ?? JSON.stringify(match.record))}`;
  }

  function getOpportunityRef(record: GenericRecord): string | null {
    return getMatchedOpportunityRecordRef(record);
  }

  function getBenefitMatchRef(match: OpportunityBenefitMatch): string | null {
    return getMatchedOpportunityBenefitRef(match);
  }

  function getOpportunityTitle(match: OpportunityBenefitMatch): string {
    return getMatchedOpportunityTitle(match);
  }

  function getOpportunitySponsor(match: OpportunityBenefitMatch): string {
    return getMatchedOpportunitySponsor(match);
  }

  function getFundingLabel(match: OpportunityBenefitMatch): string {
    return match.potentialFunding === null ? 'Funding amount unavailable' : moneyFormatter.format(match.potentialFunding);
  }

  function getDeadlineLabel(match: OpportunityBenefitMatch): string {
    const dateValue = getMatchedOpportunityDeadlineValue(match);
    return dateValue ? formatDate(dateValue) : 'Rolling';
  }

  function formatDate(value: string): string {
    const parsed = new Date(value.includes('T') ? value : `${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
  }

  function readSavedOpportunityRefs(): string[] {
    if (!browser) {
      return [];
    }

    try {
      const rawValue = localStorage.getItem(SHORTLIST_STORAGE_KEY);
      const parsed = rawValue ? JSON.parse(rawValue) : [];
      return Array.isArray(parsed)
        ? unique(parsed.filter((item): item is string => typeof item === 'string').map((item) => item.trim()).filter(Boolean))
        : [];
    } catch {
      return [];
    }
  }

  function persistSavedOpportunityRefs(refs: string[]) {
    try {
      if (refs.length === 0) {
        localStorage.removeItem(SHORTLIST_STORAGE_KEY);
        return;
      }

      localStorage.setItem(SHORTLIST_STORAGE_KEY, JSON.stringify(refs));
    } catch {
      // localStorage can be unavailable in private windows or locked-down browsers.
    }
  }

  function toggleSelectedSaved() {
    if (!selectedOpportunityRef) {
      return;
    }

    savedOpportunityRefs = savedOpportunityRefSet.has(selectedOpportunityRef)
      ? savedOpportunityRefs.filter((ref) => ref !== selectedOpportunityRef)
      : [...savedOpportunityRefs, selectedOpportunityRef];
  }

  async function toggleGraphFullscreen() {
    if (!browser || !graphPanelElement) {
      return;
    }

    try {
      if (document.fullscreenElement === graphPanelElement) {
        await document.exitFullscreen();
      } else {
        await graphPanelElement.requestFullscreen();
      }
    } catch {
      syncGraphFullscreenState();
    }
  }

  function syncGraphFullscreenState() {
    isGraphFullscreen = document.fullscreenElement === graphPanelElement;
  }

  function hashString(value: string): string {
    let hash = 5381;
    for (let index = 0; index < value.length; index += 1) {
      hash = (hash * 33) ^ value.charCodeAt(index);
    }

    return (hash >>> 0).toString(36);
  }

  function unique(values: string[]): string[] {
    return [...new Set(values)];
  }
</script>

<svelte:head>
  <title>Graph View | FundRadar</title>
  <meta name="description" content="Explore company-centered funding matches in an interactive graph view." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

{#snippet graphDetailsPanel()}
  {#if selectedMatch}
    <div class="mb-3 flex items-start justify-between gap-3">
      <div>
        <p class="m-0 mb-2 text-xs font-black tracking-normal text-emerald-700 uppercase">Selected opportunity</p>
        <h3 class="m-0 text-2xl leading-tight text-[#191c1e]">{getOpportunityTitle(selectedMatch)}</h3>
        <p class="m-0 mt-2 text-sm font-black text-[#006c49] uppercase">{getOpportunitySponsor(selectedMatch)}</p>
      </div>
      <button
        aria-label="Clear selected opportunity"
        class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-[#191c1e] hover:bg-[#f2f4f6]"
        type="button"
        onclick={() => {
          selectedNodeId = null;
        }}
      >
        <span class="material-symbols-outlined text-[18px]" aria-hidden="true">close</span>
      </button>
    </div>

    <dl class="my-5 grid grid-cols-2 gap-3">
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Match</dt>
        <dd class="m-0 mt-1 text-2xl font-black text-[#006c49]">{selectedMatch.matchScore}%</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Funding</dt>
        <dd class="m-0 mt-1 text-sm font-black text-[#191c1e]">{getFundingLabel(selectedMatch)}</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Deadline</dt>
        <dd class="m-0 mt-1 text-sm font-black text-[#191c1e]">{getDeadlineLabel(selectedMatch)}</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Status</dt>
        <dd class="m-0 mt-1 text-sm font-black text-[#191c1e]">{selectedMatch.statusLabel}</dd>
      </div>
    </dl>

    <ul class="m-0 grid list-none gap-2 p-0 text-sm leading-6 text-[#45464d]">
      {#each selectedMatch.reasons.slice(0, 4) as reason (reason)}
        <li class="relative pl-4 before:absolute before:left-0 before:text-emerald-700 before:content-['-']">{reason}</li>
      {/each}
    </ul>

    <button
      aria-pressed={selectedSaved}
      class={`mt-6 w-full rounded-lg border px-4 py-3 leading-none font-black text-white disabled:cursor-not-allowed disabled:border-[#c6c6cd] disabled:bg-[#eceef0] disabled:text-[#76777d] ${
        selectedSaved ? 'border-[#131b2e] bg-[#131b2e]' : 'border-emerald-700 bg-emerald-700 hover:bg-emerald-800'
      }`}
      disabled={!selectedOpportunityRef}
      type="button"
      onclick={toggleSelectedSaved}
    >
      {selectedSaved ? 'Saved' : 'Save opportunity'}
    </button>
  {:else}
    <p class="m-0 mb-2 text-xs font-black tracking-normal text-emerald-700 uppercase">Graph summary</p>
    <h3 class="m-0 text-2xl leading-tight text-[#191c1e]">{graphMatches.length} matched benefit programs</h3>
    <p class="mt-2 text-sm leading-6 text-[#45464d]">
      The graph visualizes currently available Business Benefits Finder opportunities around {applicantName}.
    </p>

    <dl class="my-5 grid grid-cols-2 gap-3">
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Programs</dt>
        <dd class="m-0 mt-1 text-2xl font-black text-[#006c49]">{activeRecords.length}</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Graph nodes</dt>
        <dd class="m-0 mt-1 text-2xl font-black text-[#006c49]">{graphMatches.length}</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Historical grants</dt>
        <dd class="m-0 mt-1 text-sm font-black text-[#191c1e]">{grants.length}</dd>
      </div>
      <div class="rounded-lg bg-[#f2f4f6] p-3">
        <dt class="text-[11px] font-black text-[#45464d] uppercase">Scoring</dt>
        <dd class="m-0 mt-1 text-sm font-black text-[#191c1e]">{loadingSemanticScores ? 'Refining' : 'Ready'}</dd>
      </div>
    </dl>

    <a class="block rounded-lg bg-emerald-700 px-4 py-3 text-center text-sm font-black text-white no-underline transition hover:bg-emerald-800" href="/dashboard/persona/matches">
      Open ranked matches
    </a>
  {/if}
{/snippet}

<div class={pageShellClass}>
  <WorkspaceSidebar active="graph" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search graph, opportunities, or funding data..." />

    <main class="flex-1 overflow-y-auto">
      <div class="mx-auto w-full max-w-[1440px] px-6 py-10 max-md:px-4 max-md:py-7">
        <section class="mb-8 flex items-end justify-between gap-6 max-lg:grid">
          <div>
            <p class="m-0 mb-2 text-xs font-black tracking-normal text-emerald-700 uppercase">Interactive funding graph</p>
            <h2 class="m-0 text-4xl leading-tight text-[#191c1e] max-md:text-3xl">Graph View</h2>
            <p class="mt-2 max-w-[72ch] leading-7 text-[#45464d]">
              Explore active Business Benefits Finder opportunities around {applicantName}. Closer nodes represent stronger profile matches.
            </p>
          </div>

          <dl class="m-0 flex flex-wrap gap-2.5">
            <div class="grid min-w-24 rounded-lg bg-white px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
              <dt class="text-[11px] font-black text-[#45464d] uppercase">Graph nodes</dt>
              <dd class="m-0 text-xl font-black text-[#006c49]">{graphMatches.length}</dd>
            </div>
            <div class="grid min-w-24 rounded-lg bg-white px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
              <dt class="text-[11px] font-black text-[#45464d] uppercase">Saved</dt>
              <dd class="m-0 text-xl font-black text-[#006c49]">{savedOpportunityRefs.length}</dd>
            </div>
          </dl>
        </section>

        {#if loading}
          <section class="rounded-lg border border-[#d6d0bf] bg-[#fffdf6] p-6" role="status">
            <h3 class="m-0 text-xl leading-snug text-[#191c1e]">Loading graph data</h3>
            <p class="mt-2 text-sm leading-6 text-[#45464d]">
              {#if progress}
                Loaded {progress.loaded} of {progress.target} Business Benefits Finder records.
              {:else}
                Preparing company profile matches.
              {/if}
            </p>
          </section>
        {:else if error}
          <section class="rounded-lg border border-[#d6d0bf] bg-[#fffdf6] p-6" role="status">
            <h3 class="m-0 text-xl leading-snug text-[#191c1e]">Graph data unavailable</h3>
            <p class="mt-2 text-sm leading-6 text-[#45464d]">{error}</p>
          </section>
        {:else if graphMatches.length === 0}
          <section class="rounded-lg border border-[#d6d0bf] bg-[#fffdf6] p-6" role="status">
            <h3 class="m-0 text-xl leading-snug text-[#191c1e]">No active matches to graph</h3>
            <p class="mt-2 text-sm leading-6 text-[#45464d]">Update the company profile or reload Business Benefits Finder data to populate the graph.</p>
          </section>
        {:else}
          <section class="grid grid-cols-[minmax(0,1fr)_340px] gap-6 max-[1040px]:grid-cols-1" aria-label="Interactive graph workspace">
            <div
              class={`rounded-lg border border-slate-200 bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)] ${
                isGraphFullscreen ? 'flex h-screen w-screen flex-col rounded-none border-0 shadow-none' : ''
              }`}
              bind:this={graphPanelElement}
            >
              <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
                <p class="m-0 text-sm leading-6 text-[#45464d]">
                  Drag nodes, scroll to zoom, and click an opportunity to inspect details.
                </p>
                <div class="flex items-center gap-2">
                  {#if loadingSemanticScores}
                    <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-800 uppercase">Refining scores</span>
                  {/if}
                  <button
                    aria-label={isGraphFullscreen ? 'Exit fullscreen graph view' : 'Maximize graph view'}
                    aria-pressed={isGraphFullscreen}
                    class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-[#191c1e] transition hover:bg-[#f2f4f6] focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-emerald-200"
                    title={isGraphFullscreen ? 'Exit fullscreen' : 'Maximize graph'}
                    type="button"
                    onclick={toggleGraphFullscreen}
                  >
                    <span class="material-symbols-outlined text-[20px]" aria-hidden="true">
                      {isGraphFullscreen ? 'close_fullscreen' : 'open_in_full'}
                    </span>
                  </button>
                </div>
              </div>

              {#if isGraphFullscreen}
                <div class="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_380px] gap-4 max-[900px]:grid-cols-1">
                  <div class="min-h-0 min-w-0">
                    <OpportunityForceGraph
                      nodes={graphNodes}
                      links={graphLinks}
                      selectedId={selectedNodeId}
                      fill
                      onSelect={(id) => {
                        selectedNodeId = id;
                      }}
                    />
                  </div>

                  <aside class="min-h-0 overflow-y-auto rounded-lg border border-slate-200 bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
                    {@render graphDetailsPanel()}
                  </aside>
                </div>
              {:else}
                <OpportunityForceGraph
                  nodes={graphNodes}
                  links={graphLinks}
                  selectedId={selectedNodeId}
                  onSelect={(id) => {
                    selectedNodeId = id;
                  }}
                />
              {/if}
            </div>

            <aside class="rounded-lg border border-slate-200 bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              {@render graphDetailsPanel()}
            </aside>
          </section>
        {/if}
      </div>
    </main>
  </div>
</div>
