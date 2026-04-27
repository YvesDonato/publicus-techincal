import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

type ActivityKey = 'research' | 'hiring' | 'equipment' | 'export' | 'facilities' | 'sustainability';
type CompanyType = 'for-profit' | 'nonprofit' | 'academic' | 'public-sector';
type EmployeeRange = '1-10' | '11-50' | '51-200' | '200+';
type CompanyProfilePayload = {
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

const activityKeys: ActivityKey[] = ['research', 'hiring', 'equipment', 'export', 'facilities', 'sustainability'];
const companyTypes: CompanyType[] = ['for-profit', 'nonprofit', 'academic', 'public-sector'];
const employeeRanges: EmployeeRange[] = ['1-10', '11-50', '51-200', '200+'];
const provinces = new Set(['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']);
const companyProfileLoadWarning = 'Company profile storage is temporarily unavailable.';

export const GET: RequestHandler = async ({ locals }) => {
  const { user } = await locals.safeGetSession();

  if (!user) {
    error(401, 'Authentication required.');
  }

  const { data, error: profileError } = await locals.supabase
    .from('company_profiles')
    .select(
      'legal_entity_name, doing_business_as, incorporation_date, website, province, city, company_type, employee_range, industry, sub_sector, keywords, funding_need, funding_objectives'
    )
    .eq('user_id', user.id)
    .maybeSingle();

  if (profileError) {
    return json({ profile: null, warning: companyProfileLoadWarning });
  }

  return json({
    profile: data ? rowToPayload(data as Record<string, unknown>) : null
  });
};

export const PUT: RequestHandler = async ({ locals, request }) => {
  const { user } = await locals.safeGetSession();

  if (!user) {
    error(401, 'Authentication required.');
  }

  const payload = normalizePayload(await request.json());
  const { error: upsertError } = await locals.supabase.from('company_profiles').upsert(
    {
      user_id: user.id,
      legal_entity_name: payload.legalEntityName,
      doing_business_as: nullable(payload.doingBusinessAs),
      incorporation_date: nullable(payload.incorporationDate),
      website: nullable(payload.website),
      province: nullable(payload.province),
      city: nullable(payload.city),
      company_type: payload.companyType,
      employee_range: payload.employeeRange,
      industry: nullable(payload.industry),
      sub_sector: nullable(payload.subSector),
      keywords: nullable(payload.keywords),
      funding_need: parseFundingNeed(payload.fundingNeed),
      funding_objectives: activityKeys.filter((key) => payload.activities[key])
    },
    {
      onConflict: 'user_id'
    }
  );

  if (upsertError) {
    error(400, 'Could not save company profile.');
  }

  return json({ profile: payload });
};

function rowToPayload(row: Record<string, unknown>): CompanyProfilePayload {
  const objectives = Array.isArray(row.funding_objectives)
    ? new Set(row.funding_objectives.filter((value): value is ActivityKey => isActivityKey(value)))
    : new Set<ActivityKey>();

  return normalizePayload({
    legalEntityName: row.legal_entity_name,
    doingBusinessAs: row.doing_business_as,
    incorporationDate: row.incorporation_date,
    website: row.website,
    province: row.province,
    city: row.city,
    companyType: row.company_type,
    employeeRange: row.employee_range,
    industry: row.industry,
    subSector: row.sub_sector,
    keywords: row.keywords,
    fundingNeed: typeof row.funding_need === 'number' ? String(row.funding_need) : row.funding_need,
    activities: Object.fromEntries(activityKeys.map((key) => [key, objectives.has(key)]))
  });
}

function normalizePayload(value: unknown): CompanyProfilePayload {
  const record = isRecord(value) ? value : {};
  const activities = isRecord(record.activities) ? record.activities : {};
  const companyType = readEnum(record.companyType, companyTypes, 'for-profit');
  const employeeRange = readEnum(record.employeeRange, employeeRanges, '11-50');
  const province = readString(record.province, 2).toUpperCase();

  return {
    legalEntityName: readString(record.legalEntityName, 240),
    doingBusinessAs: readString(record.doingBusinessAs, 240),
    incorporationDate: readDate(record.incorporationDate),
    website: readUrl(record.website),
    province: provinces.has(province) ? province : '',
    city: readString(record.city, 120),
    companyType,
    employeeRange,
    industry: readString(record.industry, 100),
    subSector: readString(record.subSector, 100),
    keywords: readString(record.keywords, 2000),
    fundingNeed: readString(record.fundingNeed, 20),
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isActivityKey(value: unknown): value is ActivityKey {
  return typeof value === 'string' && activityKeys.includes(value as ActivityKey);
}

function readString(value: unknown, maxLength: number): string {
  return typeof value === 'string' ? value.trim().slice(0, maxLength) : '';
}

function readDate(value: unknown): string {
  const candidate = readString(value, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(candidate) ? candidate : '';
}

function readUrl(value: unknown): string {
  const candidate = readString(value, 2048);
  return candidate === '' || /^https?:\/\//i.test(candidate) ? candidate : '';
}

function readEnum<T extends string>(value: unknown, allowed: T[], fallback: T): T {
  return typeof value === 'string' && allowed.includes(value as T) ? (value as T) : fallback;
}

function nullable(value: string): string | null {
  return value.length > 0 ? value : null;
}

function parseFundingNeed(value: string): number | null {
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.min(parsed, 100000000000) : null;
}
