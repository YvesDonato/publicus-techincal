import type { Session, SupabaseClient, User } from '@supabase/supabase-js';

// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	namespace App {
		interface AuthUser {
			id: string;
			email: string | null;
			name: string | null;
			avatarUrl: string | null;
		}

		interface AuthSession {
			expiresAt: number | null;
		}

		interface Profile {
			id: string;
			email: string | null;
			full_name: string | null;
			avatar_url: string | null;
			organization_name: string | null;
			title: string | null;
			[key: string]: unknown;
		}

		interface Locals {
			supabase: SupabaseClient;
			safeGetSession: () => Promise<{ session: Session | null; user: User | null }>;
		}

		interface PageData {
			auth?: {
				session: App.AuthSession | null;
				user: App.AuthUser | null;
			};
			profile?: App.Profile | null;
		}
	}
}

export {};
