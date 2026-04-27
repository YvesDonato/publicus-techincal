import { env } from '$env/dynamic/public';
import { createServerClient } from '@supabase/ssr';
import type { SetAllCookies } from '@supabase/ssr';
import type { SupabaseClient, User } from '@supabase/supabase-js';
import type { RequestEvent } from '@sveltejs/kit';

export function createSupabaseClient(event: RequestEvent): SupabaseClient {
	const { supabaseKey, supabaseUrl } = getSupabaseEnvironment();
	const setAll: SetAllCookies = (cookiesToSet) => {
		for (const { name, value, options } of cookiesToSet) {
			event.cookies.set(name, value, { ...options, path: '/' });
		}
	};

	return createServerClient(supabaseUrl, supabaseKey, {
		cookies: {
			getAll: () => event.cookies.getAll(),
			setAll
		}
	});
}

function getSupabaseEnvironment(): { supabaseKey: string; supabaseUrl: string } {
	const supabaseUrl = env.PUBLIC_SUPABASE_URL;
	const supabaseKey = env.PUBLIC_SUPABASE_PUBLISHABLE_KEY;

	if (!supabaseUrl || !supabaseKey) {
		throw new Error('Missing PUBLIC_SUPABASE_URL or PUBLIC_SUPABASE_PUBLISHABLE_KEY.');
	}

	return { supabaseKey, supabaseUrl };
}

export function profileFromUser(user: User): App.Profile {
	const metadata = user.user_metadata ?? {};

	return {
		id: user.id,
		email: user.email ?? null,
		full_name: getStringMetadata(metadata, 'full_name') ?? getStringMetadata(metadata, 'name'),
		avatar_url: getStringMetadata(metadata, 'avatar_url') ?? getStringMetadata(metadata, 'picture'),
		organization_name:
			getStringMetadata(metadata, 'organization_name') ??
			getStringMetadata(metadata, 'company_name') ??
			getStringMetadata(metadata, 'organization') ??
			getStringMetadata(metadata, 'company'),
		title: getStringMetadata(metadata, 'title') ?? getStringMetadata(metadata, 'role')
	};
}

export async function loadProfile(supabase: SupabaseClient, user: User): Promise<App.Profile> {
	try {
		const { data, error } = await supabase.from('profiles').select('*').eq('id', user.id).maybeSingle();

		if (!error && data && typeof data === 'object') {
			return { ...profileFromUser(user), ...data };
		}
	} catch {
		// A missing table, disabled RLS policy, or local schema mismatch should not break auth state.
	}

	return profileFromUser(user);
}

function getStringMetadata(metadata: Record<string, unknown>, key: string): string | null {
	const value = metadata[key];
	return typeof value === 'string' && value.length > 0 ? value : null;
}
