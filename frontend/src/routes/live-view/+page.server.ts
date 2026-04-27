import { loadBusinessBenefitsFinderData } from '$lib/server/live-view-data';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ fetch, url }) => loadBusinessBenefitsFinderData(fetch, url);
