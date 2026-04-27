const legacyDashboardPaths = new Map<string, string>([
  ['/business-benefits-finder', '/dashboard/business-benefits-finder'],
  ['/graph-view', '/dashboard/graph-view'],
  ['/grants-contributions', '/dashboard/grants-contributions'],
  ['/live-view', '/dashboard/live-view'],
  ['/persona/matches', '/dashboard/persona/matches'],
  ['/persona', '/dashboard/persona'],
  ['/profile', '/dashboard/profile'],
  ['/settings', '/dashboard/settings']
]);

export function normalizeDashboardPath(pathname: string): string {
  return legacyDashboardPaths.get(pathname) ?? pathname;
}

export function normalizeDashboardUrl(pathname: string, search = '', hash = ''): string {
  return `${normalizeDashboardPath(pathname)}${search}${hash}`;
}

export function isDashboardPath(pathname: string): boolean {
  return pathname === '/dashboard' || pathname.startsWith('/dashboard/');
}

export function normalizeDashboardRedirectUrl(pathname: string, search = '', hash = ''): string {
  const normalizedPath = normalizeDashboardPath(pathname);

  if (!isDashboardPath(normalizedPath)) {
    return '/dashboard';
  }

  return `${normalizedPath}${search}${hash}`;
}
