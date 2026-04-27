import { env } from '$env/dynamic/private';
import type { GrantRecord } from './dashboard-data';

export type GenericRecord = Record<string, unknown>;

type GrantsResponse = {
  count?: number;
  limit?: number;
  requested?: number;
  total?: number;
  records?: GrantRecord[];
};

type BusinessBenefitsResponse = {
  requested?: number;
  count?: number;
  records?: GenericRecord[];
  source?: string;
};

type DatasetResult<T> = {
  requested: number;
  count: number;
  records: T[];
  endpoint: string;
  error: string | null;
};

type GrantsResult = DatasetResult<GrantRecord> & {
  total: number | null;
};

type BenefitsResult = DatasetResult<GenericRecord> & {
  source: string | null;
};

const DEFAULT_BACKEND_API_URL = '';
const DEFAULT_COUNT = 100;
const COUNT_INCREMENT = 100;
const MAX_COUNT = 5000;

function parseBoundedInteger(value: string | null, fallback: number, minimum: number, maximum: number): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    return fallback;
  }

  return Math.min(maximum, Math.max(minimum, parsed));
}

function parseLiveViewFilters(url: URL) {
  const legacyCount = url.searchParams.get('count');

  return {
    grantsCount: parseBoundedInteger(
      url.searchParams.get('grantsCount') ?? legacyCount,
      DEFAULT_COUNT,
      1,
      MAX_COUNT
    ),
    benefitsCount: parseBoundedInteger(
      url.searchParams.get('benefitsCount') ?? legacyCount,
      DEFAULT_COUNT,
      1,
      MAX_COUNT
    )
  };
}

function buildGrantsResult(backendApiUrl: string, count: number): GrantsResult {
  const params = new URLSearchParams({
    limit: String(count),
    offset: '0',
    include_total: 'true'
  });
  const endpoint = `${backendApiUrl}/api/grants?${params.toString()}`;

  return {
    requested: count,
    count: 0,
    records: [],
    total: null,
    endpoint,
    error: null
  };
}

function buildBusinessBenefitsResult(backendApiUrl: string, count: number): BenefitsResult {
  const endpoint = `${backendApiUrl}/api/business-benefits/first/${count}`;

  return {
    requested: count,
    count: 0,
    records: [],
    source: null,
    endpoint,
    error: null
  };
}

export function loadGrantsContributionsData(_fetch: typeof globalThis.fetch, url: URL) {
  const backendApiUrl = (env.PUBLIC_BACKEND_API_URL ?? DEFAULT_BACKEND_API_URL).replace(/\/$/, '');
  const grantsCount = parseBoundedInteger(
    url.searchParams.get('count') ?? url.searchParams.get('grantsCount'),
    DEFAULT_COUNT,
    1,
    MAX_COUNT
  );
  const grantsResult = buildGrantsResult(backendApiUrl, grantsCount);

  return {
    filters: {
      grantsCount
    },
    limits: {
      increment: COUNT_INCREMENT,
      maxCount: MAX_COUNT
    },
    grants: grantsResult.records,
    grantsResult
  };
}

export function loadBusinessBenefitsFinderData(_fetch: typeof globalThis.fetch, url: URL) {
  const backendApiUrl = (env.PUBLIC_BACKEND_API_URL ?? DEFAULT_BACKEND_API_URL).replace(/\/$/, '');
  const benefitsCount = parseBoundedInteger(
    url.searchParams.get('count') ?? url.searchParams.get('benefitsCount'),
    DEFAULT_COUNT,
    1,
    MAX_COUNT
  );
  const benefits = buildBusinessBenefitsResult(backendApiUrl, benefitsCount);

  return {
    filters: {
      benefitsCount
    },
    limits: {
      increment: COUNT_INCREMENT,
      maxCount: MAX_COUNT
    },
    benefits
  };
}

export function loadLiveViewData(_fetch: typeof globalThis.fetch, url: URL) {
  const backendApiUrl = (env.PUBLIC_BACKEND_API_URL ?? DEFAULT_BACKEND_API_URL).replace(/\/$/, '');
  const filters = parseLiveViewFilters(url);
  const grantsResult = buildGrantsResult(backendApiUrl, filters.grantsCount);
  const benefits = buildBusinessBenefitsResult(backendApiUrl, filters.benefitsCount);

  return {
    filters,
    limits: {
      increment: COUNT_INCREMENT,
      maxCount: MAX_COUNT
    },
    grants: grantsResult.records,
    grantsResult,
    benefits
  };
}
