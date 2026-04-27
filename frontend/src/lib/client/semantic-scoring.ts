import {
  LIKELY_MATCH_THRESHOLD,
  REVIEW_MATCH_THRESHOLD,
  type CompanyProfile,
  type GenericRecord,
  type ScoredRecord
} from './company-matching';

export type SemanticSource = 'grants' | 'business-benefits';
export type SemanticScore = {
  record_id: string;
  source: SemanticSource;
  source_id: string;
  semantic_score: number;
  rule_score: number | null;
  combined_score: number;
  similarity: number;
  reasons: string[];
};
export type SemanticScoreMap = Record<string, SemanticScore>;

const SEMANTIC_SCORE_TIMEOUT_MS = 8000;
const MAX_SEMANTIC_RECORDS = 500;
const SEMANTIC_SCORE_CACHE_KEY = 'fundradar.matchPercentages.v1';
const SEMANTIC_SCORE_CACHE_MAX_ENTRIES = 2000;
const SEMANTIC_SCORE_CACHE_TTL_MS = 1000 * 60 * 60 * 24 * 30;
const ID_FIELDS = [
  '_semantic_client_id',
  'ref_number',
  'id',
  '_id',
  'record_id',
  'project_id',
  'application_id',
  'token',
  'reference',
  'url'
];
type CachedSemanticScore = {
  savedAt: number;
  score: SemanticScore;
};
type SemanticScoreCache = Record<string, CachedSemanticScore>;

export async function fetchSemanticScoresForMatches<TRecord extends GenericRecord>(
  backendApiUrl: string,
  profile: CompanyProfile,
  matches: ScoredRecord<TRecord>[],
  source: SemanticSource
): Promise<SemanticScoreMap> {
  const candidates = matches.slice(0, MAX_SEMANTIC_RECORDS);
  if (candidates.length === 0) {
    return {};
  }

  const cachedScores = readCachedSemanticScores(profile, candidates, source);
  const missingEntries = candidates
    .map((match, index) => ({ match, index }))
    .filter(({ match, index }) => cachedScores[getSemanticRecordId(match.record, source, index)] === undefined);

  if (missingEntries.length === 0) {
    return cachedScores;
  }

  const records = missingEntries.map(({ match, index }) => ({
    ...match.record,
    _semantic_client_id: getSemanticRecordSourceId(match.record, index)
  }));
  const ruleScores = Object.fromEntries(
    missingEntries.map(({ match, index }) => [`${source}:${getSemanticRecordSourceId(match.record, index)}`, match.matchScore])
  );

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), SEMANTIC_SCORE_TIMEOUT_MS);

  try {
    const response = await fetch(`${backendApiUrl.replace(/\/$/, '')}/api/search/semantic`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({
        profile,
        records,
        source,
        rule_scores: ruleScores,
        rule_weight: 0.7,
        use_vector_cache: true
      }),
      signal: controller.signal
    });

    if (!response.ok) {
      return {};
    }

    const payload = (await response.json()) as { matches?: SemanticScore[] };
    const semanticScores = Array.isArray(payload.matches) ? payload.matches : [];
    writeCachedSemanticScores(profile, candidates, source, semanticScores);
    return {
      ...cachedScores,
      ...Object.fromEntries(semanticScores.map((score) => [score.record_id, score]))
    };
  } catch {
    return cachedScores;
  } finally {
    window.clearTimeout(timeout);
  }
}

export function readCachedSemanticScores<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  matches: ScoredRecord<TRecord>[],
  source: SemanticSource
): SemanticScoreMap {
  const cache = readSemanticScoreCache();
  const now = Date.now();
  const cachedScores: SemanticScoreMap = {};

  matches.slice(0, MAX_SEMANTIC_RECORDS).forEach((match, index) => {
    const key = buildSemanticScoreCacheKey(profile, match, source, index);
    const cached = cache[key];

    if (!cached || now - cached.savedAt > SEMANTIC_SCORE_CACHE_TTL_MS) {
      return;
    }

    cachedScores[getSemanticRecordId(match.record, source, index)] = cached.score;
  });

  return cachedScores;
}

export function applySemanticScore<TRecord>(
  match: ScoredRecord<TRecord>,
  semanticScore: SemanticScore | undefined
): ScoredRecord<TRecord> {
  if (!semanticScore) {
    return match;
  }

  const matchScore = clampScore(semanticScore.combined_score);
  const status =
    matchScore >= LIKELY_MATCH_THRESHOLD
      ? { label: 'Likely match', tone: 'likely' as const }
      : matchScore >= REVIEW_MATCH_THRESHOLD
        ? { label: 'Worth review', tone: 'review' as const }
        : { label: 'Low confidence', tone: 'low' as const };

  return {
    ...match,
    matchScore,
    statusLabel: status.label,
    statusTone: status.tone,
    semanticScore: semanticScore.semantic_score,
    ruleScore: semanticScore.rule_score ?? match.matchScore,
    reasons: unique([...semanticScore.reasons, ...match.reasons]).slice(0, 4)
  };
}

export function getSemanticRecordId(record: GenericRecord, source: SemanticSource, index: number): string {
  return `${source}:${getSemanticRecordSourceId(record, index)}`;
}

function writeCachedSemanticScores<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  matches: ScoredRecord<TRecord>[],
  source: SemanticSource,
  semanticScores: SemanticScore[]
) {
  if (semanticScores.length === 0) {
    return;
  }

  const cache = readSemanticScoreCache();
  const now = Date.now();
  const matchesByRecordId = new Map(
    matches.slice(0, MAX_SEMANTIC_RECORDS).map((match, index) => [getSemanticRecordId(match.record, source, index), { match, index }])
  );

  for (const score of semanticScores) {
    const matchEntry = matchesByRecordId.get(score.record_id);
    if (!matchEntry) {
      continue;
    }

    cache[buildSemanticScoreCacheKey(profile, matchEntry.match, source, matchEntry.index)] = {
      savedAt: now,
      score
    };
  }

  writeSemanticScoreCache(pruneSemanticScoreCache(cache));
}

function buildSemanticScoreCacheKey<TRecord extends GenericRecord>(
  profile: CompanyProfile,
  match: ScoredRecord<TRecord>,
  source: SemanticSource,
  index: number
): string {
  return [
    source,
    hashString(stableStringify(profileScoreCacheShape(profile))),
    hashString(stableStringify(recordScoreCacheShape(match.record))),
    getSemanticRecordSourceId(match.record, index),
    match.matchScore
  ].join('|');
}

function profileScoreCacheShape(profile: CompanyProfile): Partial<CompanyProfile> {
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

function recordScoreCacheShape(record: GenericRecord): GenericRecord {
  return Object.fromEntries(
    Object.entries(record).filter(([key, value]) => key !== '_semantic_client_id' && value !== undefined)
  );
}

function readSemanticScoreCache(): SemanticScoreCache {
  try {
    const rawValue = localStorage.getItem(SEMANTIC_SCORE_CACHE_KEY);
    const parsed: unknown = rawValue ? JSON.parse(rawValue) : {};

    if (!isRecord(parsed)) {
      return {};
    }

    return parsed as SemanticScoreCache;
  } catch {
    return {};
  }
}

function writeSemanticScoreCache(cache: SemanticScoreCache) {
  try {
    localStorage.setItem(SEMANTIC_SCORE_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

function pruneSemanticScoreCache(cache: SemanticScoreCache): SemanticScoreCache {
  const now = Date.now();
  const entries = Object.entries(cache)
    .filter(([, value]) => now - value.savedAt <= SEMANTIC_SCORE_CACHE_TTL_MS)
    .sort(([, left], [, right]) => right.savedAt - left.savedAt)
    .slice(0, SEMANTIC_SCORE_CACHE_MAX_ENTRIES);

  return Object.fromEntries(entries);
}

function getSemanticRecordSourceId(record: GenericRecord, index: number): string {
  for (const field of ID_FIELDS) {
    const value = record[field];
    if (value !== null && value !== undefined && String(value).trim()) {
      return `${field}:${String(value).trim()}`;
    }
  }

  return `index:${index}`;
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
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

function unique(values: string[]): string[] {
  return [...new Set(values)];
}
