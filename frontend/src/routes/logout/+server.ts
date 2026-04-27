import { error as kitError, redirect } from '@sveltejs/kit';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { RequestHandler } from './$types';

type AuthLocals = App.Locals & {
  supabase: SupabaseClient;
};

const signOut: RequestHandler = async ({ locals }) => {
  const { supabase } = getAuthLocals(locals);

  await supabase.auth.signOut();
  redirect(303, '/login');
};

export const POST = signOut;

function getAuthLocals(locals: App.Locals): AuthLocals {
  const authLocals = locals as Partial<AuthLocals>;

  if (!authLocals.supabase) {
    kitError(500, 'Authentication is not configured.');
  }

  return authLocals as AuthLocals;
}
