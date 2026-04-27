import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = ({ url }) => {
  redirect(308, `/dashboard/live-view${url.search}`);
};
