import { error as kitError, fail, redirect } from '@sveltejs/kit';
import type { Session, SupabaseClient, User } from '@supabase/supabase-js';
import { normalizeDashboardRedirectUrl } from '$lib/server/dashboard-routes';

type SafeSessionResult = {
  session: Session | null;
  user: User | null;
};

type AuthLocals = App.Locals & {
  supabase: SupabaseClient;
  safeGetSession: () => Promise<SafeSessionResult>;
};

type AuthLoadEvent = {
  locals: App.Locals;
  url: URL;
};

type AuthActionEvent = AuthLoadEvent & {
  request: Request;
};

type SignUpProfile = {
  fullName: string;
  organizationName: string;
  title: string;
};

export async function loadAuthPage({ locals, url }: AuthLoadEvent) {
  const { safeGetSession } = getAuthLocals(locals);
  const next = safeRedirectPath(url.searchParams.get('next'));
  const { session } = await safeGetSession();

  if (session) {
    redirect(303, next);
  }

  return {
    next
  };
}

export async function signInAction({ locals, request, url }: AuthActionEvent) {
  const { supabase } = getAuthLocals(locals);
  const formData = await request.formData();
  const email = readString(formData, 'email').toLowerCase();
  const password = readString(formData, 'password');
  const next = readNextPath(formData, url);

  if (!email || !password) {
    return fail(400, {
      error: 'Enter your email and password.',
      values: { email }
    });
  }

  const { error } = await supabase.auth.signInWithPassword({
    email,
    password
  });

  if (error) {
    return fail(400, {
      error: 'The email or password did not match an account.',
      values: { email }
    });
  }

  redirect(303, next);
}

export async function signUpAction({ locals, request, url }: AuthActionEvent) {
  const { supabase } = getAuthLocals(locals);
  const formData = await request.formData();
  const email = readString(formData, 'email').toLowerCase();
  const password = readString(formData, 'password');
  const profile = readSignUpProfile(formData);
  const next = readNextPath(formData, url);

  if (!email || !password) {
    return fail(400, {
      error: 'Enter an email and password to create an account.',
      values: { email, ...profile }
    });
  }

  if (password.length < 6) {
    return fail(400, {
      error: 'Use a password with at least 6 characters.',
      values: { email, ...profile }
    });
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${url.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      data: {
        full_name: profile.fullName,
        organization_name: profile.organizationName,
        title: profile.title
      }
    }
  });

  if (error) {
    return fail(400, {
      error: error.message,
      values: { email, ...profile }
    });
  }

  if (data.session) {
    redirect(303, next);
  }

  return {
    message: 'Account created. Check your email to confirm the account, then sign in.',
    values: { email, ...profile }
  };
}

function getAuthLocals(locals: App.Locals): AuthLocals {
  const authLocals = locals as Partial<AuthLocals>;

  if (!authLocals.supabase || !authLocals.safeGetSession) {
    kitError(500, 'Authentication is not configured.');
  }

  return authLocals as AuthLocals;
}

function readSignUpProfile(formData: FormData): SignUpProfile {
  return {
    fullName: readString(formData, 'full_name'),
    organizationName: readString(formData, 'organization_name'),
    title: readString(formData, 'title')
  };
}

function readNextPath(formData: FormData, url: URL): string {
  return safeRedirectPath(readString(formData, 'next') || url.searchParams.get('next'));
}

function readString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === 'string' ? value.trim() : '';
}

function safeRedirectPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) {
    return '/dashboard';
  }

  try {
    const parsed = new URL(value, 'https://fundradar.local');

    if (parsed.origin !== 'https://fundradar.local') {
      return '/dashboard';
    }

    return normalizeDashboardRedirectUrl(parsed.pathname, parsed.search, parsed.hash);
  } catch {
    return '/dashboard';
  }
}
