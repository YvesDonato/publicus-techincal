<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/state';
  import {
    hydrateCachedGrantsResult,
    hydrateProgressiveCachedBenefitsResult,
    readCachedGrantsResult,
    type CachedBenefitsResult,
    type CachedGrantsResult
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
    fetchSemanticScoresForMatches,
    getSemanticRecordId,
    type SemanticScore,
    type SemanticScoreMap
  } from '$lib/client/semantic-scoring';
  import {
    fetchOpportunityAnalysis,
    fetchOpportunityFitJudgments,
    getOpportunityAnalysisCacheKey,
    getOpportunityFitJudgmentCacheKey,
    type OpportunityAnalysis,
    type OpportunityFitJudgment
  } from '$lib/client/opportunity-analysis';
  import {
    applyOpportunitySemanticScore as applySharedOpportunitySemanticScore,
    isCurrentlyAvailableOpportunity,
    scoreOpportunityBenefitRecord,
    scoreOpportunityGrantRecord
  } from '$lib/client/opportunity-matches';
  import { onMount } from 'svelte';

  type SortMode = 'score' | 'amount' | 'newest';
  type GenericRecord = Record<string, unknown>;
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
  type GrantQuery = {
    mode: 'first' | 'calendar-year';
    count: number;
    year: number | null;
    order: 'asc' | 'desc';
    endpoint: string;
  };
  type PersonaData = {
    grants: GrantRecord[];
    total: number | null;
    requested: number;
    grantsQuery: GrantQuery | null;
    error: string | null;
    filters: {
      source: 'grants' | 'innovation';
      year: number | null;
      count: number;
      sort: SortMode;
    };
    innovation: {
      requested: number;
      count: number;
      records: Record<string, unknown>[];
      source: string | null;
      endpoint: string | null;
      error: string | null;
    };
  };
  const DEFAULT_BACKEND_API_URL = '';
  const MAX_COUNT = 5000;
  const pageShellClass =
    'flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]';
  const profileCanvasClass = 'mx-auto w-full max-w-[1280px] px-6 py-12 max-md:px-4 max-md:py-7';
  const profileIntroClass = 'mb-12 flex items-end justify-between gap-6 max-lg:grid max-lg:items-start max-md:mb-7';
  const sortLinkClass =
    'inline-flex min-h-9 items-center justify-center rounded-full px-4 text-sm leading-none font-extrabold text-[#191c1e] no-underline transition hover:bg-[#f2f4f6] focus-visible:bg-[#f2f4f6]';
  const sortLinkActiveClass =
    'inline-flex min-h-9 items-center justify-center rounded-full bg-[#006c49] px-4 text-sm leading-none font-extrabold text-white no-underline shadow-sm';
  const secondaryButtonClass =
    'inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3.5 py-3 leading-none font-extrabold text-emerald-800 no-underline hover:bg-emerald-50 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-emerald-200';
  const compactButtonClass = `${secondaryButtonClass} min-h-9 px-3 py-2 text-sm`;
  const statePanelClass = 'mt-6 rounded-lg border border-[#d6d0bf] bg-[#fffdf6] p-6';
  const eyebrowClass = 'm-0 mb-3 text-xs font-bold tracking-normal text-emerald-700 uppercase';
  const cardShadowClass = 'shadow-[0_4px_20px_rgba(0,0,0,0.03)]';

  let props = $props<{ data?: Partial<PersonaData> }>();
  let clientData = $state<PersonaData | null>(null);
  const data = $derived(clientData ?? normalizeData(props.data));
  type ActivityKey =
    | 'research'
    | 'hiring'
    | 'equipment'
    | 'export'
    | 'facilities'
    | 'sustainability';
  type CompanyType = 'for-profit' | 'nonprofit' | 'academic' | 'public-sector';
  type EmployeeRange = '1-10' | '11-50' | '51-200' | '200+';
  type CompanyPersona = {
    legalEntityName: string;
    doingBusinessAs: string;
    incorporationDate: string;
    website: string;
    province: string;
    city: string;
    companyType: CompanyType;
    employeeRange: EmployeeRange;
    industry: string;
    subSector: string;
    keywords: string;
    fundingNeed: string;
    activities: Record<ActivityKey, boolean>;
  };
  type GrantMatch = {
    grant: GrantRecord;
    amount: number | null;
    matchScore: number;
    statusLabel: string;
    statusTone: 'likely' | 'review' | 'low';
    reasons: string[];
    risks: string[];
    nextActions: string[];
  };
  type BenefitMatch = {
    record: GenericRecord;
    amount: number | null;
    estimatedAmount: number | null;
    potentialFunding: number | null;
    historicalEvidenceCount: number;
    matchedKeywords: string[];
    matchScore: number;
    statusLabel: string;
    statusTone: 'likely' | 'review' | 'low';
    reasons: string[];
    risks: string[];
    nextActions: string[];
  };
  type ShortlistedOpportunity = {
    ref: string;
    match: BenefitMatch | null;
  };

  const companyTypes: { value: CompanyType; label: string }[] = [
    { value: 'for-profit', label: 'For-profit' },
    { value: 'nonprofit', label: 'Nonprofit' },
    { value: 'academic', label: 'Academic' },
    { value: 'public-sector', label: 'Public sector' }
  ];
  const provinceOptions = [
    { value: 'AB', label: 'Alberta' },
    { value: 'BC', label: 'British Columbia' },
    { value: 'MB', label: 'Manitoba' },
    { value: 'NB', label: 'New Brunswick' },
    { value: 'NL', label: 'Newfoundland and Labrador' },
    { value: 'NS', label: 'Nova Scotia' },
    { value: 'NT', label: 'Northwest Territories' },
    { value: 'NU', label: 'Nunavut' },
    { value: 'ON', label: 'Ontario' },
    { value: 'PE', label: 'Prince Edward Island' },
    { value: 'QC', label: 'Quebec' },
    { value: 'SK', label: 'Saskatchewan' },
    { value: 'YT', label: 'Yukon' }
  ];
  const employeeOptions: { value: EmployeeRange; label: string }[] = [
    { value: '1-10', label: '1 - 10' },
    { value: '11-50', label: '11 - 50' },
    { value: '51-200', label: '51 - 200' },
    { value: '200+', label: '200+' }
  ];
  const industryOptions = [
    { value: 'tech', label: 'Technology & Software', terms: ['technology', 'software', 'digital', 'data'] },
    { value: 'mfg', label: 'Manufacturing', terms: ['manufacturing', 'equipment', 'production'] },
    { value: 'agri', label: 'Agriculture', terms: ['agriculture', 'agri-food', 'farm'] },
    { value: 'health', label: 'Healthcare & Life Sciences', terms: ['health', 'life sciences', 'medical'] },
    { value: 'clean', label: 'CleanTech', terms: ['clean technology', 'cleantech', 'sustainability'] }
  ];
  const subSectorOptions = [
    { value: 'ai', label: 'Artificial Intelligence (AI)', terms: ['ai', 'artificial intelligence', 'machine learning'] },
    { value: 'saas', label: 'B2B SaaS', terms: ['saas', 'software', 'cloud'] },
    { value: 'cybersecurity', label: 'Cybersecurity', terms: ['cybersecurity', 'cyber security', 'security', 'privacy'] },
    { value: 'data', label: 'Data & Analytics', terms: ['data', 'analytics', 'business intelligence', 'reporting'] },
    { value: 'fintech', label: 'FinTech', terms: ['fintech', 'financial technology', 'payments', 'banking'] },
    { value: 'healthtech', label: 'HealthTech / MedTech', terms: ['healthtech', 'medtech', 'medical device', 'digital health'] },
    { value: 'biotech', label: 'Biotechnology', terms: ['biotechnology', 'biotech', 'life sciences', 'biomanufacturing'] },
    { value: 'advanced-mfg', label: 'Advanced Manufacturing', terms: ['advanced manufacturing', 'manufacturing', 'automation', 'production'] },
    { value: 'robotics', label: 'Robotics & Automation', terms: ['robotics', 'robot', 'automation', 'industrial automation'] },
    { value: 'hardware-iot', label: 'Hardware / IoT', terms: ['hardware', 'iot', 'internet of things', 'connected device'] },
    { value: 'agtech', label: 'AgTech / FoodTech', terms: ['agtech', 'foodtech', 'agriculture technology', 'food processing'] },
    { value: 'clean', label: 'CleanTech', terms: ['clean technology', 'energy', 'sustainability'] },
    { value: 'clean-energy', label: 'Clean Energy', terms: ['clean energy', 'renewable energy', 'solar', 'wind'] },
    { value: 'ev', label: 'Electric Vehicles & Batteries', terms: ['electric vehicle', 'ev', 'battery', 'charging'] },
    { value: 'circular', label: 'Circular Economy', terms: ['circular economy', 'recycling', 'waste reduction', 'reuse'] },
    { value: 'construction-tech', label: 'Construction Tech', terms: ['construction technology', 'proptech', 'building technology', 'retrofit'] },
    { value: 'aerospace', label: 'Aerospace', terms: ['aerospace', 'aviation', 'aircraft', 'space'] },
    { value: 'ocean', label: 'Ocean / Marine Tech', terms: ['ocean technology', 'marine', 'aquaculture', 'blue economy'] },
    { value: 'supply-chain', label: 'Supply Chain & Logistics', terms: ['supply chain', 'logistics', 'transportation', 'distribution'] },
    { value: 'digital-media', label: 'Digital Media & Gaming', terms: ['digital media', 'gaming', 'interactive media', 'content'] },
    { value: 'edtech', label: 'Education Technology', terms: ['edtech', 'education technology', 'learning', 'training'] },
    { value: 'social-impact', label: 'Social Impact', terms: ['social impact', 'community', 'inclusive', 'nonprofit'] },
    { value: 'accessibility', label: 'Accessibility Tech', terms: ['accessibility', 'accessible', 'disability'] },
    { value: 'export', label: 'Export Growth', terms: ['export', 'international', 'market'] }
  ];
  const activityOptions: { value: ActivityKey; label: string; terms: string[] }[] = [
    {
      value: 'research',
      label: 'Research & Development',
      terms: ['research', 'development', 'r&d', 'innovation', 'pilot']
    },
    { value: 'hiring', label: 'Hiring & Payroll', terms: ['hiring', 'employment', 'jobs', 'workforce', 'training'] },
    { value: 'equipment', label: 'Equipment Purchase', terms: ['equipment', 'machinery', 'capital', 'purchase'] },
    { value: 'export', label: 'Market Expansion', terms: ['export', 'international', 'market', 'commercialization'] },
    { value: 'facilities', label: 'Real Estate / Facility', terms: ['facility', 'facilities', 'building', 'infrastructure'] },
    {
      value: 'sustainability',
      label: 'Green / Sustainability',
      terms: ['green', 'sustainability', 'climate', 'emissions', 'energy']
    }
  ];
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
  const amountFields = ['amount', 'funding_amount', 'approved_amount', 'agreement_value', 'contribution', 'loan', 'value'];
  const locationFields = ['location', 'city', 'province', 'region', 'country'];
  const dateFields = ['deadline', 'closing_date', 'end_date', 'date', 'updated_at', 'modified'];
  const idFields = ['_id', 'id', 'record_id', 'project_id', 'application_id', 'token', 'reference', 'url'];

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
  const LIKELY_MATCH_THRESHOLD = 75;
  const PROFILE_STORAGE_KEY = 'publicus.companyProfile.v1';
  const SHORTLIST_STORAGE_KEY = 'publicus.shortlistedOpportunityRefs';
  const LIKELY_OPPORTUNITY_REFS_STORAGE_KEY = 'fundradar.opportunityMatchesLikelyRefs.v1';
  const INITIAL_VISIBLE_OPPORTUNITIES = 10;
  const OPPORTUNITY_PAGE_SIZE = 10;
  const BENEFIT_RECORD_WINDOW = 100;
  const HISTORICAL_GRANT_RECORD_WINDOW = 500;

  let persona = $state(createDefaultPersona());
  let likelyOnly = $state(false);
  let visibleOpportunityTarget = $state(INITIAL_VISIBLE_OPPORTUNITIES);
  let savedOpportunityRefs = $state<string[]>([]);
  let semanticScores = $state<SemanticScoreMap>({});
  let opportunityAnalyses = $state<Record<string, OpportunityAnalysis>>({});
  let opportunityAnalysisLoading = $state<Record<string, boolean>>({});
  let opportunityAnalysisErrors = $state<Record<string, string>>({});
  let opportunityFitJudgments = $state<Record<string, OpportunityFitJudgment>>({});
  let opportunityFitJudging = $state(false);
  let opportunityFitFilterAvailable = $state(false);
  let opportunityFitFilterMessage = $state('');
  let showLlmExcluded = $state(false);
  let lastOpportunityFitBatchKey = '';
  let analysisModalMatch = $state<BenefitMatch | null>(null);
  let comparisonRefs = $state<string[]>([]);
  let comparisonModalOpen = $state(false);
  let shortlistHydrated = $state(false);
  let profileHydrated = $state(false);
  let profileSaved = $state(false);
  let opportunitiesHydrated = $state(false);
  let newLikelyOpportunityCount = $state(0);

  const selectedActivities = $derived(
    activityOptions.filter((activity) => persona.activities[activity.value]).map((activity) => activity.value)
  );
  const personaKeywords = $derived(buildPersonaKeywords(persona, selectedActivities));
  const personaCompleteness = $derived(calculatePersonaCompleteness(persona, selectedActivities));
  const grantMatches = $derived(data.grants.map((grant) => scoreOpportunityGrantRecord(grant, persona)));
  const activeBenefitRecords = $derived(data.innovation.records.filter(isCurrentlyAvailableOpportunity));
  const ruleBenefitMatches = $derived(activeBenefitRecords.map((record) => scoreOpportunityBenefitRecord(record, persona, grantMatches)));
  const benefitMatches = $derived(
    ruleBenefitMatches.map((match, index) =>
      applySharedOpportunitySemanticScore(match, semanticScores[getSemanticRecordId(match.record, 'business-benefits', index)])
    )
  );
  const activeSort = $derived(parseSortMode(page.url.searchParams.get('sort')));
  const savedOpportunityRefSet = $derived(new Set(savedOpportunityRefs));
  const shortlistedOpportunities = $derived(
    savedOpportunityRefs.map(
      (ref): ShortlistedOpportunity => ({
        ref,
        match: benefitMatches.find((match) => getOpportunityRef(match.record) === ref) ?? null
      })
    )
  );
  const likelyMatchCount = $derived(benefitMatches.filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD).length);
  const sortedBenefitMatches = $derived(
    sortBenefitMatches(
      likelyOnly ? benefitMatches.filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD) : benefitMatches,
      activeSort
    )
  );
  const visibleCandidateBenefitMatches = $derived(sortedBenefitMatches.slice(0, visibleOpportunityTarget));
  const llmExcludedVisibleMatches = $derived(visibleCandidateBenefitMatches.filter(isLlmExcludedOpportunity));
  const visibleBenefitMatches = $derived(
    showLlmExcluded ? visibleCandidateBenefitMatches : visibleCandidateBenefitMatches.filter((match) => !isLlmExcludedOpportunity(match))
  );
  const canLoadMoreOpportunities = $derived(sortedBenefitMatches.length > visibleCandidateBenefitMatches.length);
  const topOpportunity = $derived(visibleBenefitMatches[0] ?? null);
  const remainingOpportunities = $derived(visibleBenefitMatches.slice(1));
  const totalMatchedCapital = $derived(getTotalMatchedCapital(visibleBenefitMatches));
  const historicalEvidenceCount = $derived(grantMatches.filter((match) => match.matchScore >= 55 && match.amount !== null).length);
  const applicantName = $derived(persona.doingBusinessAs || persona.legalEntityName || 'your company');
  const analysisModalAnalysis = $derived(analysisModalMatch ? getOpportunityAnalysis(analysisModalMatch) : null);
  const analysisModalFitJudgment = $derived(analysisModalMatch ? getActiveOpportunityFitJudgment(analysisModalMatch) : null);
  const analysisModalError = $derived(analysisModalMatch ? getOpportunityAnalysisError(analysisModalMatch) : '');
  const analysisModalLoading = $derived(analysisModalMatch ? isOpportunityAnalysisLoading(analysisModalMatch) : false);
  const comparisonMatches = $derived(
    comparisonRefs
      .map((ref) => benefitMatches.find((match) => getCompareRef(match) === ref) ?? null)
      .filter((match): match is BenefitMatch => match !== null)
  );
  const comparisonReady = $derived(comparisonMatches.length === 2);

  function createInitialData(): PersonaData {
    const filters = readClientFilters();
    const grantsQuery = buildClientGrantQuery(filters);

    return {
      grants: [],
      total: null,
      requested: filters.count,
      grantsQuery,
      error: null,
      filters,
      innovation: {
        requested: BENEFIT_RECORD_WINDOW,
        count: 0,
        records: [],
        source: null,
        endpoint: buildClientBenefitsEndpoint(BENEFIT_RECORD_WINDOW),
        error: null
      }
    };
  }

  function normalizeData(value: Partial<PersonaData> | undefined): PersonaData {
    const fallback = createInitialData();

    if (!value?.filters) {
      return fallback;
    }

    return {
      grants: Array.isArray(value.grants) ? value.grants : fallback.grants,
      total: typeof value.total === 'number' ? value.total : fallback.total,
      requested: typeof value.requested === 'number' ? value.requested : fallback.requested,
      grantsQuery: value.grantsQuery ?? fallback.grantsQuery,
      error: typeof value.error === 'string' ? value.error : null,
      filters: {
        source: value.filters.source === 'innovation' ? 'innovation' : 'grants',
        year: typeof value.filters.year === 'number' ? value.filters.year : null,
        count: typeof value.filters.count === 'number' ? value.filters.count : fallback.filters.count,
        sort: parseSortMode(value.filters.sort ?? null)
      },
      innovation: {
        ...fallback.innovation,
        ...(value.innovation ?? {}),
        endpoint: value.innovation?.endpoint ?? fallback.innovation.endpoint
      }
    };
  }

  function readClientFilters(): PersonaData['filters'] {
    const params = browser ? new URLSearchParams(window.location.search) : new URLSearchParams();

    return {
      source: 'grants',
      year: parseCalendarYear(params.get('year')),
      count: parseBoundedInteger(params.get('count'), HISTORICAL_GRANT_RECORD_WINDOW, 1, MAX_COUNT),
      sort: parseSortMode(params.get('sort'))
    };
  }

  function parseBoundedInteger(value: string | null, fallback: number, minimum: number, maximum: number): number {
    if (!value) {
      return fallback;
    }

    const parsed = Number(value);
    return Number.isInteger(parsed) ? Math.min(maximum, Math.max(minimum, parsed)) : fallback;
  }

  function parseCalendarYear(value: string | null): number | null {
    if (!value) {
      return null;
    }

    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 1800 && parsed <= 2200 ? parsed : null;
  }

  function parseSortMode(value: string | null): SortMode {
    if (value === 'amount' || value === 'newest') {
      return value;
    }

    return 'score';
  }

  function buildClientGrantQuery(filters: PersonaData['filters']): GrantQuery {
    const params = new URLSearchParams({
      limit: filters.count.toString(),
      include_total: filters.year === null && filters.sort === 'score' ? 'true' : 'false'
    });

    if (filters.year !== null) {
      params.set('year', filters.year.toString());
    }

    if (filters.sort !== 'score') {
      params.set('sort', filters.sort);
    }

    return {
      mode: filters.year === null ? 'first' : 'calendar-year',
      count: filters.count,
      year: filters.year,
      order: filters.sort === 'newest' ? 'desc' : 'asc',
      endpoint: `${DEFAULT_BACKEND_API_URL}/api/grants?${params.toString()}`
    };
  }

  function buildClientBenefitsEndpoint(count: number): string {
    return `${DEFAULT_BACKEND_API_URL}/api/business-benefits/first/${count}`;
  }

  onMount(() => {
    savedOpportunityRefs = readSavedOpportunityRefs();
    shortlistHydrated = true;
    void hydrateInitialPage();
  });

  async function hydrateInitialPage() {
    await hydrateProfile();
    await hydrateOpportunityData();
  }

  async function hydrateProfile() {
    persona = readStoredPersona() ?? (await readServerPersona()) ?? createDefaultPersona();
    profileHydrated = true;
  }

  async function hydrateOpportunityData() {
    const grantsEndpoint = data.grantsQuery?.endpoint;
    const benefitsEndpoint = data.innovation.endpoint ?? buildClientBenefitsEndpoint(BENEFIT_RECORD_WINDOW);
    const cachedGrants = grantsEndpoint ? readCachedGrantsResult(grantsEndpoint, data.requested) : null;
    const feedState = await fetchBusinessBenefitsFeedState(DEFAULT_BACKEND_API_URL);
    const previousFeedState = readStoredBusinessBenefitsFeedState();
    const forceBenefitsRefresh = shouldRefreshBusinessBenefitsCache(previousFeedState, feedState);
    const canReportNewFeedMatches = forceBenefitsRefresh && getBusinessBenefitsFeedMarker(previousFeedState) !== null;

    if (cachedGrants) {
      applyOpportunityResults(cachedGrants, null);
    }

    const [grantsResult, benefitsResult] = await Promise.all([
      grantsEndpoint
        ? hydrateCachedGrantsResult(grantsEndpoint, data.requested)
        : Promise.resolve<CachedGrantsResult>({
            requested: 0,
            count: 0,
            records: [],
            total: null,
            endpoint: '',
            error: null
          }),
      hydrateProgressiveCachedBenefitsResult(benefitsEndpoint, BENEFIT_RECORD_WINDOW, {
        forceRefresh: forceBenefitsRefresh
      })
    ]);

    applyOpportunityResults(grantsResult, benefitsResult);
    if (feedState) {
      writeStoredBusinessBenefitsFeedState(feedState);
    }
    updateLikelyOpportunityNotice(grantsResult, benefitsResult, canReportNewFeedMatches);
    opportunitiesHydrated = true;
    void hydrateSemanticOpportunityScores();
  }

  function applyOpportunityResults(grantsResult: CachedGrantsResult, benefitsResult: CachedBenefitsResult | null) {
    clientData = {
      ...data,
      grants: grantsResult.records as GrantRecord[],
      total: grantsResult.total,
      requested: grantsResult.requested,
      error: grantsResult.error,
      innovation: benefitsResult
        ? {
            requested: benefitsResult.requested,
            count: benefitsResult.count,
            records: benefitsResult.records,
            source: benefitsResult.source,
            endpoint: benefitsResult.endpoint,
            error: benefitsResult.error
          }
        : data.innovation
    };
  }

  function updateLikelyOpportunityNotice(
    grantsResult: CachedGrantsResult,
    benefitsResult: CachedBenefitsResult,
    canReportNewFeedMatches: boolean
  ) {
    const historicalMatches = (grantsResult.records as GrantRecord[]).map((grant) => scoreOpportunityGrantRecord(grant, persona));
    const likelyRefs = benefitsResult.records
      .filter(isCurrentlyAvailableOpportunity)
      .map((record) => scoreOpportunityBenefitRecord(record, persona, historicalMatches))
      .filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD)
      .map(getBenefitMatchRef)
      .filter((value): value is string => value !== null);
    const previousLikelyRefs = readStoredStringList(LIKELY_OPPORTUNITY_REFS_STORAGE_KEY);
    const previousSet = new Set(previousLikelyRefs);

    newLikelyOpportunityCount =
      canReportNewFeedMatches && previousLikelyRefs.length > 0
        ? likelyRefs.filter((ref) => !previousSet.has(ref)).length
        : 0;
    writeStoredStringList(LIKELY_OPPORTUNITY_REFS_STORAGE_KEY, likelyRefs);
  }

  $effect(() => {
    if (!browser || !profileHydrated) {
      return;
    }

    profileSaved = false;
  });

  $effect(() => {
    if (!browser || !shortlistHydrated) {
      return;
    }

    persistSavedOpportunityRefs(savedOpportunityRefs);
  });

  $effect(() => {
    if (!browser || !opportunitiesHydrated || visibleCandidateBenefitMatches.length === 0) {
      return;
    }

    const batchKey = visibleCandidateBenefitMatches.map(getOpportunityFitJudgmentKey).join('|');
    if (!batchKey || batchKey === lastOpportunityFitBatchKey) {
      return;
    }

    lastOpportunityFitBatchKey = batchKey;
    void judgeVisibleOpportunityFits(visibleCandidateBenefitMatches);
  });

  function createDefaultPersona(): CompanyPersona {
    return {
      legalEntityName: 'AccessBuild AI Inc.',
      doingBusinessAs: 'AccessBuild AI',
      incorporationDate: '2021-05-14',
      website: 'https://example.com',
      province: 'ON',
      city: 'Ottawa',
      companyType: 'for-profit',
      employeeRange: '11-50',
      industry: 'tech',
      subSector: 'ai',
      keywords: 'accessibility, public sector',
      fundingNeed: '250000',
      activities: {
        research: true,
        hiring: false,
        equipment: false,
        export: false,
        facilities: false,
        sustainability: false
      }
    };
  }

  function createEmptyPersona(): CompanyPersona {
    return {
      legalEntityName: '',
      doingBusinessAs: '',
      incorporationDate: '',
      website: '',
      province: '',
      city: '',
      companyType: 'for-profit',
      employeeRange: '11-50',
      industry: '',
      subSector: '',
      keywords: '',
      fundingNeed: '',
      activities: {
        research: false,
        hiring: false,
        equipment: false,
        export: false,
        facilities: false,
        sustainability: false
      }
    };
  }

  function resetPersona() {
    persona = createDefaultPersona();
    profileSaved = false;
  }

  function clearPersona() {
    persona = createEmptyPersona();
    likelyOnly = false;
    profileSaved = false;
  }

  function parseMoney(value: unknown): number | null {
    if (value === null || value === undefined || value === '') {
      return null;
    }

    const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function formatMoney(value: string | null): string {
    const parsed = parseMoney(value);
    return parsed === null ? 'Value unavailable' : moneyFormatter.format(parsed);
  }

  function formatMoneyValue(value: number | null): string {
    return value === null || value <= 0 ? 'Unavailable' : moneyFormatter.format(value);
  }

  function formatDate(value: string | null): string {
    if (!value) {
      return 'Date unavailable';
    }

    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
  }

  function formatLocation(city: string | null, province: string | null): string {
    return [city, province].filter(Boolean).join(', ') || 'Location unavailable';
  }

  function parseListInput(value: string): string[] {
    return unique(
      value
        .split(/[,;\n]/)
        .map((item) => normalizeTerm(item))
        .filter((item) => item.length > 1)
    );
  }

  function normalizeTerm(value: string): string {
    return value.trim().toLowerCase().replace(/\s+/g, ' ');
  }

  function unique(values: string[]): string[] {
    return [...new Set(values)];
  }

  function buildPersonaKeywords(profile: CompanyPersona, activities: ActivityKey[]): string[] {
    const manualKeywords = parseListInput(profile.keywords);
    const activityKeywords = activities.flatMap((activity) => {
      const option = activityOptions.find((item) => item.value === activity);
      return option ? option.terms : [];
    });
    const industry = industryOptions.find((item) => item.value === profile.industry);
    const subSector = subSectorOptions.find((item) => item.value === profile.subSector);
    const businessName = profile.doingBusinessAs || profile.legalEntityName;

    return unique(
      [
        ...manualKeywords,
        businessName,
        industry?.label,
        ...(industry?.terms ?? []),
        subSector?.label,
        ...(subSector?.terms ?? []),
        ...activityKeywords
      ]
        .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
        .map(normalizeTerm)
    );
  }

  function calculatePersonaCompleteness(profile: CompanyPersona, activities: ActivityKey[]): number {
    const fields = [
      profile.legalEntityName,
      profile.incorporationDate,
      profile.website,
      profile.province,
      profile.city,
      profile.companyType,
      profile.employeeRange,
      profile.industry,
      profile.subSector,
      profile.keywords,
      profile.fundingNeed,
      activities.length > 0 ? 'activities' : ''
    ];
    const complete = fields.filter((field) => field.trim().length > 0).length;
    return Math.round((complete / fields.length) * 100);
  }

  function grantText(grant: GrantRecord): string {
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
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
  }

  function termAppearsInText(text: string, term: string): boolean {
    const normalizedTerm = normalizeTerm(term);

    if (!normalizedTerm) {
      return false;
    }

    if (normalizedTerm.includes(' ')) {
      return text.includes(normalizedTerm);
    }

    return new RegExp(`\\b${escapeRegExp(normalizedTerm)}\\b`, 'i').test(text);
  }

  function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function scoreGrant(grant: GrantRecord, profile: CompanyPersona, keywords: string[]): GrantMatch {
    const reasons: string[] = [];
    const risks: string[] = [];
    const nextActions: string[] = [];
    const text = grantText(grant);
    const amount = parseMoney(grant.agreement_value);
    const fundingNeed = parseMoney(profile.fundingNeed);
    const province = profile.province.trim().toUpperCase();
    const city = normalizeTerm(profile.city);
    let score = keywords.length > 0 || province || fundingNeed ? 25 : 35;

    const matchedKeywords = keywords.filter((keyword) => termAppearsInText(text, keyword));
    if (matchedKeywords.length > 0) {
      score += Math.min(34, matchedKeywords.length * 7);
      reasons.push(`Matches profile terms: ${matchedKeywords.slice(0, 5).join(', ')}.`);
    } else if (keywords.length > 0) {
      risks.push('No direct keyword overlap with the current grant record.');
    } else {
      reasons.push('Add industries and activities to make this score more specific.');
    }

    if (province && grant.recipient_province?.toUpperCase() === province) {
      score += 18;
      reasons.push(`Record is associated with ${province}.`);
    } else if (province && grant.recipient_province) {
      risks.push(`Record location is ${grant.recipient_province}, not ${province}.`);
    }

    if (city && grant.recipient_city && normalizeTerm(grant.recipient_city) === city) {
      score += 6;
      reasons.push(`City signal matches ${grant.recipient_city}.`);
    }

    if (amount !== null && fundingNeed !== null) {
      if (amount >= fundingNeed) {
        score += 12;
        reasons.push(`Grant value can cover the ${moneyFormatter.format(fundingNeed)} target.`);
      } else {
        score += 4;
        risks.push(`Grant value is below the ${moneyFormatter.format(fundingNeed)} target.`);
      }

      if (amount >= fundingNeed * 0.25 && amount <= fundingNeed * 4) {
        score += 6;
        reasons.push('Funding size is in a practical range for this company profile.');
      }
    }

    if (profile.companyType === 'academic' && /university|college|research/.test(text)) {
      score += 10;
      reasons.push('Academic/research language appears in the record.');
    } else if (profile.companyType === 'nonprofit' && /society|association|institute|foundation|council/.test(text)) {
      score += 8;
      reasons.push('Nonprofit-style recipient language appears in the record.');
    } else if (profile.companyType === 'for-profit') {
      risks.push('For-profit eligibility is not explicit in this record.');
    } else if (profile.companyType === 'public-sector') {
      risks.push('Public-sector eligibility needs confirmation from the program guide.');
    }

    if (!grant.agreement_start_date) {
      risks.push('Start date is missing from this record.');
    }

    if (matchedKeywords.length > 0) {
      nextActions.push(`Frame the project around ${matchedKeywords.slice(0, 2).join(' and ')}.`);
    }

    if (amount !== null && fundingNeed !== null) {
      nextActions.push(`Compare the budget request with the ${moneyFormatter.format(amount)} historical value.`);
    }

    if (profile.website) {
      nextActions.push('Use the company website to draft a short applicant description.');
    }

    nextActions.push('Confirm applicant type, deadline, and eligible activities in the program guide.');

    const matchScore = Math.max(0, Math.min(100, Math.round(score)));
    const status =
      matchScore >= LIKELY_MATCH_THRESHOLD
        ? { label: 'Likely match', tone: 'likely' as const }
        : matchScore >= 55
          ? { label: 'Worth review', tone: 'review' as const }
          : { label: 'Low confidence', tone: 'low' as const };

    return {
      grant,
      amount,
      matchScore,
      statusLabel: status.label,
      statusTone: status.tone,
      reasons: reasons.slice(0, 4),
      risks: (risks.length > 0 ? risks : ['Eligibility details are not included in this first-record view.']).slice(0, 3),
      nextActions: unique(nextActions).slice(0, 3)
    };
  }

  function scoreBenefit(
    record: GenericRecord,
    profile: CompanyPersona,
    keywords: string[],
    historicalMatches: GrantMatch[]
  ): BenefitMatch {
    const reasons: string[] = [];
    const risks: string[] = [];
    const nextActions: string[] = [];
    const text = genericRecordText(record);
    const amount = parseMoneyFromRecord(record);
    const fundingNeed = parseMoney(profile.fundingNeed);
    const province = normalizeTerm(profile.province);
    const city = normalizeTerm(profile.city);
    let score = keywords.length > 0 || province || fundingNeed ? 30 : 45;

    const matchedKeywords = keywords.filter((keyword) => termAppearsInText(text, keyword));
    if (matchedKeywords.length > 0) {
      score += Math.min(40, matchedKeywords.length * 8);
      reasons.push(`Matches profile terms: ${matchedKeywords.slice(0, 5).join(', ')}.`);
    } else if (keywords.length > 0) {
      risks.push('No direct keyword overlap with this active opportunity.');
    }

    if (province && termAppearsInText(text, province)) {
      score += 10;
      reasons.push(`Opportunity text includes ${profile.province.toUpperCase()}.`);
    }

    if (city && termAppearsInText(text, city)) {
      score += 6;
      reasons.push(`Opportunity text includes ${profile.city}.`);
    }

    if (amount !== null && fundingNeed !== null) {
      score += amount >= fundingNeed ? 10 : 4;
      reasons.push('Published amount can be compared with the profile funding target.');
    }

    addCompanyTypeSignals(profile, text, reasons, risks, (points) => {
      score += points;
    });

    const historicalEvidence = findHistoricalEvidence(record, historicalMatches, keywords, matchedKeywords);
    const historicalAmounts = historicalEvidence
      .map((match) => match.amount)
      .filter((value): value is number => value !== null && value > 0);
    const estimatedAmount = amount === null ? median(historicalAmounts) : null;
    const potentialFunding = amount ?? estimatedAmount;

    if (historicalEvidence.length > 0) {
      const strongEvidenceCount = historicalEvidence.filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD).length;
      score += Math.min(18, historicalEvidence.length * 3 + strongEvidenceCount * 2);
      reasons.push(
        `${historicalEvidence.length} similar historical funding ${historicalEvidence.length === 1 ? 'record supports' : 'records support'} this match.`
      );

      if (estimatedAmount !== null) {
        reasons.push('Potential funding is estimated from the median similar historical award.');
      }
    } else {
      risks.push('No similar historical grant records found in the loaded evidence window.');
    }

    if (potentialFunding !== null && fundingNeed !== null && potentialFunding >= fundingNeed * 0.25 && potentialFunding <= fundingNeed * 4) {
      score += 5;
      reasons.push('Potential funding is in a practical range for this profile.');
    }

    nextActions.push('Confirm deadline, applicant type, and eligible costs on the official program page.');
    if (matchedKeywords.length > 0) {
      nextActions.push(`Frame the application around ${matchedKeywords.slice(0, 2).join(' and ')}.`);
    }
    if (potentialFunding !== null) {
      nextActions.push(`Compare the project budget with the ${moneyFormatter.format(potentialFunding)} funding signal.`);
    }

    const matchScore = Math.max(0, Math.min(100, Math.round(score)));
    const status =
      matchScore >= LIKELY_MATCH_THRESHOLD
        ? { label: 'Likely match', tone: 'likely' as const }
        : matchScore >= 55
          ? { label: 'Worth review', tone: 'review' as const }
          : { label: 'Low confidence', tone: 'low' as const };

    return {
      record,
      amount,
      estimatedAmount,
      potentialFunding,
      historicalEvidenceCount: historicalEvidence.length,
      matchedKeywords,
      matchScore,
      statusLabel: status.label,
      statusTone: status.tone,
      reasons: unique(reasons).slice(0, 4),
      risks: unique(risks).slice(0, 3),
      nextActions: unique(nextActions).slice(0, 3)
    };
  }

  function findHistoricalEvidence(
    benefit: GenericRecord,
    historicalMatches: GrantMatch[],
    keywords: string[],
    matchedBenefitKeywords: string[]
  ): GrantMatch[] {
    const benefitText = genericRecordText(benefit);
    const profileProvince = persona.province.trim().toUpperCase();
    const activeTerms = selectedActivities.flatMap((activity) => {
      const option = activityOptions.find((item) => item.value === activity);
      return option ? option.terms : [];
    });
    const comparisonTerms = unique([...matchedBenefitKeywords, ...keywords.slice(0, 8), ...activeTerms]);

    return historicalMatches
      .filter((match) => {
        if (match.matchScore < 55 || match.amount === null) {
          return false;
        }

        const historicalText = grantText(match.grant);
        const sharedTerm = comparisonTerms.some(
          (term) => termAppearsInText(benefitText, term) && termAppearsInText(historicalText, term)
        );
        const sharedLocation =
          profileProvince.length > 0 &&
          match.grant.recipient_province?.toUpperCase() === profileProvince &&
          termAppearsInText(benefitText, profileProvince);
        const sharedProgramLanguage = [getRecordFieldValue(benefit, subtitleFields), getRecordFieldValue(benefit, titleFields)]
          .filter((value): value is string => value !== null)
          .some((value) => normalizeTerm(value).split(' ').some((term) => term.length > 3 && termAppearsInText(historicalText, term)));

        return sharedTerm || sharedLocation || sharedProgramLanguage;
      })
      .sort((left, right) => right.matchScore - left.matchScore)
      .slice(0, 25);
  }

  function sortGrantMatches(matches: GrantMatch[], mode: SortMode): GrantMatch[] {
    return [...matches].sort((left, right) => {
      if (mode === 'amount') {
        return (right.amount ?? 0) - (left.amount ?? 0);
      }

      if (mode === 'newest') {
        return getGrantDateValue(right.grant) - getGrantDateValue(left.grant);
      }

      return right.matchScore - left.matchScore;
    });
  }

  function sortBenefitMatches(matches: BenefitMatch[], mode: SortMode): BenefitMatch[] {
    return [...matches].sort((left, right) => {
      if (mode === 'amount') {
        return (right.potentialFunding ?? 0) - (left.potentialFunding ?? 0);
      }

      if (mode === 'newest') {
        return getBenefitDateValue(right.record) - getBenefitDateValue(left.record);
      }

      return right.matchScore - left.matchScore;
    });
  }

  function addCompanyTypeSignals(
    profile: CompanyPersona,
    text: string,
    reasons: string[],
    risks: string[],
    addScore: (points: number) => void
  ) {
    if (profile.companyType === 'academic' && /university|college|research|academic/.test(text)) {
      addScore(10);
      reasons.push('Academic or research language appears in the opportunity.');
    } else if (profile.companyType === 'nonprofit' && /non.?profit|society|association|institute|foundation|council/.test(text)) {
      addScore(8);
      reasons.push('Nonprofit-style language appears in the opportunity.');
    } else if (profile.companyType === 'for-profit' && /business|company|sme|small and medium|enterprise|commercial/.test(text)) {
      addScore(8);
      reasons.push('Business eligibility language appears in the opportunity.');
    } else if (profile.companyType === 'public-sector' && /municipal|government|public sector|community/.test(text)) {
      addScore(8);
      reasons.push('Public-sector language appears in the opportunity.');
    } else {
      risks.push('Applicant type eligibility needs confirmation.');
    }
  }

  function isCurrentlyAvailableBenefit(record: GenericRecord): boolean {
    const text = genericRecordText(record);
    return !/\b(closed|expired|inactive|archived|not accepting|no longer accepting|application closed)\b/i.test(text);
  }

  function genericRecordText(record: GenericRecord): string {
    return Object.entries(record)
      .map(([key, value]) => `${formatFieldLabel(key)} ${key} ${valueToSearchText(value)}`)
      .join(' ')
      .toLowerCase();
  }

  function parseMoneyFromRecord(record: GenericRecord): number | null {
    for (const [key, value] of Object.entries(record)) {
      if (/amount|funding|contribution|grant|loan|value/i.test(key)) {
        const parsed = parseMoney(value);
        if (parsed !== null) {
          return parsed;
        }
      }
    }

    return null;
  }

  function getBenefitDateValue(record: GenericRecord): number {
    const dateValue = getRecordFieldValue(record, dateFields);

    if (!dateValue) {
      return 0;
    }

    const parsed = new Date(dateValue.includes('T') ? dateValue : `${dateValue}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function median(values: number[]): number | null {
    if (values.length === 0) {
      return null;
    }

    const sorted = [...values].sort((left, right) => left - right);
    const midpoint = Math.floor(sorted.length / 2);

    return sorted.length % 2 === 0 ? Math.round((sorted[midpoint - 1] + sorted[midpoint]) / 2) : sorted[midpoint];
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

  function formatFieldLabel(key: string): string {
    return key
      .replace(/^_+/, '')
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }

  function findField(record: GenericRecord, candidates: string[]): { key: string; value: unknown } | null {
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

  function getGrantDateValue(grant: GrantRecord): number {
    if (!grant.agreement_start_date) {
      return 0;
    }

    const parsed = new Date(`${grant.agreement_start_date}T00:00:00`).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function getGrantRef(grant: GrantRecord): string | null {
    const ref = grant.ref_number?.trim();
    return ref && ref.length > 0 ? ref : null;
  }

  function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  function readStringField(record: Record<string, unknown>, key: keyof CompanyPersona, fallback: string): string {
    const value = record[key];
    return typeof value === 'string' ? value : fallback;
  }

  function readPersonaRecord(parsed: Record<string, unknown>): CompanyPersona {
      const defaults = createDefaultPersona();
      const activities = isRecord(parsed.activities) ? parsed.activities : {};
      const companyType = readStringField(parsed, 'companyType', defaults.companyType);
      const employeeRange = readStringField(parsed, 'employeeRange', defaults.employeeRange);

      return {
        legalEntityName: readStringField(parsed, 'legalEntityName', defaults.legalEntityName),
        doingBusinessAs: readStringField(parsed, 'doingBusinessAs', defaults.doingBusinessAs),
        incorporationDate: readStringField(parsed, 'incorporationDate', defaults.incorporationDate),
        website: readStringField(parsed, 'website', defaults.website),
        province: readStringField(parsed, 'province', defaults.province),
        city: readStringField(parsed, 'city', defaults.city),
        companyType: companyTypes.some((item) => item.value === companyType) ? (companyType as CompanyType) : defaults.companyType,
        employeeRange: employeeOptions.some((item) => item.value === employeeRange)
          ? (employeeRange as EmployeeRange)
          : defaults.employeeRange,
        industry: readStringField(parsed, 'industry', defaults.industry),
        subSector: readStringField(parsed, 'subSector', defaults.subSector),
        keywords: readStringField(parsed, 'keywords', defaults.keywords),
        fundingNeed: readStringField(parsed, 'fundingNeed', defaults.fundingNeed),
        activities: {
          research: activities.research === true,
          hiring: activities.hiring === true,
          equipment: activities.equipment === true,
          export: activities.export === true,
          facilities: activities.facilities === true,
          sustainability: activities.sustainability === true
        }
      };
  }

  async function readServerPersona(): Promise<CompanyPersona | null> {
    if (!browser) {
      return null;
    }

    try {
      const response = await fetch('/dashboard/persona/profile');
      if (!response.ok) {
        return null;
      }

      const payload: unknown = await response.json();
      if (!isRecord(payload) || !isRecord(payload.profile)) {
        return null;
      }

      return readPersonaRecord(payload.profile);
    } catch {
      return null;
    }
  }

  function readStoredPersona(): CompanyPersona | null {
    if (!browser) {
      return null;
    }

    try {
      const rawValue = localStorage.getItem(PROFILE_STORAGE_KEY);
      const parsed = rawValue ? JSON.parse(rawValue) : null;

      if (!isRecord(parsed)) {
        return null;
      }

      return readPersonaRecord(parsed);
    } catch {
      return null;
    }
  }

  async function saveServerPersona(profile: CompanyPersona) {
    const response = await fetch('/dashboard/persona/profile', {
      method: 'PUT',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify(profile)
    });

    if (!response.ok) {
      throw new Error('Could not save company profile.');
    }

    try {
      localStorage.removeItem(PROFILE_STORAGE_KEY);
    } catch {
      // localStorage can be unavailable in private windows or locked-down browsers.
    }
  }

  async function saveAndContinue() {
    if (browser) {
      await saveServerPersona(persona);
      profileSaved = true;
      document.getElementById('recommendations-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function readSavedOpportunityRefs(): string[] {
    if (!browser) {
      return [];
    }

    try {
      const rawValue = localStorage.getItem(SHORTLIST_STORAGE_KEY);
      const parsed = rawValue ? JSON.parse(rawValue) : [];

      if (!Array.isArray(parsed)) {
        return [];
      }

      return unique(
        parsed
          .filter((item): item is string => typeof item === 'string')
          .map((item) => item.trim())
          .filter(Boolean)
      );
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

  function toggleOpportunitySaved(match: BenefitMatch) {
    const ref = getOpportunityRef(match.record);

    if (!ref) {
      return;
    }

    savedOpportunityRefs = savedOpportunityRefSet.has(ref)
      ? savedOpportunityRefs.filter((savedRef) => savedRef !== ref)
      : [...savedOpportunityRefs, ref];
  }

  function toggleOpportunityComparison(match: BenefitMatch | null) {
    if (!match) {
      return;
    }

    const ref = getCompareRef(match);

    if (comparisonRefs.includes(ref)) {
      comparisonRefs = comparisonRefs.filter((selectedRef) => selectedRef !== ref);
      comparisonModalOpen = false;
      return;
    }

    comparisonRefs = comparisonRefs.length >= 2 ? [comparisonRefs[1], ref] : [...comparisonRefs, ref];
    comparisonModalOpen = comparisonRefs.length === 2;
  }

  function isOpportunitySelectedForComparison(match: BenefitMatch): boolean {
    return comparisonRefs.includes(getCompareRef(match));
  }

  function getComparisonButtonLabel(match: BenefitMatch | null): string {
    if (!match) {
      return 'Compare';
    }

    return isOpportunitySelectedForComparison(match) ? 'Selected' : comparisonRefs.length >= 2 ? 'Replace' : 'Compare';
  }

  function clearComparison() {
    comparisonRefs = [];
    comparisonModalOpen = false;
  }

  function openComparisonModal() {
    if (comparisonReady) {
      comparisonModalOpen = true;
    }
  }

  function closeComparisonModal() {
    comparisonModalOpen = false;
  }

  async function judgeVisibleOpportunityFits(matches: BenefitMatch[]) {
    if (!browser || matches.length === 0) {
      return;
    }

    opportunityFitJudging = true;
    opportunityFitFilterMessage = '';

    try {
      const descriptions = Object.fromEntries(
        matches.map((match) => [getBenefitMatchRef(match) ?? getOpportunityTitle(match), getOpportunityDescription(match)])
      );
      const result = await fetchOpportunityFitJudgments({
        backendApiUrl: getBackendApiUrl(data.innovation.endpoint),
        profile: persona,
        matches,
        descriptions
      });

      opportunityFitJudgments = {
        ...opportunityFitJudgments,
        ...result.judgments
      };
      opportunityFitFilterAvailable = result.filter_available;
      opportunityFitFilterMessage = result.filter_available ? '' : result.unavailable_reason ?? 'LLM fit filtering is unavailable.';
    } catch (error) {
      opportunityFitFilterMessage = error instanceof Error ? error.message : 'LLM fit filtering is unavailable.';
    } finally {
      opportunityFitJudging = false;
    }
  }

  function retryOpportunityFitFilter() {
    lastOpportunityFitBatchKey = '';
    void judgeVisibleOpportunityFits(visibleCandidateBenefitMatches);
  }

  async function analyzeOpportunity(match: BenefitMatch, forceRefresh = false) {
    if (!browser) {
      return;
    }

    const loadingKey = getOpportunityAnalysisLoadingKey(match);
    if (opportunityAnalysisLoading[loadingKey]) {
      return;
    }

    opportunityAnalysisLoading = { ...opportunityAnalysisLoading, [loadingKey]: true };
    opportunityAnalysisErrors = { ...opportunityAnalysisErrors, [loadingKey]: '' };

    try {
      const fitJudgment = await ensureOpportunityFitJudgment(match);
      const key = getOpportunityAnalysisKey(match, fitJudgment);
      const analysis = await fetchOpportunityAnalysis({
        backendApiUrl: getBackendApiUrl(data.innovation.endpoint),
        profile: persona,
        match,
        description: getOpportunityDescription(match),
        fitJudgment,
        forceRefresh
      });

      opportunityAnalyses = { ...opportunityAnalyses, [key]: analysis };
    } catch (error) {
      opportunityAnalysisErrors = {
        ...opportunityAnalysisErrors,
        [loadingKey]: error instanceof Error ? error.message : 'Could not analyze this opportunity.'
      };
    } finally {
      opportunityAnalysisLoading = { ...opportunityAnalysisLoading, [loadingKey]: false };
    }
  }

  async function ensureOpportunityFitJudgment(match: BenefitMatch): Promise<OpportunityFitJudgment | null> {
    const existing = getOpportunityFitJudgment(match);
    if ((existing && opportunityFitFilterAvailable) || !browser) {
      return existing;
    }
    if (existing && opportunityFitFilterMessage) {
      return null;
    }

    try {
      const description = getOpportunityDescription(match);
      const result = await fetchOpportunityFitJudgments({
        backendApiUrl: getBackendApiUrl(data.innovation.endpoint),
        profile: persona,
        matches: [match],
        descriptions: {
          [getBenefitMatchRef(match) ?? getOpportunityTitle(match)]: description
        }
      });

      opportunityFitJudgments = {
        ...opportunityFitJudgments,
        ...result.judgments
      };
      opportunityFitFilterAvailable = opportunityFitFilterAvailable || result.filter_available;
      if (!result.filter_available && !opportunityFitFilterAvailable) {
        opportunityFitFilterMessage = result.unavailable_reason ?? 'LLM fit filtering is unavailable.';
      }

      return result.filter_available ? result.judgments[getOpportunityFitJudgmentKey(match)] ?? null : null;
    } catch {
      return null;
    }
  }

  function openOpportunityAnalysisModal(match: BenefitMatch) {
    analysisModalMatch = match;

    if (!getOpportunityAnalysis(match) && !isOpportunityAnalysisLoading(match)) {
      void analyzeOpportunity(match);
    }
  }

  function closeOpportunityAnalysisModal() {
    analysisModalMatch = null;
  }

  function refreshOpportunityAnalysisModal() {
    if (analysisModalMatch && !isOpportunityAnalysisLoading(analysisModalMatch)) {
      void analyzeOpportunity(analysisModalMatch, true);
    }
  }

  function handleAnalysisModalKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape') {
      return;
    }

    if (analysisModalMatch) {
      closeOpportunityAnalysisModal();
    }

    if (comparisonModalOpen) {
      closeComparisonModal();
    }
  }

  function handleAnalysisBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeOpportunityAnalysisModal();
    }
  }

  function handleComparisonBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeComparisonModal();
    }
  }

  function getOpportunityFitJudgmentKey(match: BenefitMatch): string {
    return getOpportunityFitJudgmentCacheKey(persona, match, getOpportunityDescription(match));
  }

  function getOpportunityFitJudgment(match: BenefitMatch): OpportunityFitJudgment | null {
    return opportunityFitJudgments[getOpportunityFitJudgmentKey(match)] ?? null;
  }

  function getActiveOpportunityFitJudgment(match: BenefitMatch): OpportunityFitJudgment | null {
    return opportunityFitFilterAvailable ? getOpportunityFitJudgment(match) : null;
  }

  function isLlmExcludedOpportunity(match: BenefitMatch): boolean {
    const judgment = getOpportunityFitJudgment(match);
    return opportunityFitFilterAvailable && judgment?.should_show === false;
  }

  function getOpportunityFitBadgeLabel(match: BenefitMatch): string {
    const judgment = getOpportunityFitJudgment(match);
    if (!judgment || !opportunityFitFilterAvailable) {
      return '';
    }

    if (judgment.fit === 'strong') {
      return 'LLM strong fit';
    }

    if (judgment.fit === 'weak') {
      return 'LLM excluded';
    }

    return 'LLM possible fit';
  }

  function getOpportunityFitBadgeClass(match: BenefitMatch): string {
    const judgment = getOpportunityFitJudgment(match);
    if (!judgment || !opportunityFitFilterAvailable) {
      return 'hidden';
    }

    if (judgment.fit === 'strong') {
      return 'rounded-full bg-emerald-100 px-2.5 py-1.5 text-xs leading-none font-black text-emerald-800 uppercase';
    }

    if (judgment.fit === 'weak') {
      return 'rounded-full bg-red-50 px-2.5 py-1.5 text-xs leading-none font-black text-red-700 uppercase';
    }

    return 'rounded-full bg-[#e8eef7] px-2.5 py-1.5 text-xs leading-none font-black text-[#38485d] uppercase';
  }

  function getAnalysisFitBadgeLabel(fit: OpportunityAnalysis['fit']): string {
    if (fit === 'strong') {
      return 'LLM strong fit';
    }

    if (fit === 'weak') {
      return 'LLM excluded';
    }

    return 'LLM possible fit';
  }

  function getAnalysisFitBadgeClass(fit: OpportunityAnalysis['fit']): string {
    if (fit === 'strong') {
      return 'rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-black text-emerald-800 uppercase';
    }

    if (fit === 'weak') {
      return 'rounded-full bg-red-50 px-2.5 py-1 text-[11px] font-black text-red-700 uppercase';
    }

    return 'rounded-full bg-[#e8eef7] px-2.5 py-1 text-[11px] font-black text-[#38485d] uppercase';
  }

  function getOpportunityAnalysisKey(
    match: BenefitMatch,
    fitJudgment: OpportunityFitJudgment | null = getActiveOpportunityFitJudgment(match)
  ): string {
    return getOpportunityAnalysisCacheKey(persona, match, getOpportunityDescription(match), fitJudgment);
  }

  function getOpportunityAnalysisLoadingKey(match: BenefitMatch): string {
    return getOpportunityFitJudgmentKey(match);
  }

  function getOpportunityAnalysis(match: BenefitMatch): OpportunityAnalysis | null {
    return opportunityAnalyses[getOpportunityAnalysisKey(match)] ?? null;
  }

  function isOpportunityAnalysisLoading(match: BenefitMatch): boolean {
    return opportunityAnalysisLoading[getOpportunityAnalysisLoadingKey(match)] === true;
  }

  function getOpportunityAnalysisError(match: BenefitMatch): string {
    return opportunityAnalysisErrors[getOpportunityAnalysisLoadingKey(match)] ?? '';
  }

  function getOpportunityAnalysisButtonLabel(match: BenefitMatch): string {
    if (isOpportunityAnalysisLoading(match)) {
      return 'Analyzing...';
    }

    return getOpportunityAnalysis(match) ? 'View analysis' : 'Analyze fit';
  }

  function removeShortlistedOpportunity(ref: string) {
    savedOpportunityRefs = savedOpportunityRefs.filter((savedRef) => savedRef !== ref);
  }

  function clearShortlist() {
    savedOpportunityRefs = [];
  }

  function getTotalMatchedCapital(matches: BenefitMatch[]): number {
    return matches.reduce((total, match) => total + (match.potentialFunding ?? 0), 0);
  }

  async function hydrateSemanticOpportunityScores() {
    const historicalMatches = data.grants.map((grant) => scoreOpportunityGrantRecord(grant, persona));
    const ruleMatches = data.innovation.records
      .filter(isCurrentlyAvailableOpportunity)
      .map((record) => scoreOpportunityBenefitRecord(record, persona, historicalMatches));
    const scores = await fetchSemanticScoresForMatches(
      getBackendApiUrl(data.innovation.endpoint),
      persona,
      ruleMatches,
      'business-benefits'
    );

    semanticScores = {
      ...semanticScores,
      ...scores
    };
  }

  function applyOpportunitySemanticScore(match: BenefitMatch, semanticScore: SemanticScore | undefined): BenefitMatch {
    if (!semanticScore) {
      return match;
    }

    const matchScore = Math.max(0, Math.min(100, Math.round(semanticScore.combined_score)));
    const status =
      matchScore >= LIKELY_MATCH_THRESHOLD
        ? { label: 'Likely match', tone: 'likely' as const }
        : matchScore >= 55
          ? { label: 'Worth review', tone: 'review' as const }
          : { label: 'Low confidence', tone: 'low' as const };

    return {
      ...match,
      matchScore,
      statusLabel: status.label,
      statusTone: status.tone,
      reasons: unique([...semanticScore.reasons, ...match.reasons]).slice(0, 4)
    };
  }

  function getBackendApiUrl(endpoint: string | null): string {
    try {
      return endpoint ? new URL(endpoint, window.location.origin).origin : DEFAULT_BACKEND_API_URL;
    } catch {
      return DEFAULT_BACKEND_API_URL;
    }
  }

  function getOpportunityRef(record: GenericRecord): string | null {
    const field = findField(record, idFields);
    const ref = field ? valueToString(field.value).trim() : '';
    return ref && ref !== 'Unavailable' ? `${field?.key}:${ref}` : null;
  }

  function getBenefitMatchRef(match: BenefitMatch): string | null {
    const recordRef = getOpportunityRef(match.record);
    if (recordRef) {
      return recordRef;
    }

    return `title:${getOpportunityTitle(match)}|${getOpportunitySponsor(match)}`;
  }

  function getCompareRef(match: BenefitMatch): string {
    return getBenefitMatchRef(match) ?? `match:${getOpportunityTitle(match)}|${getOpportunitySponsor(match)}`;
  }

  function getOpportunityTitle(match: BenefitMatch): string {
    return getRecordFieldValue(match.record, titleFields) ?? 'Funding opportunity';
  }

  function getOpportunitySponsor(match: BenefitMatch): string {
    return getRecordFieldValue(match.record, subtitleFields) ?? 'Program source unavailable';
  }

  function getOpportunityDescription(match: BenefitMatch): string {
    const description =
      getRecordFieldValue(match.record, ['description', 'description_en', 'summary', 'details', 'objective', 'eligibility']) ??
      match.reasons[0] ??
      'Review the source record to confirm applicant type, eligible activities, and application timing.';

    return description.length > 240 ? `${description.slice(0, 237)}...` : description;
  }

  function getOpportunityTags(match: BenefitMatch): string[] {
    const sponsor = getOpportunitySponsor(match).toLowerCase();
    const jurisdiction = sponsor.includes('canada') || sponsor.includes('federal') ? 'Federal' : 'Program';
    const activity = selectedActivities[0];
    const activityLabel = activityOptions.find((option) => option.value === activity)?.label;
    const industryLabel = industryOptions.find((option) => option.value === persona.industry)?.label;

    return unique([
      jurisdiction,
      industryLabel,
      activityLabel,
      match.historicalEvidenceCount > 0 ? 'Historical signal' : null
    ].filter((value): value is string => Boolean(value)));
  }

  function getFundingLabel(match: BenefitMatch): string {
    if (match.potentialFunding === null) {
      return 'Funding amount unavailable';
    }

    return moneyFormatter.format(match.potentialFunding);
  }

  function getFundingSourceLabel(match: BenefitMatch): string {
    return match.amount !== null ? 'Published amount' : match.estimatedAmount !== null ? 'Historical median estimate' : 'Not available';
  }

  function getComparisonMetricClass(value: number | null, peerValue: number | null): string {
    if (value === null || peerValue === null || value === peerValue) {
      return 'rounded-lg border border-slate-200 bg-[#f2f4f6] p-3';
    }

    return value > peerValue
      ? 'rounded-lg border border-emerald-200 bg-emerald-50 p-3'
      : 'rounded-lg border border-slate-200 bg-white p-3';
  }

  function getComparisonSummary(left: BenefitMatch, right: BenefitMatch): string {
    const scoreDifference = left.matchScore - right.matchScore;
    const fundingDifference = (left.potentialFunding ?? 0) - (right.potentialFunding ?? 0);

    if (Math.abs(scoreDifference) >= 8) {
      const stronger = scoreDifference > 0 ? left : right;
      return `${getOpportunityTitle(stronger)} has the stronger profile fit based on the current match score.`;
    }

    if (Math.abs(fundingDifference) > 0) {
      const larger = fundingDifference > 0 ? left : right;
      return `${getOpportunityTitle(larger)} has the larger funding signal, while both opportunities remain close on fit.`;
    }

    return 'These opportunities are close. Use risks, deadline, and application effort to decide which one to pursue first.';
  }

  function getComparisonFitLabel(match: BenefitMatch): string {
    const judgment = getActiveOpportunityFitJudgment(match);
    if (judgment) {
      return judgment.fit === 'weak' ? 'LLM excluded' : judgment.fit === 'strong' ? 'LLM strong fit' : 'LLM possible fit';
    }

    return match.statusLabel;
  }

  function getDeadlineLabel(match: BenefitMatch): string {
    const dateValue = getRecordFieldValue(match.record, dateFields);
    return dateValue ? formatDate(dateValue) : 'Rolling';
  }

  function getFitLabel(score: number): string {
    if (score >= 90) {
      return 'Exceptional fit';
    }

    if (score >= LIKELY_MATCH_THRESHOLD) {
      return 'Strong fit';
    }

    if (score >= 55) {
      return 'Worth review';
    }

    return 'Low confidence';
  }

  function getMatchTone(score: number): 'strong' | 'good' | 'review' | 'low' {
    if (score >= 90) {
      return 'strong';
    }

    if (score >= LIKELY_MATCH_THRESHOLD) {
      return 'good';
    }

    if (score >= 55) {
      return 'review';
    }

    return 'low';
  }

  function getScoreOffset(score: number): number {
    return Math.max(0, Math.min(100, 100 - score));
  }

  function getCompletenessWidthClass(value: number): string {
    if (value >= 100) return 'w-full';
    if (value >= 92) return 'w-11/12';
    if (value >= 83) return 'w-10/12';
    if (value >= 75) return 'w-9/12';
    if (value >= 67) return 'w-8/12';
    if (value >= 58) return 'w-7/12';
    if (value >= 50) return 'w-6/12';
    if (value >= 42) return 'w-5/12';
    if (value >= 33) return 'w-4/12';
    if (value >= 25) return 'w-3/12';
    if (value >= 17) return 'w-2/12';
    if (value > 0) return 'w-1/12';
    return 'w-0';
  }

  function getMatchStrokeClass(score: number): string {
    const tone = getMatchTone(score);

    if (tone === 'review') {
      return 'text-amber-600';
    }

    if (tone === 'low') {
      return 'text-slate-500';
    }

    return 'text-emerald-700';
  }

  function getInsightSignals(match: BenefitMatch): string[] {
    return (match.reasons.length > 0 ? match.reasons : match.nextActions).slice(0, 3);
  }

  function loadMoreOpportunities() {
    visibleOpportunityTarget = Math.min(sortedBenefitMatches.length, visibleOpportunityTarget + OPPORTUNITY_PAGE_SIZE);
  }

  function getSortHref(sort: SortMode): string {
    const params = new URLSearchParams(page.url.searchParams);
    params.set('sort', sort);
    return `${page.url.pathname}?${params.toString()}`;
  }
</script>

<svelte:head>
  <title>Opportunity Matches | FundRadar</title>
  <meta name="description" content="Review active funding benefits ranked with historical funding signals in FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<svelte:window onkeydown={handleAnalysisModalKeydown} />

{#snippet opportunityAnalysisPanel(analysis: OpportunityAnalysis, fitJudgment: OpportunityFitJudgment | null)}
  <section class="rounded-lg border border-emerald-100 bg-emerald-50/80 p-4 text-sm text-[#25302a]" aria-label="Opportunity fit analysis">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="m-0 text-xs font-black tracking-normal text-emerald-700 uppercase">Fit analysis</p>
      <div class="flex flex-wrap items-center gap-2">
        <span class={getAnalysisFitBadgeClass(analysis.fit)}>
          {getAnalysisFitBadgeLabel(analysis.fit)}
        </span>
        <span class="rounded-full bg-white px-2.5 py-1 text-[11px] font-black text-[#45464d] uppercase">{analysis.confidence} confidence</span>
      </div>
    </div>
    {#if fitJudgment}
      <p class="m-0 mt-2 rounded-md border border-white bg-white/70 px-3 py-2 leading-5 text-[#45464d]">
        Filter verdict: {fitJudgment.should_show ? 'visible in ranked matches' : 'hidden unless LLM-excluded matches are shown'}.
        {fitJudgment.reason}
      </p>
    {/if}
    <p class="m-0 mt-2 leading-6 text-[#25302a]">{analysis.fit_summary}</p>

    <div class="mt-4 grid grid-cols-2 gap-3 max-[720px]:grid-cols-1">
      {@render analysisList('Eligibility signals', analysis.eligibility_flags)}
      {@render analysisList('Missing info', analysis.missing_company_info)}
      {@render analysisList('Next steps', analysis.application_steps)}
      {@render analysisList('Risks', analysis.risk_notes)}
      {@render analysisList('Questions', analysis.questions_to_answer)}
    </div>
  </section>
{/snippet}

{#snippet analysisList(title: string, items: string[])}
  {#if items.length > 0}
    <div class="rounded-lg border border-emerald-100 bg-white/75 p-3">
      <h4 class="m-0 text-[11px] font-black text-[#45464d] uppercase">{title}</h4>
      <ul class="m-0 mt-2 grid list-none gap-1.5 p-0 leading-5 text-[#45464d]">
        {#each items as item (item)}
          <li class="relative pl-4 before:absolute before:left-0 before:text-emerald-700 before:content-['-']">{item}</li>
        {/each}
      </ul>
    </div>
  {/if}
{/snippet}

{#snippet comparisonOpportunityPanel(match: BenefitMatch, peer: BenefitMatch)}
  <section class="grid gap-4 rounded-lg border border-slate-200 bg-white p-4">
    <header class="grid gap-2">
      <div class="flex flex-wrap gap-1.5">
        {#each getOpportunityTags(match).slice(0, 3) as tag (tag)}
          <span class="rounded-full bg-[#eceef0] px-2.5 py-1.5 text-xs leading-none font-black text-[#45464d] uppercase first:bg-[#131b2e] first:text-[#dae2fd]">{tag}</span>
        {/each}
        {#if getActiveOpportunityFitJudgment(match)}
          <span class={getAnalysisFitBadgeClass(getActiveOpportunityFitJudgment(match)?.fit ?? 'possible')}>
            {getComparisonFitLabel(match)}
          </span>
        {/if}
      </div>
      <h3 class="m-0 text-xl leading-tight text-[#191c1e]">{getOpportunityTitle(match)}</h3>
      <p class="m-0 text-sm font-black text-[#006c49] uppercase">{getOpportunitySponsor(match)}</p>
    </header>

    <div class="grid grid-cols-2 gap-3 max-[640px]:grid-cols-1">
      <div class={getComparisonMetricClass(match.matchScore, peer.matchScore)}>
        <span class="text-[11px] font-black text-[#45464d] uppercase">Match</span>
        <strong class="mt-1 block text-2xl text-[#006c49]">{match.matchScore}%</strong>
        <small class="text-xs text-[#45464d]">{getComparisonFitLabel(match)}</small>
      </div>
      <div class={getComparisonMetricClass(match.potentialFunding, peer.potentialFunding)}>
        <span class="text-[11px] font-black text-[#45464d] uppercase">Funding</span>
        <strong class="mt-1 block text-lg text-[#191c1e]">{getFundingLabel(match)}</strong>
        <small class="text-xs text-[#45464d]">{getFundingSourceLabel(match)}</small>
      </div>
      <div class="rounded-lg border border-slate-200 bg-[#f2f4f6] p-3">
        <span class="text-[11px] font-black text-[#45464d] uppercase">Deadline</span>
        <strong class="mt-1 block text-lg text-[#191c1e]">{getDeadlineLabel(match)}</strong>
      </div>
      <div class={getComparisonMetricClass(match.historicalEvidenceCount, peer.historicalEvidenceCount)}>
        <span class="text-[11px] font-black text-[#45464d] uppercase">Historical signals</span>
        <strong class="mt-1 block text-lg text-[#191c1e]">{match.historicalEvidenceCount}</strong>
      </div>
    </div>

    <p class="m-0 text-sm leading-6 text-[#45464d]">{getOpportunityDescription(match)}</p>

    <div class="grid gap-3">
      {@render analysisList('Why it matches', match.reasons)}
      {@render analysisList('Risks', match.risks)}
      {@render analysisList('Next actions', match.nextActions)}
    </div>
  </section>
{/snippet}

<div class={pageShellClass}>
  <WorkspaceSidebar active="matches" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search profile, keywords, or opportunities..." />

    <main class="flex-1 overflow-y-auto">
      <div class={profileCanvasClass}>
      <section class={profileIntroClass}>
        <div>
          <h2 id="matches-page-heading" class="m-0 text-4xl leading-tight text-[#191c1e] max-md:text-3xl">Opportunity Matches</h2>
          <p class="mt-2 max-w-[66ch] leading-7 text-[#45464d]">
            Review ranked opportunities and manage saved applications for {applicantName}.
          </p>
        </div>
      </section>

      <section class="grid grid-cols-12 gap-6 max-lg:grid-cols-1" aria-labelledby="matches-heading">
        <section class="col-span-full grid gap-5" id="recommendations-panel" aria-labelledby="matches-heading">
        <div class="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-6 max-[760px]:grid-cols-1">
          <div>
            <p class={eyebrowClass}>FundRadar discovery</p>
            <h2 id="matches-heading" class="m-0 text-3xl leading-tight text-[#191c1e]">Opportunity Matches</h2>
            <p class="mt-2 max-w-[72ch] leading-7 text-[#45464d]">
              Based on {applicantName}'s profile, FundRadar ranks active benefits by fit, funding size,
              location, profile keywords, and historical award signals.
            </p>
          </div>

          <div
            class="inline-flex flex-wrap items-center gap-1 rounded-full border border-slate-200 bg-white p-1 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
            aria-label="Sort opportunities"
          >
            <span class="px-2 text-xs font-black tracking-normal text-[#45464d] uppercase">Sort by</span>
            <a class={activeSort === 'score' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('score')}>
              Relevance
            </a>
            <a class={activeSort === 'amount' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('amount')}>
              Amount
            </a>
            <a class={activeSort === 'newest' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('newest')}>
              Deadline
            </a>
          </div>
        </div>

        <section>
          <div class="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4" aria-label="Opportunity match controls">
            <label class="flex min-w-0 items-center gap-2 text-sm font-bold text-[#25302a]">
              <input class="h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-700" bind:checked={likelyOnly} type="checkbox" />
              <span>Likely matches only</span>
            </label>

            <dl class="m-0 flex flex-wrap gap-2.5">
              <div class="grid min-w-20 rounded-lg bg-[#f2f4f6] px-3 py-2">
                <dt class="text-[11px] font-black text-[#45464d] uppercase">Likely</dt>
                <dd class="m-0 text-lg font-black text-[#006c49]">{likelyMatchCount}</dd>
              </div>
              <div class="grid min-w-20 rounded-lg bg-[#f2f4f6] px-3 py-2">
                <dt class="text-[11px] font-black text-[#45464d] uppercase">Saved</dt>
                <dd class="m-0 text-lg font-black text-[#006c49]">{savedOpportunityRefs.length}</dd>
              </div>
            </dl>
          </div>

          <div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm text-[#45464d]" aria-label="LLM fit filter status">
            <div class="min-w-0">
              <p class="m-0 text-xs font-black tracking-normal text-emerald-700 uppercase">LLM fit filter</p>
              {#if opportunityFitJudging}
                <p class="m-0 mt-1 leading-6">Judging the visible opportunity batch against {applicantName}'s profile.</p>
              {:else if opportunityFitFilterMessage}
                <p class="m-0 mt-1 leading-6">{opportunityFitFilterMessage}</p>
              {:else if opportunityFitFilterAvailable}
                <p class="m-0 mt-1 leading-6">
                  Gemini reviewed the visible batch and hid {llmExcludedVisibleMatches.length}
                  {llmExcludedVisibleMatches.length === 1 ? ' weak fit' : ' weak fits'}.
                </p>
              {:else}
                <p class="m-0 mt-1 leading-6">Waiting for visible matches before running the fit filter.</p>
              {/if}
            </div>

            {#if opportunityFitFilterMessage}
              <button class={compactButtonClass} type="button" onclick={retryOpportunityFitFilter}>
                Retry filter
              </button>
            {:else if llmExcludedVisibleMatches.length > 0}
              <label class="flex shrink-0 items-center gap-2 text-sm font-bold text-[#25302a]">
                <input class="h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-700" bind:checked={showLlmExcluded} type="checkbox" />
                <span>Show LLM-excluded</span>
              </label>
            {/if}
          </div>

          {#if comparisonRefs.length > 0}
            <section class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950" aria-label="Opportunity comparison selection">
              <div class="min-w-0">
                <p class="m-0 text-xs font-black tracking-normal text-emerald-700 uppercase">Compare opportunities</p>
                <p class="m-0 mt-1 leading-6">
                  {comparisonRefs.length}/2 selected
                  {#if comparisonMatches.length > 0}
                    : {comparisonMatches.map(getOpportunityTitle).join(' vs ')}
                  {/if}
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button class={compactButtonClass} disabled={!comparisonReady} type="button" onclick={openComparisonModal}>
                  Open comparison
                </button>
                <button class={compactButtonClass} type="button" onclick={clearComparison}>
                  Clear
                </button>
              </div>
            </section>
          {/if}

          {#if newLikelyOpportunityCount > 0}
            <section class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950" role="status">
              <h3 class="m-0 font-bold">New likely opportunities found</h3>
              <p class="m-0 mt-2 leading-6">
                The Business Benefits Finder feed changed, so FundRadar refreshed active opportunities and found
                {newLikelyOpportunityCount} newly likely {newLikelyOpportunityCount === 1 ? 'match' : 'matches'} for {applicantName}.
              </p>
            </section>
          {/if}

          {#if !opportunitiesHydrated}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">Loading opportunities</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">Preparing active benefits and historical funding signals.</p>
            </section>
          {:else if data.innovation.error}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">Opportunities unavailable</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">{data.innovation.error}</p>
            </section>
          {:else if activeBenefitRecords.length === 0}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">No active benefits returned</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">No active Business Benefits Finder records are available in this selection.</p>
            </section>
          {:else if visibleCandidateBenefitMatches.length > 0 && visibleBenefitMatches.length === 0}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">Visible matches were filtered out</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">
                Gemini marked the current visible batch as weak fits for {applicantName}. Show excluded opportunities or load more results to continue reviewing.
              </p>
              <div class="mt-4 flex flex-wrap gap-2">
                <button class={secondaryButtonClass} type="button" onclick={() => (showLlmExcluded = true)}>
                  Show LLM-excluded
                </button>
                {#if canLoadMoreOpportunities}
                  <button class={secondaryButtonClass} type="button" onclick={loadMoreOpportunities}>
                    Load 10 more
                  </button>
                {/if}
              </div>
            </section>
          {:else if visibleBenefitMatches.length === 0}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">No likely matches yet</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">Broaden the company keywords or turn off the likely-only filter to review all active benefits.</p>
            </section>
          {:else}
            <section class="grid grid-cols-12 gap-6" aria-label="Ranked opportunity matches">
              {#if topOpportunity}
                {@const topOpportunityRef = getOpportunityRef(topOpportunity.record)}
                {@const topOpportunitySaved = topOpportunityRef ? savedOpportunityRefSet.has(topOpportunityRef) : false}
                {@const topOpportunityCompared = isOpportunitySelectedForComparison(topOpportunity)}
                {@const topOpportunityAnalysisLoading = isOpportunityAnalysisLoading(topOpportunity)}
                <article class={`col-span-8 grid min-h-[360px] grid-cols-[minmax(0,1fr)_260px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)] max-[1080px]:col-span-full max-[1080px]:grid-cols-[minmax(0,1fr)_230px] max-[760px]:grid-cols-1 ${isLlmExcludedOpportunity(topOpportunity) ? 'opacity-75' : ''}`}>
                  <div class="grid gap-4 p-7">
                    <div class="flex flex-wrap gap-1.5">
                      {#each getOpportunityTags(topOpportunity) as tag (tag)}
                        <span class="rounded-full bg-[#eceef0] px-2.5 py-1.5 text-xs leading-none font-black text-[#45464d] uppercase first:bg-[#131b2e] first:text-[#dae2fd]">{tag}</span>
                      {/each}
                      {#if getOpportunityFitBadgeLabel(topOpportunity)}
                        <span class={getOpportunityFitBadgeClass(topOpportunity)}>{getOpportunityFitBadgeLabel(topOpportunity)}</span>
                      {/if}
                    </div>

                    <h3 class="m-0 text-3xl leading-tight text-[#191c1e]">{getOpportunityTitle(topOpportunity)}</h3>
                    <p class="m-0 text-sm font-black text-[#006c49] uppercase">{getOpportunitySponsor(topOpportunity)}</p>
                    <p class="m-0 leading-7 text-[#45464d]">{getOpportunityDescription(topOpportunity)}</p>

                    <div class="mt-auto flex items-end justify-between gap-4 border-t border-slate-200 pt-4 max-[760px]:grid max-[760px]:items-stretch">
                      <div>
                        <p class="m-0 text-xs font-black text-[#45464d] uppercase">Potential funding</p>
                        <strong class="mt-1 block text-2xl text-[#006c49]">{getFundingLabel(topOpportunity)}</strong>
                        <span class="mt-1 block text-xs font-bold text-[#45464d]">{getFundingSourceLabel(topOpportunity)}</span>
                      </div>
                      <div class="flex flex-wrap justify-end gap-2 max-[760px]:justify-stretch">
                        <button
                          aria-busy={topOpportunityAnalysisLoading}
                          class={`${secondaryButtonClass} ${topOpportunityAnalysisLoading ? 'cursor-wait opacity-80' : ''}`}
                          type="button"
                          onclick={() => openOpportunityAnalysisModal(topOpportunity)}
                        >
                          {getOpportunityAnalysisButtonLabel(topOpportunity)}
                        </button>
                        <button
                          aria-pressed={topOpportunityCompared}
                          class={`${secondaryButtonClass} ${topOpportunityCompared ? 'border-emerald-700 bg-emerald-50 text-emerald-800' : ''}`}
                          type="button"
                          onclick={() => toggleOpportunityComparison(topOpportunity)}
                        >
                          {getComparisonButtonLabel(topOpportunity)}
                        </button>
                        <button
                          aria-pressed={topOpportunitySaved}
                          class={`rounded-lg border px-4 py-3 leading-none font-black text-white disabled:cursor-not-allowed disabled:border-[#c6c6cd] disabled:bg-[#eceef0] disabled:text-[#76777d] ${
                            topOpportunitySaved ? 'border-[#131b2e] bg-[#131b2e]' : 'border-emerald-700 bg-emerald-700 hover:bg-emerald-800'
                          }`}
                          disabled={!topOpportunityRef}
                          type="button"
                          onclick={() => toggleOpportunitySaved(topOpportunity)}
                        >
                          {topOpportunitySaved ? 'Saved' : 'Save opportunity'}
                        </button>
                      </div>
                    </div>
                  </div>

                  <aside class="grid place-items-center content-center gap-3.5 border-l border-slate-200 bg-[#f2f4f6] p-7 max-[760px]:border-t max-[760px]:border-l-0">
                    <div class={`relative grid h-[140px] w-[140px] place-items-center ${getMatchStrokeClass(topOpportunity.matchScore)}`} aria-label={`${topOpportunity.matchScore} percent match`}>
                      <svg class="absolute inset-0 h-full w-full -rotate-90" aria-hidden="true" viewBox="0 0 100 100">
                        <circle class="fill-none stroke-slate-200 [stroke-width:8]" cx="50" cy="50" r="42"></circle>
                        <circle
                          class="fill-none stroke-current [stroke-dasharray:100] [stroke-linecap:round] [stroke-width:8] transition-[stroke-dashoffset] duration-300"
                          cx="50"
                          cy="50"
                          r="42"
                          pathLength="100"
                          stroke-dashoffset={getScoreOffset(topOpportunity.matchScore)}
                        ></circle>
                      </svg>
                      <strong class="relative text-4xl leading-none text-[#191c1e]">{topOpportunity.matchScore}<span class="text-base">%</span></strong>
                    </div>

                    <p class="m-0 text-center text-sm font-black text-[#191c1e] uppercase">{getFitLabel(topOpportunity.matchScore)}</p>
                    <ul class="m-0 grid list-none gap-2 p-0 text-sm leading-6 text-[#45464d]">
                      {#each getInsightSignals(topOpportunity) as signal (signal)}
                        <li class="relative pl-4 before:absolute before:left-0 before:text-emerald-700 before:content-['-']">{signal}</li>
                      {/each}
                    </ul>
                  </aside>
                </article>
              {/if}

              <aside class={`relative col-span-4 grid content-start gap-4 overflow-hidden rounded-lg border border-slate-200 bg-[#0b1c30] p-7 text-white ${cardShadowClass} max-[1080px]:col-span-full`}>
                <h3 class="relative m-0 text-2xl leading-snug text-white">Profile Strength</h3>
                <p class="relative m-0 leading-6 text-[#dae2fd]/80">Your profile is {personaCompleteness}% complete, which improves match confidence for active benefits.</p>

                <div class="relative grid gap-2 rounded-lg border border-white/10 bg-[#131b2e]/70 p-3.5">
                  <span class="text-xs font-black text-[#dae2fd]/70 uppercase">Active benefits analyzed</span>
                  <strong class="text-3xl">{activeBenefitRecords.length}</strong>
                  <div class="h-2 overflow-hidden rounded-full bg-white/15"><span class={`block h-full rounded-full bg-emerald-400 ${getCompletenessWidthClass(personaCompleteness)}`}></span></div>
                </div>

                <div class="relative grid gap-2 rounded-lg border border-white/10 bg-[#131b2e]/70 p-3.5">
                  <span class="text-xs font-black text-[#dae2fd]/70 uppercase">Historical funding signals</span>
                  <strong class="text-3xl">{historicalEvidenceCount}</strong>
                </div>

                <div class="relative grid gap-2 rounded-lg border border-white/10 bg-[#131b2e]/70 p-3.5">
                  <span class="text-xs font-black text-[#dae2fd]/70 uppercase">Total matched capital</span>
                  <strong class="text-3xl">{formatMoneyValue(totalMatchedCapital)}</strong>
                </div>
              </aside>

              {#each remainingOpportunities as match, index (getOpportunityRef(match.record) ?? `opportunity-${index}`)}
                {@const opportunityRef = getOpportunityRef(match.record)}
                {@const opportunitySaved = opportunityRef ? savedOpportunityRefSet.has(opportunityRef) : false}
                {@const opportunityCompared = isOpportunitySelectedForComparison(match)}
                {@const opportunityAnalysisLoading = isOpportunityAnalysisLoading(match)}
                <article class={`col-span-4 grid min-h-80 gap-4 rounded-lg border border-slate-200 bg-white p-6 ${cardShadowClass} transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] max-[1080px]:col-span-full ${isLlmExcludedOpportunity(match) ? 'opacity-75' : ''}`}>
                  <div class="flex items-start justify-between gap-4">
                    <div class="flex flex-wrap gap-1.5">
                      {#each getOpportunityTags(match).slice(0, 2) as tag (tag)}
                        <span class="rounded-full bg-[#eceef0] px-2.5 py-1.5 text-xs leading-none font-black text-[#45464d] uppercase first:bg-[#131b2e] first:text-[#dae2fd]">{tag}</span>
                      {/each}
                      {#if getOpportunityFitBadgeLabel(match)}
                        <span class={getOpportunityFitBadgeClass(match)}>{getOpportunityFitBadgeLabel(match)}</span>
                      {/if}
                    </div>

                    <div class={`relative grid h-14 w-14 shrink-0 place-items-center ${getMatchStrokeClass(match.matchScore)}`} aria-label={`${match.matchScore} percent match`}>
                      <svg class="absolute inset-0 h-full w-full -rotate-90" aria-hidden="true" viewBox="0 0 40 40">
                        <circle class="fill-none stroke-slate-200 [stroke-width:4]" cx="20" cy="20" r="16"></circle>
                        <circle
                          class="fill-none stroke-current [stroke-dasharray:100] [stroke-linecap:round] [stroke-width:4] transition-[stroke-dashoffset] duration-300"
                          cx="20"
                          cy="20"
                          r="16"
                          pathLength="100"
                          stroke-dashoffset={getScoreOffset(match.matchScore)}
                        ></circle>
                      </svg>
                      <strong class="relative text-xs font-black text-[#191c1e]">{match.matchScore}%</strong>
                    </div>
                  </div>

                  <h3 class="m-0 text-xl leading-snug text-[#191c1e]">{getOpportunityTitle(match)}</h3>
                  <p class="m-0 text-sm leading-6 text-[#45464d]">{getOpportunityDescription(match)}</p>

                  <div class="mt-auto grid grid-cols-2 gap-3 border-t border-slate-200 pt-4">
                    <div class="grid gap-1">
                      <span class="text-[11px] font-black text-[#45464d] uppercase">Amount</span>
                      <strong class="text-sm text-[#191c1e]">{getFundingLabel(match)}</strong>
                      <small class="text-xs text-[#45464d]">{getFundingSourceLabel(match)}</small>
                    </div>
                    <div class="grid gap-1">
                      <span class="text-[11px] font-black text-[#45464d] uppercase">Deadline</span>
                      <strong class="text-sm text-[#191c1e]">{getDeadlineLabel(match)}</strong>
                    </div>
                  </div>

                  <div class="grid grid-cols-3 gap-2 max-[760px]:grid-cols-1">
                    <button
                      aria-busy={opportunityAnalysisLoading}
                      class={`${secondaryButtonClass} ${opportunityAnalysisLoading ? 'cursor-wait opacity-80' : ''}`}
                      type="button"
                      onclick={() => openOpportunityAnalysisModal(match)}
                    >
                      {getOpportunityAnalysisButtonLabel(match)}
                    </button>
                    <button
                      aria-pressed={opportunityCompared}
                      class={`${secondaryButtonClass} ${opportunityCompared ? 'border-emerald-700 bg-emerald-50 text-emerald-800' : ''}`}
                      type="button"
                      onclick={() => toggleOpportunityComparison(match)}
                    >
                      {getComparisonButtonLabel(match)}
                    </button>
                    <button
                      aria-pressed={opportunitySaved}
                      class={`rounded-lg border px-4 py-3 leading-none font-black text-white disabled:cursor-not-allowed disabled:border-[#c6c6cd] disabled:bg-[#eceef0] disabled:text-[#76777d] ${
                        opportunitySaved ? 'border-[#131b2e] bg-[#131b2e]' : 'border-emerald-700 bg-emerald-700 hover:bg-emerald-800'
                      }`}
                      disabled={!opportunityRef}
                      type="button"
                      onclick={() => toggleOpportunitySaved(match)}
                    >
                      {opportunitySaved ? 'Saved' : 'Save'}
                    </button>
                  </div>
                </article>
              {/each}
            </section>

            {#if canLoadMoreOpportunities}
              <div class="mt-6 flex justify-center">
                <button class={secondaryButtonClass} type="button" onclick={loadMoreOpportunities}>
                  Load 10 more
                </button>
              </div>
            {/if}
          {/if}

          <section class="mt-8 rounded-lg border border-slate-200 bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="shortlist-heading">
            <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
              <div>
                <p class={eyebrowClass}>Shortlist</p>
                <h2 id="shortlist-heading" class="m-0 text-2xl leading-tight text-[#191c1e]">Compare saved opportunities</h2>
              </div>

              <dl class="m-0">
                <div class="grid min-w-20 rounded-lg bg-[#f2f4f6] px-3 py-2">
                  <dt class="text-[11px] font-black text-[#45464d] uppercase">Saved</dt>
                  <dd class="m-0 text-lg font-black text-[#006c49]">{savedOpportunityRefs.length}</dd>
                </div>
              </dl>
            </div>

            {#if savedOpportunityRefs.length === 0}
              <p class="m-0 py-8 text-sm leading-6 text-[#45464d]">No opportunities saved yet.</p>
            {:else}
              <div class="grid gap-0 overflow-hidden rounded-lg border border-slate-200" aria-label="Saved opportunity comparison">
                <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 bg-[#f2f4f6] px-4 py-3 text-xs font-black text-[#45464d] uppercase max-[840px]:hidden">
                  <span>Opportunity</span>
                  <span>Program</span>
                  <span>Amount</span>
                  <span>Fit</span>
                  <span>Action</span>
                </div>

                {#each shortlistedOpportunities as item (item.ref)}
                  {#if item.match}
                    <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 border-t border-slate-200 px-4 py-4 first:border-t-0 max-[840px]:grid-cols-1">
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Opportunity</span>
                        <strong class="text-sm text-[#191c1e]">{getOpportunityTitle(item.match)}</strong>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Program</span>
                        <span class="text-sm text-[#191c1e]">{getOpportunitySponsor(item.match)}</span>
                        <small class="text-xs text-[#45464d]">{item.match.historicalEvidenceCount} historical signals</small>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Amount</span>
                        <strong class="text-sm text-[#191c1e]">{getFundingLabel(item.match)}</strong>
                        <small class="text-xs text-[#45464d]">{getFundingSourceLabel(item.match)}</small>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Fit</span>
                        <strong class="text-sm text-[#191c1e]">{item.match.matchScore}%</strong>
                        <small class="text-xs text-[#45464d]">{item.match.statusLabel}</small>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <button
                          class={compactButtonClass}
                          type="button"
                          onclick={() => toggleOpportunityComparison(item.match)}
                        >
                          {getComparisonButtonLabel(item.match)}
                        </button>
                        <button
                          class={compactButtonClass}
                          type="button"
                          onclick={() => removeShortlistedOpportunity(item.ref)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  {:else}
                    <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 border-t border-slate-200 bg-slate-50 px-4 py-4 first:border-t-0 max-[840px]:grid-cols-1">
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Opportunity</span>
                        <strong class="text-sm text-[#191c1e]">Opportunity not in current results</strong>
                      </div>
                      <div><span class="text-sm text-[#45464d]">Program unavailable</span></div>
                      <div><span class="text-sm text-[#45464d]">Amount unavailable</span></div>
                      <div><span class="text-sm text-[#45464d]">Fit unavailable</span></div>
                      <div>
                        <button
                          class={compactButtonClass}
                          type="button"
                          onclick={() => removeShortlistedOpportunity(item.ref)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  {/if}
                {/each}
              </div>

              <div class="mt-4 flex justify-end">
                <button class={compactButtonClass} type="button" onclick={clearShortlist}>
                  Clear shortlist
                </button>
              </div>
            {/if}
          </section>
        </section>
        </section>
      </section>
    </div>
  </main>
</div>

{#if analysisModalMatch}
  {@const modalMatch = analysisModalMatch}
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b1c30]/60 p-4 backdrop-blur-sm"
    role="presentation"
    onclick={handleAnalysisBackdropClick}
  >
    <div
      aria-labelledby="fit-analysis-modal-title"
      aria-modal="true"
      class="grid max-h-[92vh] w-full max-w-3xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_24px_80px_rgba(0,0,0,0.24)]"
      role="dialog"
    >
      <header class="flex items-start justify-between gap-4 border-b border-slate-200 bg-[#f7f9fb] p-5">
        <div class="min-w-0">
          <p class={eyebrowClass}>Opportunity fit</p>
          <h2 id="fit-analysis-modal-title" class="m-0 text-2xl leading-tight text-[#191c1e]">{getOpportunityTitle(modalMatch)}</h2>
          <p class="m-0 mt-1 text-sm font-black text-[#006c49] uppercase">{getOpportunitySponsor(modalMatch)}</p>
        </div>

        <button
          aria-label="Close fit analysis"
          class="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-slate-200 bg-white leading-none text-[#191c1e] hover:bg-slate-100"
          type="button"
          onclick={closeOpportunityAnalysisModal}
        >
          <span class="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
        </button>
      </header>

      <div class="grid gap-4 overflow-y-auto p-5">
        <div class="grid grid-cols-3 gap-3 max-[640px]:grid-cols-1" aria-label="Selected opportunity summary">
          <div class="rounded-lg border border-slate-200 bg-[#f2f4f6] p-3">
            <span class="text-[11px] font-black text-[#45464d] uppercase">Match</span>
            <strong class="mt-1 block text-2xl text-[#006c49]">{modalMatch.matchScore}%</strong>
            <small class="text-xs text-[#45464d]">{modalMatch.statusLabel}</small>
          </div>
          <div class="rounded-lg border border-slate-200 bg-[#f2f4f6] p-3">
            <span class="text-[11px] font-black text-[#45464d] uppercase">Funding</span>
            <strong class="mt-1 block text-lg text-[#191c1e]">{getFundingLabel(modalMatch)}</strong>
            <small class="text-xs text-[#45464d]">{getFundingSourceLabel(modalMatch)}</small>
          </div>
          <div class="rounded-lg border border-slate-200 bg-[#f2f4f6] p-3">
            <span class="text-[11px] font-black text-[#45464d] uppercase">Deadline</span>
            <strong class="mt-1 block text-lg text-[#191c1e]">{getDeadlineLabel(modalMatch)}</strong>
          </div>
        </div>

        <p class="m-0 leading-7 text-[#45464d]">{getOpportunityDescription(modalMatch)}</p>

        {#if analysisModalLoading}
          <section class="rounded-lg border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950" role="status">
            Analyzing the selected opportunity against {applicantName}'s company profile.
          </section>
        {/if}

        {#if analysisModalAnalysis}
          {@render opportunityAnalysisPanel(analysisModalAnalysis, analysisModalFitJudgment)}
        {:else if analysisModalError}
          <section class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-800" role="alert">
            {analysisModalError}
          </section>
        {:else if !analysisModalLoading}
          <section class="rounded-lg border border-slate-200 bg-[#f7f9fb] p-4 text-sm leading-6 text-[#45464d]" role="status">
            Fit analysis is ready to run for this opportunity.
          </section>
        {/if}
      </div>

      <footer class="flex flex-wrap justify-end gap-2 border-t border-slate-200 bg-[#f7f9fb] p-5">
        <button class={secondaryButtonClass} type="button" onclick={closeOpportunityAnalysisModal}>
          Close
        </button>
        <button
          class="inline-flex items-center justify-center rounded-lg border border-emerald-700 bg-emerald-700 px-3.5 py-3 leading-none font-extrabold text-white no-underline hover:border-emerald-800 hover:bg-emerald-800 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-emerald-200 disabled:cursor-wait disabled:border-slate-300 disabled:bg-white disabled:text-[#45464d] disabled:opacity-100"
          disabled={analysisModalLoading}
          type="button"
          onclick={refreshOpportunityAnalysisModal}
        >
          {analysisModalAnalysis ? 'Refresh analysis' : analysisModalError ? 'Retry analysis' : 'Analyze fit'}
        </button>
      </footer>
    </div>
  </div>
{/if}

{#if comparisonModalOpen && comparisonReady}
  {@const leftComparisonMatch = comparisonMatches[0]}
  {@const rightComparisonMatch = comparisonMatches[1]}
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b1c30]/60 p-4 backdrop-blur-sm"
    role="presentation"
    onclick={handleComparisonBackdropClick}
  >
    <div
      aria-labelledby="opportunity-comparison-title"
      aria-modal="true"
      class="grid max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-xl border border-slate-200 bg-[#f7f9fb] shadow-[0_24px_80px_rgba(0,0,0,0.24)]"
      role="dialog"
    >
      <header class="flex items-start justify-between gap-4 border-b border-slate-200 bg-white p-5">
        <div class="min-w-0">
          <p class={eyebrowClass}>Opportunity comparison</p>
          <h2 id="opportunity-comparison-title" class="m-0 text-2xl leading-tight text-[#191c1e]">Compare two matches</h2>
          <p class="m-0 mt-1 text-sm leading-6 text-[#45464d]">{getComparisonSummary(leftComparisonMatch, rightComparisonMatch)}</p>
        </div>

        <button
          aria-label="Close opportunity comparison"
          class="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-slate-200 bg-white leading-none text-[#191c1e] hover:bg-slate-100"
          type="button"
          onclick={closeComparisonModal}
        >
          <span class="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
        </button>
      </header>

      <div class="grid gap-5 overflow-y-auto p-5">
        <div class="grid grid-cols-2 gap-5 max-[900px]:grid-cols-1">
          {@render comparisonOpportunityPanel(leftComparisonMatch, rightComparisonMatch)}
          {@render comparisonOpportunityPanel(rightComparisonMatch, leftComparisonMatch)}
        </div>
      </div>

      <footer class="flex flex-wrap justify-between gap-2 border-t border-slate-200 bg-white p-5">
        <button class={secondaryButtonClass} type="button" onclick={clearComparison}>
          Clear comparison
        </button>
        <button class={secondaryButtonClass} type="button" onclick={closeComparisonModal}>
          Close
        </button>
      </footer>
    </div>
  </div>
{/if}
</div>
