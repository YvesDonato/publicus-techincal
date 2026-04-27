import { createSupabaseClient } from '$lib/server/supabase';
import { isDashboardPath } from '$lib/server/dashboard-routes';
import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.supabase = createSupabaseClient(event);

	event.locals.safeGetSession = async () => {
		const {
			data: { session }
		} = await event.locals.supabase.auth.getSession();

		if (!session) {
			return { session: null, user: null };
		}

		const {
			data: { user },
			error
		} = await event.locals.supabase.auth.getUser();

		if (error || !user) {
			return { session: null, user: null };
		}

		return { session, user };
	};

	if (isDashboardPath(event.url.pathname)) {
		const { session } = await event.locals.safeGetSession();

		if (!session) {
			redirect(303, `/login?next=${encodeURIComponent(`${event.url.pathname}${event.url.search}`)}`);
		}
	}

	const response = await resolve(event, {
		filterSerializedResponseHeaders: (name) =>
			name === 'content-range' || name === 'x-supabase-api-version'
	});

	response.headers.set('X-Content-Type-Options', 'nosniff');
	response.headers.set('X-Frame-Options', 'DENY');
	response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
	response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

	return response;
};
