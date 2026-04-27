<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import { hydrateCachedGrantsResult, readCachedGrantsResult, type CachedGrantsResult } from '$lib/client/funding-cache';
  import { onMount } from 'svelte';

  type SortMode = 'score' | 'amount' | 'newest';
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
  const DEFAULT_BACKEND_API_URL = 'http://127.0.0.1:8000';
  const DEFAULT_COUNT = 10;
  const MAX_COUNT = 100;
  const pageShellClass =
    'flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]';
  const profileCanvasClass = 'mx-auto w-full max-w-[1280px] px-6 py-12 max-md:px-4 max-md:py-7';
  const profileIntroClass = 'mb-12 flex items-end justify-between gap-6 max-lg:grid max-lg:items-start max-md:mb-7';
  const sortLinkClass =
    'rounded-full px-3.5 py-2.5 text-sm leading-none font-extrabold text-[#191c1e] no-underline hover:bg-[#f2f4f6] focus-visible:bg-[#f2f4f6]';
  const sortLinkActiveClass = 'rounded-full bg-[#006c49] px-3.5 py-2.5 text-sm leading-none font-extrabold text-white no-underline';
  const filterFieldClass = 'grid gap-2 text-sm font-bold text-[#25302a]';
  const filterInputClass =
    'min-h-[42px] w-full rounded-lg border border-[#bec9c1] bg-white px-3 py-2 font-medium leading-[1.4] text-[#172026] focus:border-emerald-700 focus:outline-[3px] focus:outline-offset-2 focus:outline-emerald-200';
  const primaryButtonClass =
    'inline-flex items-center justify-center rounded-lg border border-emerald-800 bg-emerald-800 px-3.5 py-3 leading-none font-extrabold text-white no-underline hover:bg-emerald-900 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-emerald-200';
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
    businessNumber: string;
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
  type ShortlistedGrant = {
    ref: string;
    match: GrantMatch | null;
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
    { value: 'clean', label: 'CleanTech', terms: ['clean technology', 'energy', 'sustainability'] },
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
  const SHORTLIST_STORAGE_KEY = 'publicus.shortlistedGrantRefs';

  let persona = $state(createDefaultPersona());
  let selectedYear = $state<string | null>(null);
  let selectedCount = $state<string | null>(null);
  let selectedSort = $state<SortMode | null>(null);
  let likelyOnly = $state(false);
  let savedGrantRefs = $state<string[]>([]);
  let shortlistHydrated = $state(false);
  let profileHydrated = $state(false);
  let profileSaved = $state(false);
  let grantsHydrated = $state(false);

  const activeYear = $derived(selectedYear ?? data.filters.year?.toString() ?? '');
  const activeCount = $derived(selectedCount ?? data.filters.count.toString());
  const activeSortInput = $derived(selectedSort ?? data.filters.sort);
  const selectedActivities = $derived(
    activityOptions.filter((activity) => persona.activities[activity.value]).map((activity) => activity.value)
  );
  const personaKeywords = $derived(buildPersonaKeywords(persona, selectedActivities));
  const personaCompleteness = $derived(calculatePersonaCompleteness(persona, selectedActivities));
  const grantMatches = $derived(data.grants.map((grant) => scoreGrant(grant, persona, personaKeywords)));
  const savedGrantRefSet = $derived(new Set(savedGrantRefs));
  const shortlistedGrants = $derived(
    savedGrantRefs.map(
      (ref): ShortlistedGrant => ({
        ref,
        match: grantMatches.find((match) => getGrantRef(match.grant) === ref) ?? null
      })
    )
  );
  const likelyMatchCount = $derived(grantMatches.filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD).length);
  const visibleGrantMatches = $derived(
    sortGrantMatches(
      likelyOnly ? grantMatches.filter((match) => match.matchScore >= LIKELY_MATCH_THRESHOLD) : grantMatches,
      data.filters.sort
    )
  );
  const topOpportunity = $derived(visibleGrantMatches[0] ?? null);
  const remainingOpportunities = $derived(visibleGrantMatches.slice(1));
  const totalMatchedCapital = $derived(getTotalMatchedCapital(visibleGrantMatches));
  const applicantName = $derived(persona.doingBusinessAs || persona.legalEntityName || 'your company');

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
        requested: filters.count,
        count: 0,
        records: [],
        source: null,
        endpoint: null,
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
        ...(value.innovation ?? {})
      }
    };
  }

  function readClientFilters(): PersonaData['filters'] {
    const params = browser ? new URLSearchParams(window.location.search) : new URLSearchParams();

    return {
      source: 'grants',
      year: parseCalendarYear(params.get('year')),
      count: parseBoundedInteger(params.get('count'), DEFAULT_COUNT, 1, MAX_COUNT),
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

  onMount(() => {
    void hydrateProfile();
    savedGrantRefs = readSavedGrantRefs();
    shortlistHydrated = true;

    if (!hydratePersonaGrantsFromCache()) {
      void hydratePersonaGrants();
    }
  });

  async function hydrateProfile() {
    persona = (await readServerPersona()) ?? readStoredPersona() ?? createDefaultPersona();
    profileHydrated = true;
  }

  async function hydratePersonaGrants() {
    const endpoint = data.grantsQuery?.endpoint;

    if (!endpoint) {
      grantsHydrated = true;
      return;
    }

    const result = await hydrateCachedGrantsResult(endpoint, data.requested);
    applyPersonaGrantsResult(result);
    grantsHydrated = true;
  }

  function hydratePersonaGrantsFromCache(): boolean {
    const endpoint = data.grantsQuery?.endpoint;

    if (!endpoint) {
      grantsHydrated = true;
      return true;
    }

    const cached = readCachedGrantsResult(endpoint, data.requested);

    if (!cached) {
      return false;
    }

    applyPersonaGrantsResult(cached);
    grantsHydrated = true;
    return true;
  }

  function applyPersonaGrantsResult(result: CachedGrantsResult) {
    clientData = {
      ...data,
      grants: result.records as GrantRecord[],
      total: result.total,
      requested: result.requested,
      error: result.error
    };
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

    persistSavedGrantRefs(savedGrantRefs);
  });

  function createDefaultPersona(): CompanyPersona {
    return {
      legalEntityName: 'AccessBuild AI Inc.',
      doingBusinessAs: 'AccessBuild AI',
      businessNumber: '123456789 RT0001',
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
      businessNumber: '',
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

  function parseMoney(value: string | null | undefined): number | null {
    if (!value) {
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
      profile.businessNumber,
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
        businessNumber: readStringField(parsed, 'businessNumber', defaults.businessNumber),
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

  function readSavedGrantRefs(): string[] {
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

  function persistSavedGrantRefs(refs: string[]) {
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

  function toggleGrantSaved(grant: GrantRecord) {
    const ref = getGrantRef(grant);

    if (!ref) {
      return;
    }

    savedGrantRefs = savedGrantRefSet.has(ref)
      ? savedGrantRefs.filter((savedRef) => savedRef !== ref)
      : [...savedGrantRefs, ref];
  }

  function removeShortlistedGrant(ref: string) {
    savedGrantRefs = savedGrantRefs.filter((savedRef) => savedRef !== ref);
  }

  function clearShortlist() {
    savedGrantRefs = [];
  }

  function getSortLabel(mode: SortMode): string {
    if (mode === 'amount') {
      return 'largest amount';
    }

    if (mode === 'newest') {
      return 'newest first';
    }

    return 'best match';
  }

  function getGrantQuerySummary(): string {
    const grantsQuery = data.grantsQuery;
    const sortLabel = getSortLabel(data.filters.sort);

    if (grantsQuery?.mode === 'calendar-year' && grantsQuery.year !== null) {
      return `Calendar year ${grantsQuery.year}, sorted by ${sortLabel}.`;
    }

    return `Sorted by ${sortLabel}.`;
  }

  function getTotalMatchedCapital(matches: GrantMatch[]): number {
    return matches.reduce((total, match) => total + (match.amount ?? 0), 0);
  }

  function getOpportunityTitle(match: GrantMatch): string {
    return (
      match.grant.prog_name_en ??
      match.grant.agreement_title_en ??
      match.grant.recipient_legal_name ??
      'Funding opportunity'
    );
  }

  function getOpportunitySponsor(match: GrantMatch): string {
    return match.grant.owner_org_title ?? match.grant.recipient_legal_name ?? 'Sponsor unavailable';
  }

  function getOpportunityDescription(match: GrantMatch): string {
    return (
      match.grant.description_en ??
      match.grant.expected_results_en ??
      match.grant.prog_purpose_en ??
      match.reasons[0] ??
      'Review the source record to confirm applicant type, eligible activities, and application timing.'
    );
  }

  function getOpportunityTags(match: GrantMatch): string[] {
    const sponsor = getOpportunitySponsor(match).toLowerCase();
    const jurisdiction = sponsor.includes('canada') || sponsor.includes('federal') ? 'Federal' : 'Program';
    const activity = selectedActivities[0];
    const activityLabel = activityOptions.find((option) => option.value === activity)?.label;
    const industryLabel = industryOptions.find((option) => option.value === persona.industry)?.label;

    return unique([jurisdiction, industryLabel, activityLabel].filter((value): value is string => Boolean(value)));
  }

  function getFundingLabel(match: GrantMatch): string {
    return match.amount === null ? 'Value unavailable' : moneyFormatter.format(match.amount);
  }

  function getDeadlineLabel(match: GrantMatch): string {
    if (match.grant.agreement_end_date) {
      return formatDate(match.grant.agreement_end_date);
    }

    if (match.grant.agreement_start_date) {
      return `${formatDate(match.grant.agreement_start_date)} start`;
    }

    return 'Rolling';
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

  function getInsightSignals(match: GrantMatch): string[] {
    return (match.reasons.length > 0 ? match.reasons : match.nextActions).slice(0, 3);
  }

  function getSortHref(sort: SortMode): string {
    const params = new URLSearchParams({
      count: data.filters.count.toString(),
      sort
    });

    if (data.filters.year !== null) {
      params.set('year', data.filters.year.toString());
    }

    return `/dashboard/persona/matches?${params.toString()}`;
  }
</script>

<svelte:head>
  <title>Opportunity Matches | FundRadar</title>
  <meta name="description" content="Review ranked grant opportunities and saved applications with FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

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
              Based on {applicantName}'s profile, FundRadar ranked grants by fit, funding size,
              location, and profile keyword signals.
            </p>
            <p class="mt-4 break-words text-sm text-[#52615c]">{getGrantQuerySummary()}</p>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 rounded-full border border-slate-200 bg-white p-1.5" aria-label="Sort opportunities">
            <span class="px-2 text-xs font-bold text-[#45464d] uppercase">Sort by</span>
            <a class={data.filters.sort === 'score' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('score')}>
              Relevance
            </a>
            <a class={data.filters.sort === 'amount' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('amount')}>
              Amount
            </a>
            <a class={data.filters.sort === 'newest' ? sortLinkActiveClass : sortLinkClass} href={getSortHref('newest')}>
              Deadline
            </a>
          </div>
        </div>

        <form class="grid grid-cols-[minmax(120px,0.8fr)_minmax(110px,0.7fr)_auto] items-end gap-3 rounded-lg border border-slate-200 bg-white p-4 max-lg:grid-cols-2 max-md:grid-cols-1" method="GET" aria-label="Company grant filters">
          <label class={filterFieldClass}>
            <span>Year</span>
            <input
              class={filterInputClass}
              max="2200"
              min="1800"
              name="year"
              oninput={(event) => {
                selectedYear = event.currentTarget.value;
              }}
              placeholder="Any"
              type="number"
              value={activeYear}
            />
          </label>

          <label class={filterFieldClass}>
            <span>Count</span>
            <input
              class={filterInputClass}
              max="100"
              min="1"
              name="count"
              oninput={(event) => {
                selectedCount = event.currentTarget.value;
              }}
              type="number"
              value={activeCount}
            />
          </label>

          <div class="flex flex-wrap gap-2 max-md:grid">
            <button class={primaryButtonClass} type="submit">Apply</button>
            <a class={secondaryButtonClass} href="/dashboard/persona/matches">Reset filters</a>
          </div>
        </form>

        <section>
          <div class="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4" aria-label="Grant match controls">
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
                <dd class="m-0 text-lg font-black text-[#006c49]">{savedGrantRefs.length}</dd>
              </div>
            </dl>
          </div>

          {#if !grantsHydrated}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">Loading opportunities</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">Preparing the latest saved opportunity records.</p>
            </section>
          {:else if data.error}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">Opportunities unavailable</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">{data.error}</p>
            </section>
          {:else if data.grants.length === 0}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">No grants returned</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">No grants are available for this selection.</p>
            </section>
          {:else if visibleGrantMatches.length === 0}
            <section class={statePanelClass} role="status">
              <h2 class="m-0 text-xl leading-snug text-[#191c1e]">No likely matches yet</h2>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">Broaden the company keywords or turn off the likely-only filter to review all grants.</p>
            </section>
          {:else}
            <section class="grid grid-cols-12 gap-6" aria-label="Ranked opportunity matches">
              {#if topOpportunity}
                {@const topGrantRef = getGrantRef(topOpportunity.grant)}
                {@const topGrantSaved = topGrantRef ? savedGrantRefSet.has(topGrantRef) : false}
                <article class="col-span-8 grid min-h-[360px] grid-cols-[minmax(0,1fr)_260px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.03)] max-[1080px]:col-span-full max-[1080px]:grid-cols-[minmax(0,1fr)_230px] max-[760px]:grid-cols-1">
                  <div class="grid gap-4 p-7">
                    <div class="flex flex-wrap gap-1.5">
                      {#each getOpportunityTags(topOpportunity) as tag (tag)}
                        <span class="rounded-full bg-[#eceef0] px-2.5 py-1.5 text-xs leading-none font-black text-[#45464d] uppercase first:bg-[#131b2e] first:text-[#dae2fd]">{tag}</span>
                      {/each}
                    </div>

                    <h3 class="m-0 text-3xl leading-tight text-[#191c1e]">{getOpportunityTitle(topOpportunity)}</h3>
                    <p class="m-0 text-sm font-black text-[#006c49] uppercase">{getOpportunitySponsor(topOpportunity)}</p>
                    <p class="m-0 leading-7 text-[#45464d]">{getOpportunityDescription(topOpportunity)}</p>

                    <div class="mt-auto flex items-end justify-between gap-4 border-t border-slate-200 pt-4 max-[760px]:grid max-[760px]:items-stretch">
                      <div>
                        <p class="m-0 text-xs font-black text-[#45464d] uppercase">Potential funding</p>
                        <strong class="mt-1 block text-2xl text-[#006c49]">{getFundingLabel(topOpportunity)}</strong>
                      </div>
                      <button
                        aria-pressed={topGrantSaved}
                        class={`rounded-lg border px-4 py-3 leading-none font-black text-white disabled:cursor-not-allowed disabled:border-[#c6c6cd] disabled:bg-[#eceef0] disabled:text-[#76777d] ${
                          topGrantSaved ? 'border-[#131b2e] bg-[#131b2e]' : 'border-emerald-700 bg-emerald-700 hover:bg-emerald-800'
                        }`}
                        disabled={!topGrantRef}
                        type="button"
                        onclick={() => toggleGrantSaved(topOpportunity.grant)}
                      >
                        {topGrantSaved ? 'Saved' : 'Save opportunity'}
                      </button>
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
                <p class="relative m-0 leading-6 text-[#dae2fd]/80">Your profile is {personaCompleteness}% complete, which improves match confidence for available grants.</p>

                <div class="relative grid gap-2 rounded-lg border border-white/10 bg-[#131b2e]/70 p-3.5">
                  <span class="text-xs font-black text-[#dae2fd]/70 uppercase">Data points analyzed</span>
                  <strong class="text-3xl">{data.grants.length}</strong>
                  <div class="h-2 overflow-hidden rounded-full bg-white/15"><span class={`block h-full rounded-full bg-emerald-400 ${getCompletenessWidthClass(personaCompleteness)}`}></span></div>
                </div>

                <div class="relative grid gap-2 rounded-lg border border-white/10 bg-[#131b2e]/70 p-3.5">
                  <span class="text-xs font-black text-[#dae2fd]/70 uppercase">Total matched capital</span>
                  <strong class="text-3xl">{formatMoneyValue(totalMatchedCapital)}</strong>
                </div>
              </aside>

              {#each remainingOpportunities as match (match.grant._id)}
                {@const grantRef = getGrantRef(match.grant)}
                {@const grantSaved = grantRef ? savedGrantRefSet.has(grantRef) : false}
                <article class={`col-span-4 grid min-h-80 gap-4 rounded-lg border border-slate-200 bg-white p-6 ${cardShadowClass} transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] max-[1080px]:col-span-full`}>
                  <div class="flex items-start justify-between gap-4">
                    <div class="flex flex-wrap gap-1.5">
                      {#each getOpportunityTags(match).slice(0, 2) as tag (tag)}
                        <span class="rounded-full bg-[#eceef0] px-2.5 py-1.5 text-xs leading-none font-black text-[#45464d] uppercase first:bg-[#131b2e] first:text-[#dae2fd]">{tag}</span>
                      {/each}
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
                    </div>
                    <div class="grid gap-1">
                      <span class="text-[11px] font-black text-[#45464d] uppercase">Deadline</span>
                      <strong class="text-sm text-[#191c1e]">{getDeadlineLabel(match)}</strong>
                    </div>
                  </div>

                  <button
                    aria-pressed={grantSaved}
                    class={`rounded-lg border px-4 py-3 leading-none font-black text-white disabled:cursor-not-allowed disabled:border-[#c6c6cd] disabled:bg-[#eceef0] disabled:text-[#76777d] ${
                      grantSaved ? 'border-[#131b2e] bg-[#131b2e]' : 'border-emerald-700 bg-emerald-700 hover:bg-emerald-800'
                    }`}
                    disabled={!grantRef}
                    type="button"
                    onclick={() => toggleGrantSaved(match.grant)}
                  >
                    {grantSaved ? 'Saved' : 'Save'}
                  </button>
                </article>
              {/each}
            </section>
          {/if}

          <section class="mt-8 rounded-lg border border-slate-200 bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="shortlist-heading">
            <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
              <div>
                <p class={eyebrowClass}>Shortlist</p>
                <h2 id="shortlist-heading" class="m-0 text-2xl leading-tight text-[#191c1e]">Compare saved grants</h2>
              </div>

              <dl class="m-0">
                <div class="grid min-w-20 rounded-lg bg-[#f2f4f6] px-3 py-2">
                  <dt class="text-[11px] font-black text-[#45464d] uppercase">Saved</dt>
                  <dd class="m-0 text-lg font-black text-[#006c49]">{savedGrantRefs.length}</dd>
                </div>
              </dl>
            </div>

            {#if savedGrantRefs.length === 0}
              <p class="m-0 py-8 text-sm leading-6 text-[#45464d]">No grants saved yet.</p>
            {:else}
              <div class="grid gap-0 overflow-hidden rounded-lg border border-slate-200" aria-label="Saved grant comparison">
                <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 bg-[#f2f4f6] px-4 py-3 text-xs font-black text-[#45464d] uppercase max-[840px]:hidden">
                  <span>Grant</span>
                  <span>Program</span>
                  <span>Amount</span>
                  <span>Fit</span>
                  <span>Action</span>
                </div>

                {#each shortlistedGrants as item (item.ref)}
                  {#if item.match}
                    {@const grant = item.match.grant}
                    <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 border-t border-slate-200 px-4 py-4 first:border-t-0 max-[840px]:grid-cols-1">
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Grant</span>
                        <strong class="text-sm text-[#191c1e]">{grant.recipient_legal_name ?? 'Recipient unavailable'}</strong>
                        <small class="break-words text-xs text-[#45464d]">{item.ref}</small>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Program</span>
                        <span class="text-sm text-[#191c1e]">{grant.prog_name_en ?? 'Program unavailable'}</span>
                        <small class="text-xs text-[#45464d]">{grant.owner_org_title ?? 'Organization unavailable'}</small>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Amount</span>
                        <strong class="text-sm text-[#191c1e]">{formatMoney(grant.agreement_value)}</strong>
                        <small class="text-xs text-[#45464d]">{formatDate(grant.agreement_start_date)} start</small>
                      </div>
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Fit</span>
                        <strong class="text-sm text-[#191c1e]">{item.match.matchScore}%</strong>
                        <small class="text-xs text-[#45464d]">{item.match.statusLabel}</small>
                      </div>
                      <div>
                        <button
                          class={compactButtonClass}
                          type="button"
                          onclick={() => removeShortlistedGrant(item.ref)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  {:else}
                    <div class="grid grid-cols-[1.5fr_1.2fr_0.8fr_0.6fr_auto] gap-4 border-t border-slate-200 bg-slate-50 px-4 py-4 first:border-t-0 max-[840px]:grid-cols-1">
                      <div class="grid gap-1">
                        <span class="hidden text-[11px] font-black text-[#45464d] uppercase max-[840px]:block">Grant</span>
                        <strong class="text-sm text-[#191c1e]">Grant not in current results</strong>
                        <small class="break-words text-xs text-[#45464d]">{item.ref}</small>
                      </div>
                      <div><span class="text-sm text-[#45464d]">Program unavailable</span></div>
                      <div><span class="text-sm text-[#45464d]">Amount unavailable</span></div>
                      <div><span class="text-sm text-[#45464d]">Fit unavailable</span></div>
                      <div>
                        <button
                          class={compactButtonClass}
                          type="button"
                          onclick={() => removeShortlistedGrant(item.ref)}
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
</div>
