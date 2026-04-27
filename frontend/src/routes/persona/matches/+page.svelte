<script lang="ts">
  import { browser } from '$app/environment';
  import { hydrateCachedGrantsResult } from '$lib/client/funding-cache';
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
    persona = readStoredPersona() ?? createDefaultPersona();
    profileHydrated = true;
    savedGrantRefs = readSavedGrantRefs();
    shortlistHydrated = true;

    void hydratePersonaGrants();
  });

  async function hydratePersonaGrants() {
    const endpoint = data.grantsQuery?.endpoint;

    if (!endpoint) {
      grantsHydrated = true;
      return;
    }

    const result = await hydrateCachedGrantsResult(endpoint, data.requested);
    clientData = {
      ...data,
      grants: result.records as GrantRecord[],
      total: result.total,
      requested: result.requested,
      error: result.error
    };
    grantsHydrated = true;
  }

  $effect(() => {
    if (!browser || !profileHydrated) {
      return;
    }

    persistPersona(persona);
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
    } catch {
      return null;
    }
  }

  function persistPersona(profile: CompanyPersona) {
    try {
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    } catch {
      // localStorage can be unavailable in private windows or locked-down browsers.
    }
  }

  function saveAndContinue() {
    if (browser) {
      persistPersona(persona);
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
      return `Calendar year ${grantsQuery.year}, ${sortLabel}, ${data.requested} requested.`;
    }

    return `First ${data.requested} grants, ${sortLabel}.`;
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

    return `/persona/matches?${params.toString()}`;
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

<main class="profile-app-shell">
  <aside class="profile-sidebar" aria-label="FundRadar workspace navigation">
    <div class="profile-sidebar__brand">
      <div class="profile-logo" aria-hidden="true">FR</div>
      <div>
        <h1>FundRadar</h1>
        <p>Enterprise Funding</p>
      </div>
    </div>

    <a class="profile-primary-action" href="/persona/matches">
      <span class="material-symbols-outlined" aria-hidden="true">search</span>
      Find Funding
    </a>

    <nav class="profile-nav" aria-label="Profile navigation">
      <a href="/dashboard">
        <span class="material-symbols-outlined" aria-hidden="true">explore</span>
        <span class="profile-nav-label">Discovery</span>
      </a>
      <a href="/persona">
        <span class="material-symbols-outlined" aria-hidden="true">business_center</span>
        <span class="profile-nav-label">Company Profile</span>
      </a>
      <a href="/live-view">
        <span class="material-symbols-outlined" aria-hidden="true">insert_chart</span>
        <span class="profile-nav-label">Analytics</span>
      </a>
      <a class="profile-nav__active" href="/persona/matches" aria-current="page">
        <span class="material-symbols-outlined" aria-hidden="true">description</span>
        <span class="profile-nav-label">Opportunity Matches</span>
      </a>
      <a href="/settings">
        <span class="material-symbols-outlined" aria-hidden="true">settings</span>
        <span class="profile-nav-label">Settings</span>
      </a>
    </nav>

    <div class="profile-sidebar__footer">
      <a href="/">
        <span class="material-symbols-outlined" aria-hidden="true">contact_support</span>
        <span class="profile-nav-label">Support</span>
      </a>
      <a href="/">
        <span class="material-symbols-outlined" aria-hidden="true">logout</span>
        <span class="profile-nav-label">Log Out</span>
      </a>
    </div>
  </aside>

  <section class="profile-workspace" aria-label="Opportunity matches workspace">
    <header class="profile-topbar">
      <label class="profile-search">
        <span class="material-symbols-outlined" aria-hidden="true">search</span>
        <input placeholder="Search profile, keywords, or opportunities..." type="search" />
      </label>

      <div class="profile-topbar__actions">
        <button aria-label="Notifications" class="profile-icon-button" type="button">
          <span class="material-symbols-outlined" aria-hidden="true">notifications</span>
        </button>
        <button aria-label="Help" class="profile-icon-button" type="button">
          <span class="material-symbols-outlined" aria-hidden="true">help_outline</span>
        </button>
        <div class="profile-avatar" aria-label="User profile">FR</div>
      </div>
    </header>

    <div class="profile-canvas">
      <section class="profile-page-intro">
        <div>
          <h2 id="matches-page-heading">Your Opportunity Matches</h2>
          <p>
            Review ranked opportunities and manage saved applications for {applicantName}.
          </p>
        </div>

        <ol class="profile-stepper" aria-label="Profile setup progress">
          <li class="profile-step"><span>1</span><a href="/persona">Profile</a></li>
          <li class="profile-step profile-step--active"><span>2</span>Matches</li>
          <li class="profile-step"><span>3</span><a href="/persona/matches#shortlist-heading">Shortlist</a></li>
        </ol>
      </section>

      <section class="profile-builder company-profile-unified" aria-labelledby="matches-heading">
        <section class="recommendations-panel opportunity-rankings" id="recommendations-panel" aria-labelledby="matches-heading">
        <div class="opportunity-header">
          <div>
            <p class="eyebrow">FundRadar discovery</p>
            <h2 id="matches-heading">Your Opportunity Matches</h2>
            <p>
              Based on {applicantName}'s profile, FundRadar ranked the loaded grants by fit, funding size,
              location, and profile keyword signals.
            </p>
            <p class="source-note">{getGrantQuerySummary()}</p>
          </div>

          <div class="opportunity-sort" aria-label="Sort opportunities">
            <span>Sort by</span>
            <a class={data.filters.sort === 'score' ? 'opportunity-sort__active' : ''} href={getSortHref('score')}>
              Relevance
            </a>
            <a class={data.filters.sort === 'amount' ? 'opportunity-sort__active' : ''} href={getSortHref('amount')}>
              Amount
            </a>
            <a class={data.filters.sort === 'newest' ? 'opportunity-sort__active' : ''} href={getSortHref('newest')}>
              Deadline
            </a>
          </div>
        </div>

        <form class="data-filter-bar data-filter-bar--company profile-filter-bar" method="GET" aria-label="Company grant filters">
          <label class="filter-field">
            <span>Year</span>
            <input
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

          <label class="filter-field">
            <span>Count</span>
            <input
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

          <div class="filter-actions">
            <button class="button" type="submit">Apply</button>
            <a class="button button--secondary" href="/persona/matches">Reset filters</a>
          </div>
        </form>

        <section class="matches-section profile-matches">
          <div class="opportunity-toolbar" aria-label="Grant match controls">
            <label class="filter-toggle">
              <input bind:checked={likelyOnly} type="checkbox" />
              <span>Likely matches only</span>
            </label>

            <dl class="opportunity-mini-stats">
              <div>
                <dt>Likely</dt>
                <dd>{likelyMatchCount}</dd>
              </div>
              <div>
                <dt>Shown</dt>
                <dd>{visibleGrantMatches.length}</dd>
              </div>
              <div>
                <dt>Saved</dt>
                <dd>{savedGrantRefs.length}</dd>
              </div>
            </dl>
          </div>

          {#if !grantsHydrated}
            <section class="state-panel" role="status">
              <h2>Loading cached opportunities</h2>
              <p>Checking local storage before contacting the backend.</p>
            </section>
          {:else if data.error}
            <section class="state-panel" role="status">
              <h2>Backend unavailable</h2>
              <p>{data.error}</p>
            </section>
          {:else if data.grants.length === 0}
            <section class="state-panel" role="status">
              <h2>No grants returned</h2>
              <p>The backend responded, but the selected grants endpoint returned an empty record set.</p>
            </section>
          {:else if visibleGrantMatches.length === 0}
            <section class="state-panel" role="status">
              <h2>No likely matches yet</h2>
              <p>Broaden the company keywords or turn off the likely-only filter to review all loaded grants.</p>
            </section>
          {:else}
            <section class="opportunity-grid" aria-label="Ranked opportunity matches">
              {#if topOpportunity}
                {@const topGrantRef = getGrantRef(topOpportunity.grant)}
                {@const topGrantSaved = topGrantRef ? savedGrantRefSet.has(topGrantRef) : false}
                <article class="opportunity-hero-card">
                  <div class="opportunity-hero-card__content">
                    <div class="opportunity-tags">
                      {#each getOpportunityTags(topOpportunity) as tag (tag)}
                        <span>{tag}</span>
                      {/each}
                    </div>

                    <h3>{getOpportunityTitle(topOpportunity)}</h3>
                    <p class="opportunity-sponsor">{getOpportunitySponsor(topOpportunity)}</p>
                    <p class="opportunity-description">{getOpportunityDescription(topOpportunity)}</p>

                    <div class="opportunity-hero-card__footer">
                      <div>
                        <p>Potential funding</p>
                        <strong>{getFundingLabel(topOpportunity)}</strong>
                      </div>
                      <button
                        aria-pressed={topGrantSaved}
                        class={`opportunity-cta${topGrantSaved ? ' opportunity-cta--saved' : ''}`}
                        disabled={!topGrantRef}
                        type="button"
                        onclick={() => toggleGrantSaved(topOpportunity.grant)}
                      >
                        {topGrantSaved ? 'Saved' : 'Save opportunity'}
                      </button>
                    </div>
                  </div>

                  <aside class="opportunity-score-panel">
                    <div class="opportunity-score-ring opportunity-score-ring--large" aria-label={`${topOpportunity.matchScore} percent match`}>
                      <svg aria-hidden="true" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="42"></circle>
                        <circle
                          class={`opportunity-score-ring__value opportunity-score-ring__value--${getMatchTone(topOpportunity.matchScore)}`}
                          cx="50"
                          cy="50"
                          r="42"
                          pathLength="100"
                          style={`stroke-dashoffset: ${getScoreOffset(topOpportunity.matchScore)}`}
                        ></circle>
                      </svg>
                      <strong>{topOpportunity.matchScore}<span>%</span></strong>
                    </div>

                    <p>{getFitLabel(topOpportunity.matchScore)}</p>
                    <ul>
                      {#each getInsightSignals(topOpportunity) as signal (signal)}
                        <li>{signal}</li>
                      {/each}
                    </ul>
                  </aside>
                </article>
              {/if}

              <aside class="opportunity-profile-card">
                <h3>Profile Strength</h3>
                <p>Your profile is {personaCompleteness}% complete, which improves match confidence for loaded grants.</p>

                <div class="opportunity-profile-card__metric">
                  <span>Data points analyzed</span>
                  <strong>{data.grants.length}</strong>
                  <div><span style={`width: ${personaCompleteness}%`}></span></div>
                </div>

                <div class="opportunity-profile-card__metric">
                  <span>Total matched capital</span>
                  <strong>{formatMoneyValue(totalMatchedCapital)}</strong>
                </div>
              </aside>

              {#each remainingOpportunities as match (match.grant._id)}
                {@const grantRef = getGrantRef(match.grant)}
                {@const grantSaved = grantRef ? savedGrantRefSet.has(grantRef) : false}
                <article class="opportunity-card">
                  <div class="opportunity-card__topline">
                    <div class="opportunity-tags">
                      {#each getOpportunityTags(match).slice(0, 2) as tag (tag)}
                        <span>{tag}</span>
                      {/each}
                    </div>

                    <div class="opportunity-score-ring" aria-label={`${match.matchScore} percent match`}>
                      <svg aria-hidden="true" viewBox="0 0 40 40">
                        <circle cx="20" cy="20" r="16"></circle>
                        <circle
                          class={`opportunity-score-ring__value opportunity-score-ring__value--${getMatchTone(match.matchScore)}`}
                          cx="20"
                          cy="20"
                          r="16"
                          pathLength="100"
                          style={`stroke-dashoffset: ${getScoreOffset(match.matchScore)}`}
                        ></circle>
                      </svg>
                      <strong>{match.matchScore}%</strong>
                    </div>
                  </div>

                  <h3>{getOpportunityTitle(match)}</h3>
                  <p>{getOpportunityDescription(match)}</p>

                  <div class="opportunity-card__meta">
                    <div>
                      <span>Amount</span>
                      <strong>{getFundingLabel(match)}</strong>
                    </div>
                    <div>
                      <span>Deadline</span>
                      <strong>{getDeadlineLabel(match)}</strong>
                    </div>
                  </div>

                  <button
                    aria-pressed={grantSaved}
                    class={`opportunity-save${grantSaved ? ' opportunity-save--active' : ''}`}
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

          <section class="shortlist-panel" aria-labelledby="shortlist-heading">
            <div class="shortlist-panel__header">
              <div>
                <p class="eyebrow">Shortlist</p>
                <h2 id="shortlist-heading">Compare saved grants</h2>
              </div>

              <dl class="company-meter">
                <div>
                  <dt>Saved</dt>
                  <dd>{savedGrantRefs.length}</dd>
                </div>
              </dl>
            </div>

            {#if savedGrantRefs.length === 0}
              <p class="shortlist-empty">No grants saved yet.</p>
            {:else}
              <div class="shortlist-table" aria-label="Saved grant comparison">
                <div class="shortlist-row shortlist-row--head">
                  <span>Grant</span>
                  <span>Program</span>
                  <span>Amount</span>
                  <span>Fit</span>
                  <span>Action</span>
                </div>

                {#each shortlistedGrants as item (item.ref)}
                  {#if item.match}
                    {@const grant = item.match.grant}
                    <div class="shortlist-row">
                      <div>
                        <span class="shortlist-label">Grant</span>
                        <strong>{grant.recipient_legal_name ?? 'Recipient unavailable'}</strong>
                        <small>{item.ref}</small>
                      </div>
                      <div>
                        <span class="shortlist-label">Program</span>
                        <span>{grant.prog_name_en ?? 'Program unavailable'}</span>
                        <small>{grant.owner_org_title ?? 'Organization unavailable'}</small>
                      </div>
                      <div>
                        <span class="shortlist-label">Amount</span>
                        <strong>{formatMoney(grant.agreement_value)}</strong>
                        <small>{formatDate(grant.agreement_start_date)} start</small>
                      </div>
                      <div>
                        <span class="shortlist-label">Fit</span>
                        <strong>{item.match.matchScore}%</strong>
                        <small>{item.match.statusLabel}</small>
                      </div>
                      <div>
                        <button
                          class="button button--secondary button--compact"
                          type="button"
                          onclick={() => removeShortlistedGrant(item.ref)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  {:else}
                    <div class="shortlist-row shortlist-row--missing">
                      <div>
                        <span class="shortlist-label">Grant</span>
                        <strong>Grant not in loaded results</strong>
                        <small>{item.ref}</small>
                      </div>
                      <div><span>Program unavailable</span></div>
                      <div><span>Amount unavailable</span></div>
                      <div><span>Fit unavailable</span></div>
                      <div>
                        <button
                          class="button button--secondary button--compact"
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

              <div class="shortlist-actions">
                <button class="button button--secondary button--compact" type="button" onclick={clearShortlist}>
                  Clear shortlist
                </button>
              </div>
            {/if}
          </section>
        </section>
        </section>
      </section>
    </div>
  </section>
</main>

