import { env } from '$env/dynamic/private';

export type GrantRecord = {
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

type FirstGrantsResponse = {
  count?: number;
  limit?: number;
  requested?: number;
  total?: number;
  records?: GrantRecord[];
};

type GenericRecord = Record<string, unknown>;

type FirstInnovationResponse = {
  requested?: number;
  count?: number;
  records?: GenericRecord[];
  source?: string;
};

export type DataSource = 'grants' | 'innovation';
export type SortMode = 'score' | 'amount' | 'newest';
type GrantQueryMode = 'first' | 'calendar-year';
type GrantSortOrder = 'asc' | 'desc';

export type DatasetFilters = {
  source: DataSource;
  year: number | null;
  count: number;
  sort: SortMode;
};

type GrantQuery = {
  mode: GrantQueryMode;
  count: number;
  year: number | null;
  order: GrantSortOrder;
  endpoint: string;
};

const DEFAULT_BACKEND_API_URL = '';
const DEFAULT_COUNT = 10;
const MAX_COUNT = 100;

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

function parseCalendarYear(value: string | null): number | null {
  if (!value) {
    return null;
  }

  const year = Number(value);
  if (!Number.isInteger(year) || year < 1800 || year > 2200) {
    return null;
  }

  return year;
}

function parseSource(value: string | null): DataSource {
  if (value === 'innovation' || value === 'business' || value === 'business-benefits') {
    return 'innovation';
  }

  return 'grants';
}

function parseSort(value: string | null): SortMode {
  if (value === 'amount' || value === 'newest') {
    return value;
  }

  return 'score';
}

function parseFilters(url: URL): DatasetFilters {
  const source = parseSource(url.searchParams.get('source'));

  return {
    source,
    year: source === 'grants' ? parseCalendarYear(url.searchParams.get('year')) : null,
    count: parseBoundedInteger(url.searchParams.get('count'), DEFAULT_COUNT, 1, MAX_COUNT),
    sort: parseSort(url.searchParams.get('sort'))
  };
}

function buildGrantQuery(filters: DatasetFilters, backendApiUrl: string): GrantQuery {
  const order: GrantSortOrder = filters.sort === 'newest' ? 'desc' : 'asc';
  const params = new URLSearchParams({
    limit: String(filters.count),
    include_total: filters.year === null && filters.sort === 'score' ? 'true' : 'false'
  });

  if (filters.year !== null) {
    params.set('year', String(filters.year));
  }

  if (filters.sort !== 'score') {
    params.set('sort', filters.sort);
  }

  return {
    mode: filters.year === null ? 'first' : 'calendar-year',
    count: filters.count,
    year: filters.year,
    order,
    endpoint: `${backendApiUrl}/api/grants?${params.toString()}`
  };
}

async function fetchGrants(fetch: typeof globalThis.fetch, grantQuery: GrantQuery) {
  const { endpoint } = grantQuery;

  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return {
        grants: [],
        total: null,
        requested: grantQuery.count,
        grantsQuery: grantQuery,
        error: `Backend returned HTTP ${response.status}.`
      };
    }

    const payload = (await response.json()) as FirstGrantsResponse;

    return {
      grants: payload.records ?? [],
      total: payload.total ?? null,
      requested: payload.requested ?? payload.limit ?? grantQuery.count,
      grantsQuery: grantQuery,
      error: null
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown backend error.';

    return {
      grants: [],
      total: null,
      requested: grantQuery.count,
      grantsQuery: grantQuery,
      error: `Could not reach the backend at ${endpoint}: ${message}`
    };
  }
}

async function fetchInnovationRecords(fetch: typeof globalThis.fetch, backendApiUrl: string, filters: DatasetFilters) {
  const endpoint = `${backendApiUrl}/api/business-benefits/first/${filters.count}`;

  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return {
        requested: filters.count,
        count: 0,
        records: [],
        source: null,
        endpoint,
        error: `Backend returned HTTP ${response.status}.`
      };
    }

    const payload = (await response.json()) as FirstInnovationResponse;

    return {
      requested: payload.requested ?? filters.count,
      count: payload.count ?? payload.records?.length ?? 0,
      records: Array.isArray(payload.records) ? payload.records : [],
      source: payload.source ?? null,
      endpoint,
      error: null
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown backend error.';

    return {
      requested: filters.count,
      count: 0,
      records: [],
      source: null,
      endpoint,
      error: `Could not reach the backend at ${endpoint}: ${message}`
    };
  }
}

function emptyGrantsResult(filters: DatasetFilters) {
  return {
    grants: [],
    total: null,
    requested: filters.count,
    grantsQuery: null,
    error: null
  };
}

function emptyInnovationResult(filters: DatasetFilters) {
  return {
    requested: filters.count,
    count: 0,
    records: [],
    source: null,
    endpoint: null,
    error: null
  };
}

export async function loadDashboardData(_fetch: typeof globalThis.fetch, url: URL) {
  const backendApiUrl = (env.PUBLIC_BACKEND_API_URL ?? DEFAULT_BACKEND_API_URL).replace(/\/$/, '');
  const filters = parseFilters(url);
  const grantQuery = buildGrantQuery(filters, backendApiUrl);
  const grantsResult =
    filters.source === 'grants'
      ? {
          grants: [],
          total: null,
          requested: filters.count,
          grantsQuery: grantQuery,
          error: null
        }
      : emptyGrantsResult(filters);
  const innovationResult =
    filters.source === 'innovation'
      ? {
          requested: filters.count,
          count: 0,
          records: [],
          source: null,
          endpoint: `${backendApiUrl}/api/business-benefits/first/${filters.count}`,
          error: null
        }
      : emptyInnovationResult(filters);

  return {
    ...grantsResult,
    filters,
    innovation: innovationResult
  };
}
