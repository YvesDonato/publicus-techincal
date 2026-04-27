import { loadProfile } from '$lib/server/supabase';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	const { session, user } = await locals.safeGetSession();
	const profile = user ? await loadProfile(locals.supabase, user) : null;

	return {
		auth: {
			session: session
				? {
						expiresAt: session.expires_at ?? null
					}
				: null,
			user: user
				? {
						id: user.id,
						email: user.email ?? null,
						name: profile?.full_name ?? null,
						avatarUrl: profile?.avatar_url ?? null
					}
				: null
		},
		profile
	};
};
