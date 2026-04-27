export type BusinessBenefitsFeedState = {
  dataset_id?: string;
  dataset_title?: string | null;
  dataset_modified?: string | null;
  feed_url?: string | null;
  feed_updated?: string | null;
  latest_entry?: {
    id?: string | null;
    title?: string | null;
    updated?: string | null;
    link?: string | null;
  } | null;
  latest_resource?: {
    id?: string | null;
    name?: string | null;
    url?: string | null;
    created?: string | null;
    last_modified?: string | null;
  } | null;
  marker?: string | null;
};

export const BUSINESS_BENEFITS_FEED_STORAGE_KEY = 'fundradar.businessBenefitsFeed.v1';

export async function fetchBusinessBenefitsFeedState(backendApiUrl: string): Promise<BusinessBenefitsFeedState | null> {
  try {
    const response = await fetch(`${backendApiUrl}/api/business-benefits/update-feed`);

    if (!response.ok) {
      return null;
    }

    const payload: unknown = await response.json();
    return isRecord(payload) ? (payload as BusinessBenefitsFeedState) : null;
  } catch {
    return null;
  }
}

export function readStoredBusinessBenefitsFeedState(): BusinessBenefitsFeedState | null {
  try {
    const rawValue = localStorage.getItem(BUSINESS_BENEFITS_FEED_STORAGE_KEY);
    const parsed: unknown = rawValue ? JSON.parse(rawValue) : null;

    return isRecord(parsed) ? (parsed as BusinessBenefitsFeedState) : null;
  } catch {
    return null;
  }
}

export function writeStoredBusinessBenefitsFeedState(state: BusinessBenefitsFeedState) {
  try {
    localStorage.setItem(BUSINESS_BENEFITS_FEED_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

export function getBusinessBenefitsFeedMarker(state: BusinessBenefitsFeedState | null): string | null {
  if (!state) {
    return null;
  }

  const marker =
    state.marker ??
    [
      state.dataset_modified,
      state.latest_entry?.id,
      state.latest_entry?.updated,
      state.latest_resource?.id,
      state.latest_resource?.last_modified,
      state.latest_resource?.url
    ]
      .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
      .join('|');

  return marker.trim().length > 0 ? marker : null;
}

export function shouldRefreshBusinessBenefitsCache(
  previous: BusinessBenefitsFeedState | null,
  next: BusinessBenefitsFeedState | null
): boolean {
  const nextMarker = getBusinessBenefitsFeedMarker(next);

  if (!nextMarker) {
    return false;
  }

  const previousMarker = getBusinessBenefitsFeedMarker(previous);
  return previousMarker !== nextMarker;
}

export function readStoredStringList(key: string): string[] {
  try {
    const rawValue = localStorage.getItem(key);
    const parsed: unknown = rawValue ? JSON.parse(rawValue) : [];

    if (!Array.isArray(parsed)) {
      return [];
    }

    return [...new Set(parsed.filter((item): item is string => typeof item === 'string').map((item) => item.trim()).filter(Boolean))];
  } catch {
    return [];
  }
}

export function writeStoredStringList(key: string, values: string[]) {
  try {
    localStorage.setItem(key, JSON.stringify([...new Set(values)]));
  } catch {
    // localStorage can be unavailable in private windows or locked-down browsers.
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
