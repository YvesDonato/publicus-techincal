import type { CompanyProfile, GenericRecord } from './company-matching';
import {
  getOpportunityBenefitRef,
  getOpportunityDeadlineValue,
  getOpportunitySponsor,
  getOpportunityTitle,
  type OpportunityBenefitMatch
} from './opportunity-matches';

export type OpportunityAnalysis = {
  fit: OpportunityFit;
  should_show: boolean;
  fit_summary: string;
  eligibility_flags: string[];
  missing_company_info: string[];
  application_steps: string[];
  risk_notes: string[];
  questions_to_answer: string[];
  confidence: 'low' | 'medium' | 'high';
  provider: string;
};

export type OpportunityFit = 'strong' | 'possible' | 'weak';
export type OpportunityFitJudgment = {
  record_ref: string;
  fit: OpportunityFit;
  should_show: boolean;
  confidence: 'low' | 'medium' | 'high';
  reason: string;
  risk_notes: string[];
};
export type OpportunityFitJudgmentResult = {
  judgments: Record<string, OpportunityFitJudgment>;
  provider: string;
  filter_available: boolean;
  unavailable_reason: string | null;
};

type FetchOpportunityAnalysisOptions<TRecord extends GenericRecord> = {
  backendApiUrl: string;
  profile: CompanyProfile;
  match: OpportunityBenefitMatch<TRecord>;
  description: string;
  fitJudgment?: OpportunityFitJudgment | null;
  timeout?: number;
  forceRefresh?: boolean;
};

type FetchOpportunityFitJudgmentsOptions<TRecord extends GenericRecord> = {
  backendApiUrl: string;
  profile: CompanyProfile;
  matches: OpportunityBenefitMatch<TRecord>[];
  descriptions: Record<string, string>;
  timeout?: number;
};

type CachedOpportunityAnalysis = {
  savedAt: number;
  analysis: OpportunityAnalysis;
};

type OpportunityAnalysisCache = Record<string, CachedOpportunityAnalysis>;
type CachedOpportunityFitJudgment = {
  savedAt: number;
  judgment: OpportunityFitJudgment;
};
type OpportunityFitJudgmentCache = Record<string, CachedOpportunityFitJudgment>;

const OPPORTUNITY_ANALYSIS_CACHE_KEY = 'fundradar.opportunityAnalysis.v2';
const OPPORTUNITY_ANALYSIS_CACHE_TTL_MS = 1000 * 60 * 60 * 24 * 30;
const OPPORTUNITY_ANALYSIS_CACHE_MAX_ENTRIES = 250;
const OPPORTUNITY_FIT_JUDGMENT_CACHE_KEY = 'fundradar.opportunityFitJudgments.v1';
const OPPORTUNITY_FIT_JUDGMENT_CACHE_TTL_MS = 1000 * 60 * 60 * 24 * 14;
const OPPORTUNITY_FIT_JUDGMENT_CACHE_MAX_ENTRIES = 500;

export async function fetchOpportunityAnalysis<TRecord extends GenericRecord>({
  backendApiUrl,
  profile,
  match,
  description,
  fitJudgment = null,
  timeout = 30,
  forceRefresh = false
}: FetchOpportunityAnalysisOptions<TRecord>): Promise<OpportunityAnalysis> {
  const cacheKey = buildOpportunityAnalysisCacheKey(profile, match, description, fitJudgment);

  if (!forceRefresh) {
    const cached = readCachedOpportunityAnalysis(cacheKey);
    if (cached) {
      return cached;
    }
  }

  const response = await fetch(`${backendApiUrl.replace(/\/$/, '')}/api/opportunities/analyze`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      profile,
      opportunity: match.record,
      match: buildOpportunityMatchPayload(match, description),
      fit_judgment: fitJudgment,
      timeout
    })
  });

  if (!response.ok) {
    throw new Error((await readApiError(response)) ?? 'Could not analyze this opportunity.');
  }

  const analysis = normalizeOpportunityAnalysis(await response.json());
  writeCachedOpportunityAnalysis(cacheKey, analysis);
  return analysis;
}

export function getOpportunityAnalysisCacheKey<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  match: OpportunityBenefitMatch<TRecord>,
  description: string,
  fitJudgment: OpportunityFitJudgment | null = null
): string {
  return buildOpportunityAnalysisCacheKey(profile, match, description, fitJudgment);
}

export function getOpportunityFitJudgmentCacheKey<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  match: OpportunityBenefitMatch<TRecord>,
  description: string
): string {
  return buildOpportunityFitJudgmentCacheKey(profile, match, description);
}

export async function fetchOpportunityFitJudgments<TRecord extends GenericRecord>({
  backendApiUrl,
  profile,
  matches,
  descriptions,
  timeout = 30
}: FetchOpportunityFitJudgmentsOptions<TRecord>): Promise<OpportunityFitJudgmentResult> {
  if (matches.length === 0) {
    return {
      judgments: {},
      provider: 'none',
      filter_available: false,
      unavailable_reason: null
    };
  }

  const entries = matches.map((match, index) => {
    const recordRef = getOpportunityRecordRef(match);
    const description = descriptions[recordRef] ?? getOpportunityTitle(match);
    return {
      match,
      recordRef,
      description,
      cacheKey: buildOpportunityFitJudgmentCacheKey(profile, match, description),
      requestRef: `candidate-${index + 1}`
    };
  });
  const cachedJudgments = readCachedOpportunityFitJudgments(entries.map((entry) => entry.cacheKey));
  const missingEntries = entries.filter((entry) => cachedJudgments[entry.cacheKey] === undefined);

  if (missingEntries.length === 0) {
    return {
      judgments: cachedJudgments,
      provider: 'cache',
      filter_available: true,
      unavailable_reason: null
    };
  }

  const response = await fetch(`${backendApiUrl.replace(/\/$/, '')}/api/opportunities/judge-fit`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      profile,
      opportunities: missingEntries.map((entry) => ({
        record_ref: entry.requestRef,
        opportunity: entry.match.record,
        match: buildOpportunityMatchPayload(entry.match, entry.description)
      })),
      timeout
    })
  });

  if (!response.ok) {
    throw new Error((await readApiError(response)) ?? 'Could not run the LLM fit filter.');
  }

  const payload = normalizeOpportunityFitJudgmentResponse(await response.json());
  const missingByRef = new Map(missingEntries.map((entry) => [entry.requestRef, entry]));
  const newJudgments: Record<string, OpportunityFitJudgment> = {};

  for (const judgment of payload.judgments) {
    const entry = missingByRef.get(judgment.record_ref);
    if (!entry) {
      continue;
    }

    newJudgments[entry.cacheKey] = {
      ...judgment,
      record_ref: entry.recordRef
    };
  }

  if (payload.filter_available) {
    writeCachedOpportunityFitJudgments(newJudgments);
  }

  return {
    judgments: {
      ...cachedJudgments,
      ...newJudgments
    },
    provider: payload.provider,
    filter_available: payload.filter_available || Object.keys(cachedJudgments).length > 0,
    unavailable_reason: payload.unavailable_reason
  };
}

function readCachedOpportunityAnalysis(cacheKey: string): OpportunityAnalysis | null {
  const cache = readOpportunityAnalysisCache();
  const cached = cache[cacheKey];

  if (!cached || Date.now() - cached.savedAt > OPPORTUNITY_ANALYSIS_CACHE_TTL_MS) {
    return null;
  }

  return cached.analysis;
}

function writeCachedOpportunityAnalysis(cacheKey: string, analysis: OpportunityAnalysis) {
  const cache = readOpportunityAnalysisCache();
  cache[cacheKey] = {
    savedAt: Date.now(),
    analysis
  };

  writeOpportunityAnalysisCache(pruneOpportunityAnalysisCache(cache));
}

function readCachedOpportunityFitJudgments(cacheKeys: string[]): Record<string, OpportunityFitJudgment> {
  const cache = readOpportunityFitJudgmentCache();
  const now = Date.now();
  const output: Record<string, OpportunityFitJudgment> = {};

  for (const cacheKey of cacheKeys) {
    const cached = cache[cacheKey];
    if (!cached || now - cached.savedAt > OPPORTUNITY_FIT_JUDGMENT_CACHE_TTL_MS) {
      continue;
    }

    output[cacheKey] = cached.judgment;
  }

  return output;
}

function writeCachedOpportunityFitJudgments(judgments: Record<string, OpportunityFitJudgment>) {
  if (Object.keys(judgments).length === 0) {
    return;
  }

  const cache = readOpportunityFitJudgmentCache();
  const now = Date.now();

  for (const [cacheKey, judgment] of Object.entries(judgments)) {
    cache[cacheKey] = {
      savedAt: now,
      judgment
    };
  }

  writeOpportunityFitJudgmentCache(pruneOpportunityFitJudgmentCache(cache));
}

function buildOpportunityAnalysisCacheKey<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  match: OpportunityBenefitMatch<TRecord>,
  description: string,
  fitJudgment: OpportunityFitJudgment | null = null
): string {
  return [
    'business-benefits',
    getOpportunityRecordRef(match),
    hashString(stableStringify(profileAnalysisCacheShape(profile))),
    hashString(stableStringify(recordAnalysisCacheShape(match.record))),
    hashString(description),
    match.matchScore,
    match.potentialFunding ?? 'none',
    hashString(stableStringify(fitJudgmentAnalysisCacheShape(fitJudgment)))
  ].join('|');
}

function buildOpportunityFitJudgmentCacheKey<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  match: OpportunityBenefitMatch<TRecord>,
  description: string
): string {
  return [
    'fit',
    'business-benefits',
    getOpportunityRecordRef(match),
    hashString(stableStringify(profileAnalysisCacheShape(profile))),
    hashString(stableStringify(recordAnalysisCacheShape(match.record))),
    hashString(description),
    match.matchScore,
    match.potentialFunding ?? 'none'
  ].join('|');
}

function getOpportunityRecordRef<TRecord extends GenericRecord>(match: OpportunityBenefitMatch<TRecord>): string {
  return getOpportunityBenefitRef(match) ?? hashString(stableStringify(recordAnalysisCacheShape(match.record)));
}

function buildOpportunityMatchPayload<TRecord extends GenericRecord>(match: OpportunityBenefitMatch<TRecord>, description: string) {
  return {
    source: 'business-benefits',
    title: getOpportunityTitle(match),
    sponsor: getOpportunitySponsor(match),
    description,
    deadline: getOpportunityDeadlineValue(match),
    status_label: match.statusLabel,
    match_score: match.matchScore,
    semantic_score: match.semanticScore ?? null,
    rule_score: match.ruleScore ?? null,
    potential_funding: match.potentialFunding,
    reasons: match.reasons,
    risks: match.risks,
    next_actions: match.nextActions
  };
}

function profileAnalysisCacheShape(profile: CompanyProfile): Partial<CompanyProfile> {
  return {
    legalEntityName: profile.legalEntityName,
    doingBusinessAs: profile.doingBusinessAs,
    province: profile.province,
    city: profile.city,
    companyType: profile.companyType,
    employeeRange: profile.employeeRange,
    industry: profile.industry,
    subSector: profile.subSector,
    keywords: profile.keywords,
    fundingNeed: profile.fundingNeed,
    activities: profile.activities
  };
}

function fitJudgmentAnalysisCacheShape(fitJudgment: OpportunityFitJudgment | null): Record<string, unknown> {
  if (!fitJudgment) {
    return { fit: 'unjudged' };
  }

  return {
    fit: fitJudgment.fit,
    should_show: fitJudgment.should_show,
    confidence: fitJudgment.confidence,
    reason: fitJudgment.reason,
    risk_notes: fitJudgment.risk_notes
  };
}

function recordAnalysisCacheShape(record: GenericRecord): GenericRecord {
  return Object.fromEntries(Object.entries(record).filter(([, value]) => value !== undefined));
}

function normalizeOpportunityAnalysis(value: unknown): OpportunityAnalysis {
  const payload = isRecord(value) ? value : {};
  return {
    fit: readFit(payload.fit),
    should_show: payload.should_show !== false,
    fit_summary: readString(payload.fit_summary, 'Review this opportunity against the company profile.'),
    eligibility_flags: readStringList(payload.eligibility_flags),
    missing_company_info: readStringList(payload.missing_company_info),
    application_steps: readStringList(payload.application_steps),
    risk_notes: readStringList(payload.risk_notes),
    questions_to_answer: readStringList(payload.questions_to_answer),
    confidence: readConfidence(payload.confidence),
    provider: readString(payload.provider, 'google')
  };
}

function normalizeOpportunityFitJudgmentResponse(value: unknown): {
  judgments: OpportunityFitJudgment[];
  provider: string;
  filter_available: boolean;
  unavailable_reason: string | null;
} {
  const payload = isRecord(value) ? value : {};
  const rawJudgments = Array.isArray(payload.judgments) ? payload.judgments : [];

  return {
    judgments: rawJudgments.map(normalizeOpportunityFitJudgment).filter((item): item is OpportunityFitJudgment => item !== null),
    provider: readString(payload.provider, 'google'),
    filter_available: payload.filter_available === true,
    unavailable_reason: typeof payload.unavailable_reason === 'string' ? payload.unavailable_reason : null
  };
}

function normalizeOpportunityFitJudgment(value: unknown): OpportunityFitJudgment | null {
  if (!isRecord(value)) {
    return null;
  }

  const recordRef = readString(value.record_ref, '');
  if (!recordRef) {
    return null;
  }

  return {
    record_ref: recordRef,
    fit: readFit(value.fit),
    should_show: value.should_show !== false,
    confidence: readConfidence(value.confidence),
    reason: readString(value.reason, 'Review this opportunity against the company profile.'),
    risk_notes: readStringList(value.risk_notes)
  };
}

function readFit(value: unknown): OpportunityFit {
  return value === 'strong' || value === 'possible' || value === 'weak' ? value : 'possible';
}

function readString(value: unknown, fallback: string): string {
  const text = typeof value === 'string' ? value.trim() : '';
  return text || fallback;
}

function readStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0).map((item) => item.trim())
    : [];
}

function readConfidence(value: unknown): OpportunityAnalysis['confidence'] {
  return value === 'high' || value === 'medium' || value === 'low' ? value : 'medium';
}

async function readApiError(response: Response): Promise<string | null> {
  try {
    const payload: unknown = await response.json();
    if (!isRecord(payload)) {
      return null;
    }

    if (typeof payload.detail === 'string') {
      return payload.detail;
    }

    return null;
  } catch {
    return null;
  }
}

function readOpportunityAnalysisCache(): OpportunityAnalysisCache {
  try {
    const rawValue = localStorage.getItem(OPPORTUNITY_ANALYSIS_CACHE_KEY);
    const parsed: unknown = rawValue ? JSON.parse(rawValue) : {};
    return isRecord(parsed) ? (parsed as OpportunityAnalysisCache) : {};
  } catch {
    return {};
  }
}

function writeOpportunityAnalysisCache(cache: OpportunityAnalysisCache) {
  try {
    localStorage.setItem(OPPORTUNITY_ANALYSIS_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

function readOpportunityFitJudgmentCache(): OpportunityFitJudgmentCache {
  try {
    const rawValue = localStorage.getItem(OPPORTUNITY_FIT_JUDGMENT_CACHE_KEY);
    const parsed: unknown = rawValue ? JSON.parse(rawValue) : {};
    return isRecord(parsed) ? (parsed as OpportunityFitJudgmentCache) : {};
  } catch {
    return {};
  }
}

function writeOpportunityFitJudgmentCache(cache: OpportunityFitJudgmentCache) {
  try {
    localStorage.setItem(OPPORTUNITY_FIT_JUDGMENT_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

function pruneOpportunityAnalysisCache(cache: OpportunityAnalysisCache): OpportunityAnalysisCache {
  const now = Date.now();
  const entries = Object.entries(cache)
    .filter(([, value]) => now - value.savedAt <= OPPORTUNITY_ANALYSIS_CACHE_TTL_MS)
    .sort(([, left], [, right]) => right.savedAt - left.savedAt)
    .slice(0, OPPORTUNITY_ANALYSIS_CACHE_MAX_ENTRIES);

  return Object.fromEntries(entries);
}

function pruneOpportunityFitJudgmentCache(cache: OpportunityFitJudgmentCache): OpportunityFitJudgmentCache {
  const now = Date.now();
  const entries = Object.entries(cache)
    .filter(([, value]) => now - value.savedAt <= OPPORTUNITY_FIT_JUDGMENT_CACHE_TTL_MS)
    .sort(([, left], [, right]) => right.savedAt - left.savedAt)
    .slice(0, OPPORTUNITY_FIT_JUDGMENT_CACHE_MAX_ENTRIES);

  return Object.fromEntries(entries);
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }

  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(',')}}`;
  }

  return JSON.stringify(value);
}

function hashString(value: string): string {
  let hash = 2166136261;

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return (hash >>> 0).toString(36);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
