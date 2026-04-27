<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
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
  const profileShellClass =
    'flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]';
  const profileCanvasClass = 'mx-auto w-full max-w-[1280px] px-6 py-12 max-md:px-4 max-md:py-7';
  const profileIntroClass = 'mb-12 flex items-end justify-between gap-6 max-lg:grid max-lg:items-start max-md:mb-7';
  const profileBuilderClass = 'grid grid-cols-12 gap-6 max-lg:grid-cols-1';
  const profileCardClass =
    'min-w-0 rounded-lg border border-slate-200 bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.03)] max-md:p-5';
  const profileWideCardClass = `${profileCardClass} col-span-7 p-8 max-lg:col-span-full max-md:p-5`;
  const profileFullCardClass = `${profileCardClass} col-span-full p-8 max-md:p-5`;
  const profileCardHeaderClass = 'mb-5 flex items-start gap-3';
  const profileCardIconClass =
    'grid h-7 min-w-7 place-items-center rounded-lg bg-emerald-50 text-xs font-black text-emerald-700';
  const profileFieldGridClass = 'grid grid-cols-2 gap-5 max-md:grid-cols-1';
  const profileSingleFieldGridClass = 'grid grid-cols-1 gap-5';
  const profileFieldClass = 'grid min-w-0 gap-2 text-xs leading-none font-black text-[#45464d] uppercase';
  const profileInputClass =
    'min-h-[43px] w-full rounded-md border border-[#c6c6cd] bg-[#f7f9fb] px-3 py-2.5 font-normal text-[#191c1e] normal-case leading-[1.4] focus:border-[#0b1c30] focus:outline-[3px] focus:outline-offset-1 focus:outline-[#d3e4fe]';
  const profileTextareaClass = `${profileInputClass} min-h-24 resize-y`;
  const profileChoiceGridClass = 'grid grid-cols-2 gap-3 max-md:grid-cols-1';
  const profileChoiceLabelClass = 'cursor-pointer';
  const profileChoiceInputClass = 'peer sr-only';
  const profileChoiceTextClass =
    'block rounded-lg border border-[#c6c6cd] bg-white px-3.5 py-3 text-center font-bold text-[#45464d] peer-checked:border-[#0b1c30] peer-checked:bg-[#e6e8ea] peer-checked:font-black peer-checked:text-[#0b1c30] peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[#d3e4fe]';
  const profileSplitClass = 'grid grid-cols-2 gap-8 max-lg:grid-cols-1';
  const profileChipGroupClass = 'mb-6 flex flex-wrap gap-2.5';
  const profileChipInputClass = 'peer sr-only';
  const profileFundingFieldClass = `${profileFieldClass} max-w-80`;
  const profileActionsClass =
    'col-span-full mt-1 flex items-center justify-between gap-4 border-t border-slate-200 pt-6 max-md:grid max-md:items-stretch';
  const profileActionsRightClass = 'flex flex-wrap justify-end gap-3 max-md:grid max-md:justify-stretch';
  const profileButtonBaseClass =
    'inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-3 font-extrabold no-underline transition hover:opacity-90 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[#d3e4fe] disabled:cursor-wait disabled:opacity-65 max-md:w-full';
  const profilePrimaryButtonClass = `${profileButtonBaseClass} border-[#006c49] bg-[#006c49] text-white`;
  const profileSecondaryButtonClass = `${profileButtonBaseClass} border-[#c6c6cd] bg-white text-[#191c1e]`;
  const profileGhostButtonClass = `${profileButtonBaseClass} border-transparent bg-transparent text-[#45464d]`;

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
  type ProfileWalkthroughStep = {
    targetId: string;
    icon: string;
    title: string;
    detail: string;
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
  type CopilotQuestion = {
    id: string;
    question: string;
    placeholder: string;
  };
  type CopilotDraft = {
    profile: CompanyPersona;
    confidence: Record<string, number>;
    notes: string[];
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
  const profileBuilderWalkthroughSteps: ProfileWalkthroughStep[] = [
    {
      targetId: 'company-heading',
      icon: 'badge',
      title: 'Core identity',
      detail: 'Enter the legal name, operating name, website, applicant type, and incorporation date.'
    },
    {
      targetId: 'jurisdiction-heading',
      icon: 'location_on',
      title: 'Jurisdiction',
      detail: 'Add the primary province and city so regional funding programs can be matched correctly.'
    },
    {
      targetId: 'scale-heading',
      icon: 'groups',
      title: 'Organization scale',
      detail: 'Choose the employee range that best represents the company today.'
    },
    {
      targetId: 'sector-heading',
      icon: 'category',
      title: 'Sector and objectives',
      detail: 'Select the industry, sub-sector, keywords, funding activities, and target funding amount.'
    },
    {
      targetId: 'profile-actions',
      icon: 'task_alt',
      title: 'Save and continue',
      detail: 'Save the profile to generate ranked opportunity matches from grants and Business Benefits Finder data.'
    }
  ];
  const copilotQuestions: CopilotQuestion[] = [
    {
      id: 'business',
      question: 'What does your company do, and who do you serve?',
      placeholder: 'We build accessibility software for public-sector procurement teams.'
    },
    {
      id: 'location',
      question: 'Where is the company primarily based?',
      placeholder: 'Ottawa, Ontario.'
    },
    {
      id: 'organization',
      question: 'What type of organization is it?',
      placeholder: 'For-profit startup, nonprofit, university lab, municipality, etc.'
    },
    {
      id: 'scale',
      question: 'How many employees do you have?',
      placeholder: 'About 18 full-time employees.'
    },
    {
      id: 'funding_goal',
      question: 'What are you trying to fund?',
      placeholder: 'R&D, hiring engineers, market expansion, equipment, facilities, export growth.'
    },
    {
      id: 'funding_amount',
      question: 'How much funding are you looking for?',
      placeholder: '$250,000.'
    },
    {
      id: 'keywords',
      question: 'Any important keywords, sectors, technologies, or markets?',
      placeholder: 'AI, accessibility, public sector, procurement, Ontario.'
    }
  ];

  let persona = $state(createDefaultPersona());
  let copilotAnswers = $state<Record<string, string>>(createEmptyCopilotAnswers());
  let copilotDraft = $state<CopilotDraft | null>(null);
  let copilotGenerating = $state(false);
  let copilotError = $state('');
  let copilotApplied = $state(false);
  let selectedYear = $state<string | null>(null);
  let selectedCount = $state<string | null>(null);
  let selectedSort = $state<SortMode | null>(null);
  let likelyOnly = $state(false);
  let savedGrantRefs = $state<string[]>([]);
  let shortlistHydrated = $state(false);
  let profileHydrated = $state(false);
  let profileSaved = $state(false);
  let profileSaving = $state(false);
  let profileSaveError = $state('');
  let grantsHydrated = $state(false);
  let profileBuilderOnboardingChecked = $state(false);
  let showProfileBuilderWalkthrough = $state(false);
  let profileBuilderWalkthroughRequired = $state(false);
  let profileBuilderWalkthroughStep = $state(0);

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
  const currentProfileWalkthroughStep = $derived(
    profileBuilderWalkthroughSteps[profileBuilderWalkthroughStep] ?? profileBuilderWalkthroughSteps[0]
  );
  const copilotAnsweredCount = $derived(copilotQuestions.filter((question) => copilotAnswers[question.id]?.trim()).length);
  const copilotDraftChangedFields = $derived(copilotDraft ? getChangedProfileFields(persona, copilotDraft.profile) : []);
  const profileWalkthroughProgressLabel = $derived(
    `Step ${profileBuilderWalkthroughStep + 1} of ${profileBuilderWalkthroughSteps.length}`
  );

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
    hydrateProfileBuilderWalkthrough();

    void hydratePersonaGrants();
  });

  async function hydrateProfile() {
    persona = readStoredPersona() ?? (await readServerPersona()) ?? createDefaultPersona();
    profileHydrated = true;
  }

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

    profileSaved = false;
    profileSaveError = '';
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
    profileSaveError = '';
  }

  function clearPersona() {
    persona = createEmptyPersona();
    likelyOnly = false;
    profileSaved = false;
    profileSaveError = '';
  }

  function createEmptyCopilotAnswers(): Record<string, string> {
    return Object.fromEntries(copilotQuestions.map((question) => [question.id, '']));
  }

  function clearCopilotAnswers() {
    copilotAnswers = createEmptyCopilotAnswers();
    copilotDraft = null;
    copilotError = '';
    copilotApplied = false;
  }

  async function generateCopilotDraft() {
    if (!browser || copilotGenerating) {
      return;
    }

    const answers = copilotQuestions
      .map((question) => ({
        question: question.question,
        answer: copilotAnswers[question.id]?.trim() ?? ''
      }))
      .filter((answer) => answer.answer.length > 0);

    if (answers.length === 0) {
      copilotError = 'Answer at least one question before generating a draft.';
      return;
    }

    copilotGenerating = true;
    copilotError = '';
    copilotApplied = false;

    try {
      const response = await fetch(`${DEFAULT_BACKEND_API_URL}/api/company-profile/copilot/extract`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json'
        },
        body: JSON.stringify({
          answers,
          current_profile: persona,
          timeout: 30
        })
      });
      const payload: unknown = await response.json().catch(() => ({}));

      if (!response.ok) {
        copilotError = readApiError(payload) ?? 'Could not generate a company profile draft.';
        return;
      }

      if (!isRecord(payload) || !isRecord(payload.profile)) {
        copilotError = 'Gemini returned an incomplete profile draft.';
        return;
      }

      copilotDraft = {
        profile: readPersonaRecord(payload.profile),
        confidence: isRecord(payload.confidence) ? readConfidenceMap(payload.confidence) : {},
        notes: Array.isArray(payload.notes) ? payload.notes.map(String).filter(Boolean).slice(0, 5) : []
      };
    } catch {
      copilotError = 'Could not reach the profile copilot service.';
    } finally {
      copilotGenerating = false;
    }
  }

  function applyCopilotDraft() {
    if (!copilotDraft) {
      return;
    }

    persona = {
      ...copilotDraft.profile,
      activities: { ...copilotDraft.profile.activities }
    };
    profileSaved = false;
    profileSaveError = '';
    copilotApplied = true;
  }

  function readApiError(payload: unknown): string | null {
    if (!isRecord(payload)) {
      return null;
    }

    if (typeof payload.detail === 'string') {
      return payload.detail;
    }

    if (isRecord(payload.detail) && typeof payload.detail.message === 'string') {
      return payload.detail.message;
    }

    return null;
  }

  function readConfidenceMap(record: Record<string, unknown>): Record<string, number> {
    return Object.fromEntries(
      Object.entries(record)
        .map(([key, value]) => [key, typeof value === 'number' ? value : Number(value)])
        .filter((entry): entry is [string, number] => Number.isFinite(entry[1]))
    );
  }

  function getChangedProfileFields(current: CompanyPersona, draft: CompanyPersona): string[] {
    const fieldKeys: (keyof Omit<CompanyPersona, 'activities'>)[] = [
      'legalEntityName',
      'doingBusinessAs',
      'incorporationDate',
      'website',
      'province',
      'city',
      'companyType',
      'employeeRange',
      'industry',
      'subSector',
      'keywords',
      'fundingNeed'
    ];
    const changed = fieldKeys.filter((key) => current[key] !== draft[key]).map(getProfileFieldLabel);
    const activityChanged = activityOptions.some((activity) => current.activities[activity.value] !== draft.activities[activity.value]);

    return activityChanged ? [...changed, 'Activities'] : changed;
  }

  function getProfileFieldLabel(key: string): string {
    const labels: Record<string, string> = {
      legalEntityName: 'Legal entity',
      doingBusinessAs: 'Operating name',
      incorporationDate: 'Incorporation date',
      website: 'Website',
      province: 'Province',
      city: 'City',
      companyType: 'Applicant type',
      employeeRange: 'Employee range',
      industry: 'Industry',
      subSector: 'Sub-sector',
      keywords: 'Keywords',
      fundingNeed: 'Funding need'
    };

    return labels[key] ?? key;
  }

  function formatCopilotProfileValue(profile: CompanyPersona, field: string): string {
    if (field === 'location') {
      return [profile.city, profile.province].filter(Boolean).join(', ') || 'Not set';
    }

    if (field === 'companyType') {
      return companyTypes.find((type) => type.value === profile.companyType)?.label ?? profile.companyType;
    }

    if (field === 'employeeRange') {
      return employeeOptions.find((option) => option.value === profile.employeeRange)?.label ?? profile.employeeRange;
    }

    if (field === 'industry') {
      return industryOptions.find((option) => option.value === profile.industry)?.label ?? 'Not set';
    }

    if (field === 'subSector') {
      return subSectorOptions.find((option) => option.value === profile.subSector)?.label ?? 'Not set';
    }

    if (field === 'fundingNeed') {
      return profile.fundingNeed ? moneyFormatter.format(Number(profile.fundingNeed)) : 'Not set';
    }

    if (field === 'activities') {
      const labels = activityOptions.filter((activity) => profile.activities[activity.value]).map((activity) => activity.label);
      return labels.length > 0 ? labels.join(', ') : 'Not set';
    }

    const value = profile[field as keyof CompanyPersona];
    return typeof value === 'string' && value.trim() ? value : 'Not set';
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

  function saveStoredPersona(profile: CompanyPersona): boolean {
    if (!browser) {
      return false;
    }

    try {
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
      return true;
    } catch {
      return false;
    }
  }

  async function saveServerPersona(profile: CompanyPersona): Promise<boolean> {
    const response = await fetch('/dashboard/persona/profile', {
      method: 'PUT',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify(profile)
    });

    if (!response.ok || response.redirected) {
      return false;
    }

    try {
      localStorage.removeItem(PROFILE_STORAGE_KEY);
    } catch {
      // localStorage can be unavailable in private windows or locked-down browsers.
    }

    return true;
  }

  async function saveAndContinue() {
    if (!browser || profileSaving) {
      return;
    }

    if (profileBuilderWalkthroughRequired) {
      showProfileBuilderWalkthrough = true;
      return;
    }

    profileSaving = true;
    profileSaved = false;
    profileSaveError = '';

    const savedLocally = saveStoredPersona(persona);
    let savedRemotely = false;

    try {
      savedRemotely = await saveServerPersona(persona);
    } catch {
      savedRemotely = false;
    }

    if (!savedLocally && !savedRemotely) {
      profileSaveError = 'Could not save this profile. Check browser storage and try again.';
      profileSaving = false;
      return;
    }

    profileSaved = true;

    try {
      await goto('/dashboard/persona/matches');
    } finally {
      profileSaving = false;
    }
  }

  function hydrateProfileBuilderWalkthrough() {
    if (!browser || profileBuilderOnboardingChecked) {
      return;
    }

    profileBuilderOnboardingChecked = true;
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('onboarding') === '1' || params.get('onboarding') === 'company-profile';

    if (!requested) {
      return;
    }

    showProfileBuilderWalkthrough = true;
    profileBuilderWalkthroughRequired = true;
    profileBuilderWalkthroughStep = 0;
    setTimeout(() => {
      focusProfileBuilderWalkthroughStep();
    }, 0);
  }

  function finishProfileBuilderWalkthrough() {
    showProfileBuilderWalkthrough = false;
    profileBuilderWalkthroughRequired = false;
    removeProfileBuilderOnboardingSearchParam(new URLSearchParams(window.location.search));
  }

  function advanceProfileBuilderWalkthrough() {
    profileBuilderWalkthroughStep = Math.min(
      profileBuilderWalkthroughSteps.length - 1,
      profileBuilderWalkthroughStep + 1
    );
    setTimeout(() => {
      focusProfileBuilderWalkthroughStep();
    }, 0);
  }

  function retreatProfileBuilderWalkthrough() {
    profileBuilderWalkthroughStep = Math.max(0, profileBuilderWalkthroughStep - 1);
    setTimeout(() => {
      focusProfileBuilderWalkthroughStep();
    }, 0);
  }

  function focusProfileBuilderWalkthroughStep() {
    const target = document.getElementById(currentProfileWalkthroughStep.targetId);
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function removeProfileBuilderOnboardingSearchParam(params: URLSearchParams) {
    params.delete('onboarding');
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`;
    window.history.replaceState(window.history.state, '', nextUrl);
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

    return `/dashboard/persona?${params.toString()}`;
  }
</script>

<svelte:head>
  <title>Company Profile | FundRadar</title>
  <meta name="description" content="Build a company profile and rank grant opportunities with FundRadar." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class={profileShellClass}>
  <WorkspaceSidebar active="profile" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search profile, keywords, or opportunities..." />

    <main class="flex-1 overflow-y-auto">
      <div class={profileCanvasClass}>
      <section class={profileIntroClass}>
        <div>
          <h2 id="company-profile-heading" class="m-0 text-4xl leading-tight text-[#191c1e] max-md:text-3xl">Company Profile</h2>
          <p class="mt-2 max-w-[66ch] leading-7 text-[#45464d]">
            Complete your organization profile before reviewing ranked opportunity matches.
          </p>
        </div>
      </section>

      <section class={`${profileCardClass} mb-6 p-8 max-md:p-5`} aria-labelledby="profile-copilot-heading">
        <div class="mb-6 flex items-start justify-between gap-4 max-lg:grid">
          <div>
            <p class="m-0 mb-2 text-xs font-black tracking-normal text-emerald-700 uppercase">Gemini copilot</p>
            <h3 id="profile-copilot-heading" class="m-0 text-2xl leading-snug text-[#191c1e]">Company Profile Copilot</h3>
            <p class="mt-1 max-w-[72ch] text-sm leading-6 text-[#45464d]">
              Answer a few questions in plain language, then review a structured profile draft before applying it.
            </p>
          </div>

          <div class="rounded-lg bg-[#f2f4f6] px-4 py-3 text-right max-lg:text-left">
            <p class="m-0 text-[11px] font-black text-[#45464d] uppercase">Answered</p>
            <p class="m-0 mt-1 text-xl font-black text-[#006c49]">{copilotAnsweredCount}/{copilotQuestions.length}</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 max-lg:grid-cols-1">
          {#each copilotQuestions as question (question.id)}
            <label class={profileFieldClass}>
              <span>{question.question}</span>
              <textarea
                class={`${profileTextareaClass} min-h-20`}
                bind:value={copilotAnswers[question.id]}
                placeholder={question.placeholder}
                rows="2"
              ></textarea>
            </label>
          {/each}
        </div>

        <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5">
          <div class="min-h-5 text-sm font-extrabold" aria-live="polite">
            {#if copilotError}
              <span class="text-red-700">{copilotError}</span>
            {:else if copilotApplied}
              <span class="text-emerald-700">Draft applied to the form.</span>
            {:else if copilotDraft}
              <span class="text-emerald-700">Draft ready for review.</span>
            {/if}
          </div>

          <div class="flex flex-wrap justify-end gap-3 max-md:grid max-md:w-full">
            <button class={profileGhostButtonClass} type="button" onclick={clearCopilotAnswers}>Clear answers</button>
            <button class={profilePrimaryButtonClass} disabled={copilotGenerating || copilotAnsweredCount === 0} type="button" onclick={generateCopilotDraft}>
              {copilotGenerating ? 'Generating...' : 'Generate profile draft'}
              <span class="material-symbols-outlined" aria-hidden="true">auto_awesome</span>
            </button>
          </div>
        </div>

        {#if copilotDraft}
          <div class="mt-6 grid grid-cols-[minmax(0,1fr)_260px] gap-5 max-lg:grid-cols-1">
            <div class="rounded-lg border border-slate-200 bg-[#f8fafc] p-4">
              <div class="mb-4 flex items-start justify-between gap-3 max-md:grid">
                <div>
                  <p class="m-0 text-xs font-black tracking-normal text-emerald-700 uppercase">Draft profile</p>
                  <h4 class="m-0 mt-1 text-xl leading-snug text-[#191c1e]">
                    {copilotDraft.profile.doingBusinessAs || copilotDraft.profile.legalEntityName || 'Company profile draft'}
                  </h4>
                </div>
                <button class={profileSecondaryButtonClass} type="button" onclick={applyCopilotDraft}>Apply to form</button>
              </div>

              <dl class="m-0 grid grid-cols-2 gap-3 text-sm max-md:grid-cols-1">
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Legal entity</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'legalEntityName')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Location</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'location')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Applicant type</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'companyType')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Employees</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'employeeRange')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Industry</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'industry')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Sub-sector</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'subSector')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Funding need</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'fundingNeed')}</dd>
                </div>
                <div>
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Activities</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'activities')}</dd>
                </div>
                <div class="col-span-2 max-md:col-span-1">
                  <dt class="text-[11px] font-black text-[#76777d] uppercase">Keywords</dt>
                  <dd class="m-0 mt-1 text-[#191c1e]">{formatCopilotProfileValue(copilotDraft.profile, 'keywords')}</dd>
                </div>
              </dl>
            </div>

            <aside class="rounded-lg border border-slate-200 bg-white p-4">
              <p class="m-0 text-xs font-black tracking-normal text-emerald-700 uppercase">Review</p>
              <p class="mt-2 text-sm leading-6 text-[#45464d]">
                {copilotDraftChangedFields.length > 0
                  ? `${copilotDraftChangedFields.length} form fields will change.`
                  : 'No form field changes detected.'}
              </p>

              {#if copilotDraftChangedFields.length > 0}
                <div class="mt-3 flex flex-wrap gap-2">
                  {#each copilotDraftChangedFields as field (field)}
                    <span class="rounded-full border border-slate-200 bg-[#f2f4f6] px-2.5 py-1 text-xs font-black text-[#45464d]">{field}</span>
                  {/each}
                </div>
              {/if}

              {#if copilotDraft.notes.length > 0}
                <ul class="mt-4 grid list-none gap-2 p-0 text-sm leading-6 text-[#45464d]">
                  {#each copilotDraft.notes as note (note)}
                    <li class="relative pl-4 before:absolute before:left-0 before:text-emerald-700 before:content-['-']">{note}</li>
                  {/each}
                </ul>
              {/if}
            </aside>
          </div>
        {/if}
      </section>

      <section class={profileBuilderClass} aria-labelledby="company-heading">
        <section class={profileWideCardClass} aria-labelledby="company-heading">
          <div class={profileCardHeaderClass}>
            <span class={profileCardIconClass} aria-hidden="true">ID</span>
            <div>
              <h3 id="company-heading" class="m-0 text-2xl leading-snug text-[#191c1e]">Core Identity</h3>
              <p class="mt-1 text-sm leading-6 text-[#45464d]">Your official registered business information.</p>
            </div>
          </div>

          <div class={profileFieldGridClass}>
            <label class={profileFieldClass}>
              <span>Legal Entity Name</span>
              <input class={profileInputClass} bind:value={persona.legalEntityName} name="legal-entity-name" placeholder="Acme Innovations Inc." />
            </label>

            <label class={profileFieldClass}>
              <span>Doing Business As</span>
              <input class={profileInputClass} bind:value={persona.doingBusinessAs} name="doing-business-as" placeholder="Acme Tech" />
            </label>

            <label class={profileFieldClass}>
              <span>Website</span>
              <input class={profileInputClass} bind:value={persona.website} name="website" placeholder="https://example.com" type="url" />
            </label>

            <label class={profileFieldClass}>
              <span>Applicant Type</span>
              <select class={profileInputClass} bind:value={persona.companyType} name="company-type">
                {#each companyTypes as companyType (companyType.value)}
                  <option value={companyType.value}>{companyType.label}</option>
                {/each}
              </select>
            </label>

            <label class={profileFieldClass}>
              <span>Date of Incorporation</span>
              <input class={profileInputClass} bind:value={persona.incorporationDate} name="incorporation-date" type="date" />
            </label>
          </div>
        </section>

        <div class="col-span-5 grid gap-6 max-lg:col-span-full">
          <section class={profileCardClass} aria-labelledby="jurisdiction-heading">
            <div class={profileCardHeaderClass}>
              <span class={profileCardIconClass} aria-hidden="true">ON</span>
              <div>
                <h3 id="jurisdiction-heading" class="m-0 text-2xl leading-snug text-[#191c1e]">Jurisdiction</h3>
                <p class="mt-1 text-sm leading-6 text-[#45464d]">Primary operational headquarters.</p>
              </div>
            </div>

            <div class={profileSingleFieldGridClass}>
              <label class={profileFieldClass}>
                <span>Province / Territory</span>
                <select class={profileInputClass} bind:value={persona.province} name="province">
                  <option value="">Select Region</option>
                  {#each provinceOptions as province (province.value)}
                    <option value={province.value}>{province.label}</option>
                  {/each}
                </select>
              </label>

              <label class={profileFieldClass}>
                <span>City</span>
                <input class={profileInputClass} bind:value={persona.city} name="city" placeholder="Ottawa" />
              </label>
            </div>
          </section>

          <section class={profileCardClass} aria-labelledby="scale-heading">
            <div class={profileCardHeaderClass}>
              <span class={profileCardIconClass} aria-hidden="true">FTE</span>
              <div>
                <h3 id="scale-heading" class="m-0 text-2xl leading-snug text-[#191c1e]">Organization Scale</h3>
                <p class="mt-1 text-sm leading-6 text-[#45464d]">Current full-time equivalent employees.</p>
              </div>
            </div>

            <div class={profileChoiceGridClass}>
              {#each employeeOptions as option (option.value)}
                <label class={profileChoiceLabelClass}>
                  <input
                    class={profileChoiceInputClass}
                    checked={persona.employeeRange === option.value}
                    name="employees"
                    type="radio"
                    value={option.value}
                    onchange={() => {
                      persona.employeeRange = option.value;
                    }}
                  />
                  <span class={profileChoiceTextClass}>{option.label}</span>
                </label>
              {/each}
            </div>
          </section>
        </div>

        <section class={profileFullCardClass} aria-labelledby="sector-heading">
          <div class={profileSplitClass}>
            <div>
              <div class={profileCardHeaderClass}>
                <span class={profileCardIconClass} aria-hidden="true">NA</span>
                <div>
                  <h3 id="sector-heading" class="m-0 text-2xl leading-snug text-[#191c1e]">Sector & Industry</h3>
                  <p class="mt-1 text-sm leading-6 text-[#45464d]">Defines eligibility for specialized sector grants.</p>
                </div>
              </div>

              <div class={profileSingleFieldGridClass}>
                <label class={profileFieldClass}>
                  <span>Primary Industry</span>
                  <select class={profileInputClass} bind:value={persona.industry} name="industry">
                    <option value="">Select Industry</option>
                    {#each industryOptions as industry (industry.value)}
                      <option value={industry.value}>{industry.label}</option>
                    {/each}
                  </select>
                </label>

                <label class={profileFieldClass}>
                  <span>Sub-Sector Focus</span>
                  <select class={profileInputClass} bind:value={persona.subSector} name="sub-sector">
                    <option value="">Select Focus</option>
                    {#each subSectorOptions as subSector (subSector.value)}
                      <option value={subSector.value}>{subSector.label}</option>
                    {/each}
                  </select>
                </label>

                <label class={profileFieldClass}>
                  <span>Additional Keywords</span>
                  <textarea
                    class={profileTextareaClass}
                    bind:value={persona.keywords}
                    name="keywords"
                    placeholder="accessibility, public sector, procurement"
                    rows="3"
                  ></textarea>
                </label>
              </div>
            </div>

            <div>
              <div class={profileCardHeaderClass}>
                <span class={profileCardIconClass} aria-hidden="true">CAP</span>
                <div>
                  <h3 class="m-0 text-2xl leading-snug text-[#191c1e]">Capital Objectives</h3>
                  <p class="mt-1 text-sm leading-6 text-[#45464d]">Select all areas where funding will be allocated.</p>
                </div>
              </div>

              <div class={profileChipGroupClass}>
                {#each activityOptions as activity (activity.value)}
                  <label class="cursor-pointer">
                    <input class={profileChipInputClass} bind:checked={persona.activities[activity.value]} type="checkbox" />
                    <span
                      class={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm leading-tight ${
                        persona.activities[activity.value]
                          ? 'border-emerald-700 bg-emerald-50 font-extrabold text-emerald-800'
                          : 'border-[#c6c6cd] bg-[#eceef0] text-[#191c1e]'
                      } peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[#d3e4fe]`}
                    >
                      {#if persona.activities[activity.value]}
                        <span aria-hidden="true">✓</span>
                      {/if}
                      {activity.label}
                    </span>
                  </label>
                {/each}
              </div>

              <label class={profileFundingFieldClass}>
                <span>Target Funding Amount</span>
                <input class={profileInputClass} bind:value={persona.fundingNeed} min="1" name="funding-need" placeholder="250000" type="number" />
              </label>
            </div>
          </div>
        </section>

        <section id="profile-actions" class={profileActionsClass} aria-label="Profile actions">
          <a class={profileSecondaryButtonClass} href="/dashboard">Back</a>
          <div class={profileActionsRightClass}>
            <button class={profileGhostButtonClass} type="button" onclick={clearPersona}>Clear profile</button>
            <button class={profileSecondaryButtonClass} type="button" onclick={resetPersona}>Reset sample</button>
            <button class={profilePrimaryButtonClass} disabled={profileSaving} type="button" onclick={saveAndContinue}>
              {profileSaving ? 'Saving...' : 'Save and continue'}
              <span class="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
            </button>
          </div>
        </section>

        <div
          class={`col-span-full min-h-5 text-right text-sm font-extrabold max-md:text-left ${profileSaveError ? 'text-red-700' : 'text-emerald-700'}`}
          aria-live="polite"
        >
          {#if profileSaveError}
            {profileSaveError}
          {:else if profileSaved}
            Profile saved.
          {/if}
        </div>
      </section>
    </div>
  </main>
</div>

  {#if showProfileBuilderWalkthrough}
    <div class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b1c30]/55 p-4 backdrop-blur-sm" role="presentation">
      <div
        aria-labelledby="profile-builder-walkthrough-heading"
        aria-live="polite"
        aria-modal="true"
        class="w-full max-w-[520px] rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_20px_70px_rgba(15,23,42,0.24)]"
        role="dialog"
      >
        <div class="mb-4 flex items-start gap-3">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-700 text-white">
            <span class="material-symbols-outlined text-[22px]">{currentProfileWalkthroughStep.icon}</span>
          </span>
          <div>
            <p class="m-0 mb-1 text-xs font-black uppercase tracking-normal text-emerald-700">{profileWalkthroughProgressLabel}</p>
            <h3 id="profile-builder-walkthrough-heading" class="m-0 text-xl leading-tight text-[#191c1e]">
              {currentProfileWalkthroughStep.title}
            </h3>
          </div>
        </div>

        <p class="m-0 mb-4 text-sm leading-6 text-[#45464d]">{currentProfileWalkthroughStep.detail}</p>

        <p class="m-0 mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
          Finish this walkthrough before saving and reviewing matches.
        </p>

        <div class="flex flex-wrap justify-end gap-2 border-t border-[#e0e3e5] pt-4">
          <button
            class="rounded-lg border border-[#c6c6cd] px-3 py-2 text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={profileBuilderWalkthroughStep === 0}
            type="button"
            onclick={retreatProfileBuilderWalkthrough}
          >
            Back
          </button>
          {#if profileBuilderWalkthroughStep < profileBuilderWalkthroughSteps.length - 1}
            <button class="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" type="button" onclick={advanceProfileBuilderWalkthrough}>
              Next
            </button>
          {:else}
            <button class="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" type="button" onclick={finishProfileBuilderWalkthrough}>
              Finish
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>
