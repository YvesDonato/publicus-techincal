import { error as kitError, fail, redirect } from '@sveltejs/kit';
import type { Session, SupabaseClient, User } from '@supabase/supabase-js';
import type { Actions, PageServerLoad } from './$types';

type SafeSessionResult = {
  session: Session | null;
  user: User | null;
};

type AuthLocals = App.Locals & {
  supabase: SupabaseClient;
  safeGetSession: () => Promise<SafeSessionResult>;
};

type ProfileValues = {
  email: string;
  fullName: string;
  organizationName: string;
  title: string;
};

type ProfileRow = {
  email?: unknown;
  full_name?: unknown;
  organization_name?: unknown;
  title?: unknown;
};

const PROFILE_TABLE_LOAD_WARNING = 'The profiles table is not configured for this workspace yet; account metadata will still be available.';
const PROFILE_TABLE_SAVE_WARNING = 'Account metadata was saved, but the profiles table is not configured for this workspace yet.';

export const load: PageServerLoad = async ({ locals, url }) => {
  const { supabase, safeGetSession } = getAuthLocals(locals);
  const { user } = await safeGetSession();

  if (!user) {
    redirect(303, `/login?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const { profileRow, warning } = await readProfileRow(supabase, user.id);

	return {
		accountProfile: buildProfileValues(user, profileRow),
		profileWarning: warning
	};
};

export const actions: Actions = {
  default: async ({ locals, request, url }) => {
    const { supabase, safeGetSession } = getAuthLocals(locals);
    const { user } = await safeGetSession();

    if (!user) {
      redirect(303, `/login?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const values = readProfileValues(formData, user.email ?? '');

    const { error: metadataError } = await supabase.auth.updateUser({
      data: {
        full_name: values.fullName,
        organization_name: values.organizationName,
        title: values.title
      }
    });

    if (metadataError) {
      return fail(400, {
        error: metadataError.message,
        values
      });
    }

    const { error: profileError } = await supabase.from('profiles').upsert(
      {
        id: user.id,
        email: values.email,
        full_name: values.fullName,
        organization_name: values.organizationName,
        title: values.title,
        updated_at: new Date().toISOString()
      },
      { onConflict: 'id' }
    );

    return {
      success: true,
      message: 'Profile saved.',
      warning: profileError ? PROFILE_TABLE_SAVE_WARNING : '',
      values
    };
  }
};

function getAuthLocals(locals: App.Locals): AuthLocals {
  const authLocals = locals as Partial<AuthLocals>;

  if (!authLocals.supabase || !authLocals.safeGetSession) {
    kitError(500, 'Authentication is not configured.');
  }

  return authLocals as AuthLocals;
}

async function readProfileRow(
  supabase: SupabaseClient,
  userId: string
): Promise<{ profileRow: ProfileRow | null; warning: string }> {
  const { data, error } = await supabase
    .from('profiles')
    .select('email, full_name, organization_name, title')
    .eq('id', userId)
    .maybeSingle();

  if (error) {
    return {
      profileRow: null,
      warning: PROFILE_TABLE_LOAD_WARNING
    };
  }

  return {
    profileRow: (data ?? null) as ProfileRow | null,
    warning: ''
  };
}

function buildProfileValues(user: User, profileRow: ProfileRow | null): ProfileValues {
  const metadata = user.user_metadata ?? {};

  return {
    email: firstString(user.email, profileRow?.email),
    fullName: firstString(metadata.full_name, metadata.name, profileRow?.full_name),
    organizationName: firstString(metadata.organization_name, metadata.organization, profileRow?.organization_name),
    title: firstString(metadata.title, metadata.role, profileRow?.title)
  };
}

function readProfileValues(formData: FormData, email: string): ProfileValues {
  return {
    email,
    fullName: readString(formData, 'full_name'),
    organizationName: readString(formData, 'organization_name'),
    title: readString(formData, 'title')
  };
}

function readString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === 'string' ? value.trim() : '';
}

function firstString(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return '';
}
