import { loadAuthPage, signUpAction } from '$lib/server/auth-pages';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = loadAuthPage;

export const actions: Actions = {
  default: signUpAction
};
