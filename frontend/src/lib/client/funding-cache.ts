type GenericRecord = Record<string, unknown>;

export type CachedDatasetResult<TRecord extends GenericRecord> = {
  requested: number;
  count: number;
  records: TRecord[];
  endpoint: string;
  error: string | null;
};

export type CachedGrantsResult<TRecord extends GenericRecord = GenericRecord> = CachedDatasetResult<TRecord> & {
  total: number | null;
};

export type CachedBenefitsResult = CachedDatasetResult<GenericRecord> & {
  source: string | null;
};

export type CachedFundingData = {
  filters: {
    grantsCount: number;
    benefitsCount: number;
  };
  limits: {
    increment: number;
    maxCount: number;
  };
  grants: GenericRecord[];
  grantsResult: CachedGrantsResult;
  benefits: CachedBenefitsResult;
};

type GrantsApiResponse = {
  count?: number;
  limit?: number;
  requested?: number;
  total?: number;
  records?: GenericRecord[];
};

type BenefitsApiResponse = {
  requested?: number;
  count?: number;
  records?: GenericRecord[];
  source?: string;
};

type CacheEnvelope<TResult> = {
  version: 1;
  savedAt: number;
  result: TResult;
};

const GRANTS_CACHE_KEY = 'fundradar.cache.grants.v1';
const BENEFITS_CACHE_KEY = 'fundradar.cache.businessBenefits.v1';

function readCache<TResult extends { records: GenericRecord[] }>(key: string, requested: number): TResult | null {
  try {
    const rawValue = localStorage.getItem(key);
    const parsed = rawValue ? (JSON.parse(rawValue) as CacheEnvelope<TResult>) : null;

    if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.result.records)) {
      return null;
    }

    return parsed.result.records.length >= requested ? parsed.result : null;
  } catch {
    return null;
  }
}

function writeCache<TResult extends { records: GenericRecord[] }>(key: string, result: TResult) {
  try {
    localStorage.setItem(
      key,
      JSON.stringify({
        version: 1,
        savedAt: Date.now(),
        result
      } satisfies CacheEnvelope<TResult>)
    );
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

function sliceGrantsResult(result: CachedGrantsResult, requested: number, endpoint: string): CachedGrantsResult {
  const records = result.records.slice(0, requested);
  return {
    ...result,
    requested,
    count: records.length,
    records,
    endpoint,
    error: null
  };
}

function sliceBenefitsResult(result: CachedBenefitsResult, requested: number, endpoint: string): CachedBenefitsResult {
  const records = result.records.slice(0, requested);
  return {
    ...result,
    requested,
    count: records.length,
    records,
    endpoint,
    error: null
  };
}

async function fetchGrantsResult(endpoint: string, requested: number): Promise<CachedGrantsResult> {
  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return {
        requested,
        count: 0,
        records: [],
        total: null,
        endpoint,
        error: `Backend returned HTTP ${response.status}.`
      };
    }

    const payload = (await response.json()) as GrantsApiResponse;
    const records = Array.isArray(payload.records) ? payload.records : [];
    const result = {
      requested: payload.requested ?? payload.limit ?? requested,
      count: payload.count ?? records.length,
      records,
      total: payload.total ?? null,
      endpoint,
      error: null
    };

    writeCache(GRANTS_CACHE_KEY, result);
    return sliceGrantsResult(result, requested, endpoint);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown backend error.';
    return {
      requested,
      count: 0,
      records: [],
      total: null,
      endpoint,
      error: `Could not reach the backend at ${endpoint}: ${message}`
    };
  }
}

async function fetchBenefitsResult(endpoint: string, requested: number): Promise<CachedBenefitsResult> {
  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return {
        requested,
        count: 0,
        records: [],
        source: null,
        endpoint,
        error: `Backend returned HTTP ${response.status}.`
      };
    }

    const payload = (await response.json()) as BenefitsApiResponse;
    const records = Array.isArray(payload.records) ? payload.records : [];
    const result = {
      requested: payload.requested ?? requested,
      count: payload.count ?? records.length,
      records,
      source: payload.source ?? null,
      endpoint,
      error: null
    };

    writeCache(BENEFITS_CACHE_KEY, result);
    return sliceBenefitsResult(result, requested, endpoint);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown backend error.';
    return {
      requested,
      count: 0,
      records: [],
      source: null,
      endpoint,
      error: `Could not reach the backend at ${endpoint}: ${message}`
    };
  }
}

export async function hydrateCachedGrantsResult(
  endpoint: string,
  requested: number
): Promise<CachedGrantsResult> {
  const cached = readCache<CachedGrantsResult>(GRANTS_CACHE_KEY, requested);

  if (cached) {
    return sliceGrantsResult(cached, requested, endpoint);
  }

  return fetchGrantsResult(endpoint, requested);
}

export async function hydrateCachedBenefitsResult(
  endpoint: string,
  requested: number
): Promise<CachedBenefitsResult> {
  const cached = readCache<CachedBenefitsResult>(BENEFITS_CACHE_KEY, requested);

  if (cached) {
    return sliceBenefitsResult(cached, requested, endpoint);
  }

  return fetchBenefitsResult(endpoint, requested);
}

export async function hydrateCachedFundingData<TData extends CachedFundingData>(data: TData): Promise<TData> {
  const [grantsResult, benefits] = await Promise.all([
    hydrateCachedGrantsResult(data.grantsResult.endpoint, data.filters.grantsCount),
    hydrateCachedBenefitsResult(data.benefits.endpoint, data.filters.benefitsCount)
  ]);

  return {
    ...data,
    grants: grantsResult.records,
    grantsResult,
    benefits
  };
}

