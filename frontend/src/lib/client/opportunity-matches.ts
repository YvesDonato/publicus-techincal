import {
  LIKELY_MATCH_THRESHOLD,
  REVIEW_MATCH_THRESHOLD,
  buildCompanyKeywords,
  parseMoney,
  type ActivityKey,
  type CompanyProfile,
  type GenericRecord,
  type GrantRecordLike,
  type MatchTone
} from './company-matching';
import type { SemanticScore } from './semantic-scoring';

export type OpportunityGrantMatch<TRecord extends GrantRecordLike = GrantRecordLike> = {
  grant: TRecord;
  amount: number | null;
  matchScore: number;
  statusLabel: string;
  statusTone: MatchTone;
  reasons: string[];
  risks: string[];
  nextActions: string[];
};

export type OpportunityBenefitMatch<TRecord extends GenericRecord = GenericRecord> = {
  record: TRecord;
  amount: number | null;
  estimatedAmount: number | null;
  potentialFunding: number | null;
  historicalEvidenceCount: number;
  matchedKeywords: string[];
  matchScore: number;
  semanticScore?: number | null;
  ruleScore?: number | null;
  statusLabel: string;
  statusTone: MatchTone;
  reasons: string[];
  risks: string[];
  nextActions: string[];
};

const activityOptions: { value: ActivityKey; terms: string[] }[] = [
  { value: 'research', terms: ['research', 'development', 'r&d', 'innovation', 'pilot'] },
  { value: 'hiring', terms: ['hiring', 'employment', 'jobs', 'workforce', 'training'] },
  { value: 'equipment', terms: ['equipment', 'machinery', 'capital', 'purchase'] },
  { value: 'export', terms: ['export', 'international', 'market', 'commercialization'] },
  { value: 'facilities', terms: ['facility', 'facilities', 'building', 'infrastructure'] },
  { value: 'sustainability', terms: ['green', 'sustainability', 'climate', 'emissions', 'energy'] }
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
const dateFields = ['deadline', 'closing_date', 'end_date', 'date', 'updated_at', 'modified'];
const idFields = ['_id', 'id', 'record_id', 'project_id', 'application_id', 'token', 'reference', 'url'];

export function createDefaultOpportunityProfile(): CompanyProfile {
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

export function scoreOpportunityGrantRecord<TRecord extends GrantRecordLike>(
  grant: TRecord,
  profile: CompanyProfile
): OpportunityGrantMatch<TRecord> {
  const keywords = buildCompanyKeywords(profile);
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
      reasons.push('Grant value can cover the profile funding target.');
    } else {
      score += 4;
      risks.push('Grant value is below the profile funding target.');
    }

    if (amount >= fundingNeed * 0.25 && amount <= fundingNeed * 4) {
      score += 6;
      reasons.push('Funding size is in a practical range for this company profile.');
    }
  }

  addCompanyTypeSignals(profile, text, reasons, risks, (points) => {
    score += points;
  });

  if (!grant.agreement_start_date) {
    risks.push('Start date is missing from this record.');
  }

  if (matchedKeywords.length > 0) {
    nextActions.push(`Frame the project around ${matchedKeywords.slice(0, 2).join(' and ')}.`);
  }

  if (amount !== null && fundingNeed !== null) {
    nextActions.push('Compare the budget request with the historical grant value.');
  }

  if (profile.website) {
    nextActions.push('Use the company website to draft a short applicant description.');
  }

  nextActions.push('Confirm applicant type, deadline, and eligible activities in the program guide.');

  const { label, tone } = getStatus(score);

  return {
    grant,
    amount,
    matchScore: clampScore(score),
    statusLabel: label,
    statusTone: tone,
    reasons: reasons.slice(0, 4),
    risks: (risks.length > 0 ? risks : ['Eligibility details are not included in this first-record view.']).slice(0, 3),
    nextActions: unique(nextActions).slice(0, 3)
  };
}

export function scoreOpportunityBenefitRecord<TRecord extends GenericRecord>(
  record: TRecord,
  profile: CompanyProfile,
  historicalMatches: OpportunityGrantMatch[]
): OpportunityBenefitMatch<TRecord> {
  const keywords = buildCompanyKeywords(profile);
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

  const historicalEvidence = findHistoricalEvidence(record, profile, historicalMatches, keywords, matchedKeywords);
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
    nextActions.push('Compare the project budget with the funding signal.');
  }

  const { label, tone } = getStatus(score);

  return {
    record,
    amount,
    estimatedAmount,
    potentialFunding,
    historicalEvidenceCount: historicalEvidence.length,
    matchedKeywords,
    matchScore: clampScore(score),
    statusLabel: label,
    statusTone: tone,
    reasons: unique(reasons).slice(0, 4),
    risks: unique(risks).slice(0, 3),
    nextActions: unique(nextActions).slice(0, 3)
  };
}

export function applyOpportunitySemanticScore<TRecord extends GenericRecord>(
  match: OpportunityBenefitMatch<TRecord>,
  semanticScore: SemanticScore | undefined
): OpportunityBenefitMatch<TRecord> {
  if (!semanticScore) {
    return match;
  }

  const matchScore = clampScore(semanticScore.combined_score);
  const { label, tone } = getStatus(matchScore);

  return {
    ...match,
    matchScore,
    semanticScore: semanticScore.semantic_score,
    ruleScore: semanticScore.rule_score ?? match.matchScore,
    statusLabel: label,
    statusTone: tone,
    reasons: unique([...semanticScore.reasons, ...match.reasons]).slice(0, 4)
  };
}

export function isCurrentlyAvailableOpportunity(record: GenericRecord): boolean {
  const text = genericRecordText(record);
  return !/\b(closed|expired|inactive|archived|not accepting|no longer accepting|application closed)\b/i.test(text);
}

export function sortOpportunityBenefitMatches<TRecord extends GenericRecord>(
  matches: OpportunityBenefitMatch<TRecord>[],
  mode: 'score' | 'amount' | 'newest'
): OpportunityBenefitMatch<TRecord>[] {
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

export function getOpportunityRecordRef(record: GenericRecord): string | null {
  const field = findField(record, idFields);
  const ref = field ? valueToString(field.value).trim() : '';
  return ref && ref !== 'Unavailable' ? `${field?.key}:${ref}` : null;
}

export function getOpportunityBenefitRef(match: OpportunityBenefitMatch): string | null {
  return getOpportunityRecordRef(match.record) ?? `title:${getOpportunityTitle(match)}|${getOpportunitySponsor(match)}`;
}

export function getOpportunityTitle(match: OpportunityBenefitMatch): string {
  return getRecordFieldValue(match.record, titleFields) ?? 'Funding opportunity';
}

export function getOpportunitySponsor(match: OpportunityBenefitMatch): string {
  return getRecordFieldValue(match.record, subtitleFields) ?? 'Program source unavailable';
}

export function getOpportunityDeadlineValue(match: OpportunityBenefitMatch): string | null {
  return getRecordFieldValue(match.record, dateFields);
}

function findHistoricalEvidence(
  benefit: GenericRecord,
  profile: CompanyProfile,
  historicalMatches: OpportunityGrantMatch[],
  keywords: string[],
  matchedBenefitKeywords: string[]
): OpportunityGrantMatch[] {
  const benefitText = genericRecordText(benefit);
  const profileProvince = profile.province.trim().toUpperCase();
  const activeTerms = selectedActivities(profile).flatMap((activity) => activityOptions.find((item) => item.value === activity)?.terms ?? []);
  const comparisonTerms = unique([...matchedBenefitKeywords, ...keywords.slice(0, 8), ...activeTerms]);

  return historicalMatches
    .filter((match) => {
      if (match.matchScore < REVIEW_MATCH_THRESHOLD || match.amount === null) {
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

function addCompanyTypeSignals(
  profile: CompanyProfile,
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

function selectedActivities(profile: CompanyProfile): ActivityKey[] {
  return activityOptions.filter((activity) => profile.activities[activity.value]).map((activity) => activity.value);
}

function grantText(grant: GrantRecordLike): string {
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

function getStatus(score: number): { label: string; tone: MatchTone } {
  const matchScore = clampScore(score);

  if (matchScore >= LIKELY_MATCH_THRESHOLD) {
    return { label: 'Likely match', tone: 'likely' };
  }

  if (matchScore >= REVIEW_MATCH_THRESHOLD) {
    return { label: 'Worth review', tone: 'review' };
  }

  return { label: 'Low confidence', tone: 'low' };
}

function clampScore(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score)));
}

function findField(record: GenericRecord, candidates: string[]): { key: string; value: unknown } | null {
  const normalizedEntries = Object.entries(record).map(([key, value]) => ({
    key,
    normalizedKey: key.toLowerCase(),
    value
  }));

  for (const candidate of candidates) {
    const normalizedCandidate = candidate.toLowerCase();
    const match = normalizedEntries.find((entry) => entry.normalizedKey === normalizedCandidate && valueIsPresent(entry.value));

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

function unique<TValue>(values: TValue[]): TValue[] {
  return [...new Set(values)];
}
