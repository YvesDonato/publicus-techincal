import { redirect } from '@sveltejs/kit';
import { normalizeDashboardRedirectUrl } from '$lib/server/dashboard-routes';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, url }) => {
	const code = url.searchParams.get('code');
	const next = getSafeNextPath(url.searchParams.get('next'), url);

	if (code) {
		await locals.supabase.auth.exchangeCodeForSession(code);
	}

	redirect(303, next);
};

function getSafeNextPath(next: string | null, url: URL): string {
	if (!next) {
		return '/dashboard';
	}

	if (next.startsWith('/') && !next.startsWith('//')) {
		const parsed = new URL(next, url.origin);
		return normalizeDashboardRedirectUrl(parsed.pathname, parsed.search, parsed.hash);
	}

	try {
		const parsed = new URL(next);

		if (parsed.origin === url.origin) {
			return normalizeDashboardRedirectUrl(parsed.pathname, parsed.search, parsed.hash);
		}
	} catch {
		return '/dashboard';
	}

	return '/dashboard';
}
