import { loadGrantsContributionsData } from '$lib/server/live-view-data';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ fetch, url }) => loadGrantsContributionsData(fetch, url);
