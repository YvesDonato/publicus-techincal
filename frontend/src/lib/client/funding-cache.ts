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

export type HydrationProgress = {
  loaded: number;
  target: number;
  fromCache: boolean;
  done: boolean;
};

export type ProgressiveHydrationOptions = {
  batchSize?: number;
  onProgress?: (progress: HydrationProgress) => void;
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

function readAnyCache<TResult extends { records: GenericRecord[] }>(key: string): TResult | null {
  try {
    const rawValue = localStorage.getItem(key);
    const parsed = rawValue ? (JSON.parse(rawValue) as CacheEnvelope<TResult>) : null;

    if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.result.records)) {
      return null;
    }

    return parsed.result;
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

function reportProgress(options: ProgressiveHydrationOptions | undefined, progress: HydrationProgress) {
  options?.onProgress?.(progress);
}

function clampCount(value: number): number {
  return Math.max(1, Math.min(5000, Math.floor(value)));
}

function updateGrantsEndpoint(endpoint: string, limit: number, offset: number): string {
  try {
    const url = new URL(endpoint);
    url.searchParams.set('limit', String(limit));
    url.searchParams.set('offset', String(offset));
    url.searchParams.set('include_total', 'true');
    return url.toString();
  } catch {
    return endpoint;
  }
}

function updateBenefitsEndpoint(endpoint: string, count: number): string {
  try {
    const url = new URL(endpoint);
    const segments = url.pathname.split('/');
    const firstIndex = segments.lastIndexOf('first');

    if (firstIndex >= 0 && firstIndex + 1 < segments.length) {
      segments[firstIndex + 1] = String(count);
      url.pathname = segments.join('/');
    } else {
      url.searchParams.set('limit', String(count));
    }

    return url.toString();
  } catch {
    return endpoint;
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

function compactGrantRecord(record: GenericRecord): GenericRecord {
  return {
    _id: record._id,
    ref_number: record.ref_number,
    recipient_legal_name: record.recipient_legal_name,
    agreement_value: record.agreement_value,
    agreement_start_date: record.agreement_start_date,
    agreement_end_date: record.agreement_end_date,
    agreement_title_en: record.agreement_title_en,
    description_en: record.description_en,
    expected_results_en: record.expected_results_en,
    prog_name_en: record.prog_name_en,
    prog_purpose_en: record.prog_purpose_en,
    owner_org_title: record.owner_org_title,
    recipient_city: record.recipient_city,
    recipient_province: record.recipient_province
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
        error: 'Funding records are temporarily unavailable.'
      };
    }

    const payload = (await response.json()) as GrantsApiResponse;
    const records = Array.isArray(payload.records) ? payload.records.map(compactGrantRecord) : [];
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
    return {
      requested,
      count: 0,
      records: [],
      total: null,
      endpoint,
      error: 'Funding records are temporarily unavailable. Try again in a moment.'
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
        error: 'Business benefit records are temporarily unavailable.'
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
    return {
      requested,
      count: 0,
      records: [],
      source: null,
      endpoint,
      error: 'Business benefit records are temporarily unavailable. Try again in a moment.'
    };
  }
}

async function fetchGrantsPage(endpoint: string, requested: number): Promise<CachedGrantsResult> {
  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return {
        requested,
        count: 0,
        records: [],
        total: null,
        endpoint,
        error: 'Funding records are temporarily unavailable.'
      };
    }

    const payload = (await response.json()) as GrantsApiResponse;
    const records = Array.isArray(payload.records) ? payload.records.map(compactGrantRecord) : [];

    return {
      requested: payload.requested ?? payload.limit ?? requested,
      count: records.length,
      records,
      total: payload.total ?? null,
      endpoint,
      error: null
    };
  } catch {
    return {
      requested,
      count: 0,
      records: [],
      total: null,
      endpoint,
      error: 'Funding records are temporarily unavailable. Try again in a moment.'
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

export function readCachedGrantsResult(endpoint: string, requested: number): CachedGrantsResult | null {
  const cached = readCache<CachedGrantsResult>(GRANTS_CACHE_KEY, requested);
  return cached ? sliceGrantsResult(cached, requested, endpoint) : null;
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

export async function hydrateProgressiveCachedGrantsResult(
  endpoint: string,
  requested: number,
  options: ProgressiveHydrationOptions = {}
): Promise<CachedGrantsResult> {
  const target = clampCount(requested);
  const batchSize = clampCount(options.batchSize ?? 500);
  const finalEndpoint = updateGrantsEndpoint(endpoint, target, 0);
  const cached = readCache<CachedGrantsResult>(GRANTS_CACHE_KEY, target);

  if (cached) {
    const result = sliceGrantsResult(cached, target, finalEndpoint);
    reportProgress(options, { loaded: result.records.length, target, fromCache: true, done: true });
    return result;
  }

  const partialCache = readAnyCache<CachedGrantsResult>(GRANTS_CACHE_KEY);
  const records = partialCache?.records.slice(0, target) ?? [];
  let total = partialCache?.total ?? null;

  if (records.length > 0) {
    reportProgress(options, { loaded: records.length, target, fromCache: true, done: false });
  } else {
    reportProgress(options, { loaded: 0, target, fromCache: false, done: false });
  }

  while (records.length < target) {
    const pageLimit = Math.min(batchSize, target - records.length);
    const pageEndpoint = updateGrantsEndpoint(endpoint, pageLimit, records.length);
    const page = await fetchGrantsPage(pageEndpoint, pageLimit);

    if (page.error) {
      if (records.length > 0) {
        const partialResult = {
          requested: target,
          count: records.length,
          records,
          total,
          endpoint: finalEndpoint,
          error: null
        };
        writeCache(GRANTS_CACHE_KEY, partialResult);
        reportProgress(options, { loaded: records.length, target, fromCache: true, done: true });
        return partialResult;
      }

      reportProgress(options, { loaded: 0, target, fromCache: false, done: true });
      return {
        requested: target,
        count: 0,
        records: [],
        total: null,
        endpoint: finalEndpoint,
        error: page.error
      };
    }

    if (page.records.length === 0) {
      break;
    }

    records.push(...page.records);
    total = page.total ?? total;

    const merged = {
      requested: target,
      count: records.length,
      records,
      total,
      endpoint: finalEndpoint,
      error: null
    };

    writeCache(GRANTS_CACHE_KEY, merged);
    reportProgress(options, { loaded: records.length, target, fromCache: false, done: false });

    if (page.records.length < pageLimit || (total !== null && records.length >= total)) {
      break;
    }
  }

  const result = {
    requested: target,
    count: records.length,
    records,
    total,
    endpoint: finalEndpoint,
    error: null
  };
  writeCache(GRANTS_CACHE_KEY, result);
  reportProgress(options, { loaded: records.length, target, fromCache: false, done: true });
  return result;
}

export async function hydrateProgressiveCachedBenefitsResult(
  endpoint: string,
  requested: number,
  options: ProgressiveHydrationOptions = {}
): Promise<CachedBenefitsResult> {
  const target = clampCount(requested);
  const finalEndpoint = updateBenefitsEndpoint(endpoint, target);
  const cached = readCache<CachedBenefitsResult>(BENEFITS_CACHE_KEY, target);

  if (cached) {
    const result = sliceBenefitsResult(cached, target, finalEndpoint);
    reportProgress(options, { loaded: result.records.length, target, fromCache: true, done: true });
    return result;
  }

  const partialCache = readAnyCache<CachedBenefitsResult>(BENEFITS_CACHE_KEY);
  if (partialCache?.records.length) {
    reportProgress(options, {
      loaded: Math.min(partialCache.records.length, target),
      target,
      fromCache: true,
      done: false
    });
  } else {
    reportProgress(options, { loaded: 0, target, fromCache: false, done: false });
  }

  const result = await fetchBenefitsResult(finalEndpoint, target);
  if (result.error && partialCache?.records.length) {
    const partialResult = sliceBenefitsResult(partialCache, Math.min(partialCache.records.length, target), finalEndpoint);
    reportProgress(options, { loaded: partialResult.records.length, target, fromCache: true, done: true });
    return partialResult;
  }

  reportProgress(options, { loaded: result.records.length, target, fromCache: false, done: true });
  return result;
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
