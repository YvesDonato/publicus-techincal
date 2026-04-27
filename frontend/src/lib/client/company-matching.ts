export type GenericRecord = Record<string, unknown>;
export type ActivityKey = 'research' | 'hiring' | 'equipment' | 'export' | 'facilities' | 'sustainability';
export type CompanyType = 'for-profit' | 'nonprofit' | 'academic' | 'public-sector';
export type EmployeeRange = '1-10' | '11-50' | '51-200' | '200+';

export type CompanyProfile = {
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

export type GrantRecordLike = {
  agreement_value?: string | null;
  agreement_start_date?: string | null;
  recipient_city?: string | null;
  recipient_province?: string | null;
  [key: string]: unknown;
};

export type MatchTone = 'likely' | 'review' | 'low';
export type ScoredRecord<TRecord> = {
  record: TRecord;
  amount: number | null;
  matchScore: number;
  statusLabel: string;
  statusTone: MatchTone;
  reasons: string[];
  risks: string[];
  matchedKeywords: string[];
};

export const PROFILE_STORAGE_KEY = 'publicus.companyProfile.v1';
export const LIKELY_MATCH_THRESHOLD = 75;
export const REVIEW_MATCH_THRESHOLD = 55;
const PROFILE_FETCH_TIMEOUT_MS = 6000;

const activityOptions: { value: ActivityKey; terms: string[] }[] = [
  { value: 'research', terms: ['research', 'development', 'r&d', 'innovation', 'pilot'] },
  { value: 'hiring', terms: ['hiring', 'employment', 'jobs', 'workforce', 'training'] },
  { value: 'equipment', terms: ['equipment', 'machinery', 'capital', 'purchase'] },
  { value: 'export', terms: ['export', 'international', 'market', 'commercialization'] },
  { value: 'facilities', terms: ['facility', 'facilities', 'building', 'infrastructure'] },
  { value: 'sustainability', terms: ['green', 'sustainability', 'climate', 'emissions', 'energy'] }
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

const companyTypes: CompanyType[] = ['for-profit', 'nonprofit', 'academic', 'public-sector'];
const employeeRanges: EmployeeRange[] = ['1-10', '11-50', '51-200', '200+'];

export function createEmptyCompanyProfile(): CompanyProfile {
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

export async function loadCompanyProfile(): Promise<CompanyProfile> {
  return (await readServerCompanyProfile()) ?? readStoredCompanyProfile() ?? createEmptyCompanyProfile();
}

export function hasProfileSignals(profile: CompanyProfile): boolean {
  return [
    profile.legalEntityName,
    profile.doingBusinessAs,
    profile.province,
    profile.city,
    profile.industry,
    profile.subSector,
    profile.keywords,
    profile.fundingNeed,
    ...selectedActivities(profile)
  ].some((value) => value.trim().length > 0);
}

export function companyDisplayName(profile: CompanyProfile): string {
  return profile.doingBusinessAs || profile.legalEntityName || 'your company';
}

export function buildCompanyKeywords(profile: CompanyProfile): string[] {
  const manualKeywords = parseListInput(profile.keywords);
  const activities = selectedActivities(profile);
  const activityKeywords = activities.flatMap((activity) => activityOptions.find((item) => item.value === activity)?.terms ?? []);
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

export function scoreGrantRecord<TRecord extends GrantRecordLike>(record: TRecord, profile: CompanyProfile): ScoredRecord<TRecord> {
  const keywords = buildCompanyKeywords(profile);
  const text = grantRecordText(record);
  const amount = parseMoney(record.agreement_value);
  const fundingNeed = parseMoney(profile.fundingNeed);
  const province = profile.province.trim().toUpperCase();
  const city = normalizeTerm(profile.city);
  const reasons: string[] = [];
  const risks: string[] = [];
  let score = hasProfileSignals(profile) ? 25 : 40;

  const matchedKeywords = keywords.filter((keyword) => termAppearsInText(text, keyword));
  if (matchedKeywords.length > 0) {
    score += Math.min(34, matchedKeywords.length * 7);
    reasons.push(`Matches profile terms: ${matchedKeywords.slice(0, 5).join(', ')}.`);
  } else if (keywords.length > 0) {
    risks.push('No direct keyword overlap with the company profile.');
  }

  if (province && String(record.recipient_province ?? '').toUpperCase() === province) {
    score += 18;
    reasons.push(`Record is associated with ${province}.`);
  } else if (province && record.recipient_province) {
    risks.push(`Record location is ${record.recipient_province}, not ${province}.`);
  }

  if (city && record.recipient_city && normalizeTerm(String(record.recipient_city)) === city) {
    score += 6;
    reasons.push(`City signal matches ${record.recipient_city}.`);
  }

  if (amount !== null && fundingNeed !== null) {
    if (amount >= fundingNeed) {
      score += 12;
      reasons.push('Historical award value can cover the profile funding target.');
    } else {
      score += 4;
      risks.push('Historical award value is below the profile funding target.');
    }

    if (amount >= fundingNeed * 0.25 && amount <= fundingNeed * 4) {
      score += 6;
      reasons.push('Historical award size is in a practical range for this profile.');
    }
  }

  addCompanyTypeSignals(profile, text, reasons, risks, (points) => {
    score += points;
  });

  return buildScoredRecord(record, amount, score, reasons, risks, matchedKeywords);
}

export function scoreBenefitRecord<TRecord extends GenericRecord>(record: TRecord, profile: CompanyProfile): ScoredRecord<TRecord> {
  const keywords = buildCompanyKeywords(profile);
  const text = genericRecordText(record);
  const amount = parseMoneyFromRecord(record);
  const fundingNeed = parseMoney(profile.fundingNeed);
  const province = normalizeTerm(profile.province);
  const city = normalizeTerm(profile.city);
  const reasons: string[] = [];
  const risks: string[] = [];
  let score = hasProfileSignals(profile) ? 30 : 45;

  const matchedKeywords = keywords.filter((keyword) => termAppearsInText(text, keyword));
  if (matchedKeywords.length > 0) {
    score += Math.min(40, matchedKeywords.length * 8);
    reasons.push(`Matches profile terms: ${matchedKeywords.slice(0, 5).join(', ')}.`);
  } else if (keywords.length > 0) {
    risks.push('No direct keyword overlap with this available program.');
  }

  if (province && termAppearsInText(text, province)) {
    score += 10;
    reasons.push(`Program text includes ${profile.province.toUpperCase()}.`);
  }

  if (city && termAppearsInText(text, city)) {
    score += 6;
    reasons.push(`Program text includes ${profile.city}.`);
  }

  if (amount !== null && fundingNeed !== null) {
    score += amount >= fundingNeed ? 10 : 4;
    reasons.push('Program includes an amount that can be compared with the profile funding target.');
  }

  addCompanyTypeSignals(profile, text, reasons, risks, (points) => {
    score += points;
  });

  if (isCurrentlyAvailableRecord(record)) {
    score += 8;
    reasons.push('Record appears available in the current Business Benefits Finder feed.');
  } else {
    score -= 30;
    risks.push('Record status appears closed or inactive.');
  }

  return buildScoredRecord(record, amount, score, reasons, risks, matchedKeywords);
}

export function isCurrentlyAvailableRecord(record: GenericRecord): boolean {
  const text = genericRecordText(record);
  return !/\b(closed|expired|inactive|archived|not accepting|no longer accepting|application closed)\b/i.test(text);
}

export function sortScoredRecords<TRecord>(
  records: ScoredRecord<TRecord>[],
  mode: 'score' | 'amount' | 'newest',
  getDateValue: (record: TRecord) => number
): ScoredRecord<TRecord>[] {
  return [...records].sort((left, right) => {
    if (mode === 'amount') {
      return (right.amount ?? 0) - (left.amount ?? 0);
    }

    if (mode === 'newest') {
      return getDateValue(right.record) - getDateValue(left.record);
    }

    return right.matchScore - left.matchScore;
  });
}

export function parseMoney(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function genericRecordText(record: GenericRecord): string {
  return Object.entries(record)
    .map(([key, value]) => `${key} ${valueToSearchText(value)}`)
    .join(' ')
    .toLowerCase();
}

function grantRecordText(record: GrantRecordLike): string {
  return [
    record.recipient_legal_name,
    record.prog_name_en,
    record.prog_purpose_en,
    record.agreement_title_en,
    record.description_en,
    record.expected_results_en,
    record.owner_org_title,
    record.recipient_city,
    record.recipient_province,
    record.ref_number
  ]
    .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    .join(' ')
    .toLowerCase();
}

function buildScoredRecord<TRecord>(
  record: TRecord,
  amount: number | null,
  score: number,
  reasons: string[],
  risks: string[],
  matchedKeywords: string[]
): ScoredRecord<TRecord> {
  const matchScore = Math.max(0, Math.min(100, Math.round(score)));
  const status =
    matchScore >= LIKELY_MATCH_THRESHOLD
      ? { label: 'Likely match', tone: 'likely' as const }
      : matchScore >= REVIEW_MATCH_THRESHOLD
        ? { label: 'Worth review', tone: 'review' as const }
        : { label: 'Low confidence', tone: 'low' as const };

  return {
    record,
    amount,
    matchScore,
    statusLabel: status.label,
    statusTone: status.tone,
    reasons: (reasons.length > 0 ? unique(reasons) : ['Add more company profile detail to improve match confidence.']).slice(0, 4),
    risks: unique(risks).slice(0, 3),
    matchedKeywords
  };
}

function addCompanyTypeSignals(
  profile: CompanyProfile,
  text: string,
  reasons: string[],
  risks: string[],
  addScore: (points: number) => void
) {
  if (profile.companyType === 'academic' && /university|college|research|academic/.test(text)) {
    addScore(10);
    reasons.push('Academic or research language appears in the record.');
  } else if (profile.companyType === 'nonprofit' && /non.?profit|society|association|institute|foundation|council/.test(text)) {
    addScore(8);
    reasons.push('Nonprofit-style language appears in the record.');
  } else if (profile.companyType === 'for-profit' && /business|company|sme|small and medium|enterprise|commercial/.test(text)) {
    addScore(8);
    reasons.push('Business eligibility language appears in the record.');
  } else if (profile.companyType === 'public-sector' && /municipal|government|public sector|community/.test(text)) {
    addScore(8);
    reasons.push('Public-sector language appears in the record.');
  } else if (hasProfileSignals(profile)) {
    risks.push('Applicant type eligibility is not explicit in this record.');
  }
}

function selectedActivities(profile: CompanyProfile): ActivityKey[] {
  return activityOptions.filter((activity) => profile.activities[activity.value]).map((activity) => activity.value);
}

function parseListInput(value: string): string[] {
  return unique(
    value
      .split(/[,;\n]/)
      .map((item) => normalizeTerm(item))
      .filter((item) => item.length > 1)
  );
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

function normalizeTerm(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
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

function valueToSearchText(value: unknown): string {
  if (value === null || value === undefined || value === '') {
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

  return String(value);
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function isRecord(value: unknown): value is GenericRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readStringField(record: GenericRecord, key: keyof CompanyProfile, fallback: string): string {
  const value = record[key];
  return typeof value === 'string' ? value : fallback;
}

function readCompanyProfileRecord(parsed: GenericRecord): CompanyProfile {
  const defaults = createEmptyCompanyProfile();
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
    companyType: companyTypes.includes(companyType as CompanyType) ? (companyType as CompanyType) : defaults.companyType,
    employeeRange: employeeRanges.includes(employeeRange as EmployeeRange) ? (employeeRange as EmployeeRange) : defaults.employeeRange,
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

async function readServerCompanyProfile(): Promise<CompanyProfile | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), PROFILE_FETCH_TIMEOUT_MS);

  try {
    const response = await fetch('/dashboard/persona/profile', { signal: controller.signal });
    if (!response.ok) {
      return null;
    }

    const payload: unknown = await response.json();
    if (!isRecord(payload) || !isRecord(payload.profile)) {
      return null;
    }

    return readCompanyProfileRecord(payload.profile);
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
}

function readStoredCompanyProfile(): CompanyProfile | null {
  try {
    const rawValue = localStorage.getItem(PROFILE_STORAGE_KEY);
    const parsed = rawValue ? JSON.parse(rawValue) : null;

    if (!isRecord(parsed)) {
      return null;
    }

    return readCompanyProfileRecord(parsed);
  } catch {
    return null;
  }
}
