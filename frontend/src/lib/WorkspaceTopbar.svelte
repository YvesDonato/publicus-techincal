<script lang="ts">
  import { page } from '$app/state';
  import DashboardSearch from './DashboardSearch.svelte';

  type AuthUser = {
    id?: string | null;
    email?: string | null;
    name?: string | null;
    avatarUrl?: string | null;
  };

  type AuthState = {
    user?: AuthUser | null;
  } | null;

  type ProfileState = {
    full_name?: string | null;
    organization_name?: string | null;
    title?: string | null;
    avatar_url?: string | null;
  } | null;

  type NavigationPageData = {
    auth?: AuthState;
    profile?: ProfileState;
  };

  let { placeholder = 'Search pages, tools, or funding data...' }: { placeholder?: string } = $props();

  const auth = $derived((page.data as NavigationPageData).auth);
  const profile = $derived((page.data as NavigationPageData).profile);
  const user = $derived(auth?.user ?? null);
  const email = $derived(user?.email?.trim() ?? '');
  const profileName = $derived(profile?.full_name?.trim() ?? '');
  const organizationName = $derived(profile?.organization_name?.trim() ?? '');
  const accountName = $derived(profileName || organizationName || user?.name?.trim() || email || 'FundRadar account');
  const accountDetail = $derived(profile?.title?.trim() || (profileName && organizationName ? organizationName : email));
  const accountInitials = $derived(getInitials(profileName, organizationName, email));
  const avatarUrl = $derived(profile?.avatar_url?.trim() || user?.avatarUrl?.trim() || '');

  function getInitials(...sources: Array<string | null | undefined>): string {
    const source = sources.find((value) => value?.trim())?.trim();

    if (!source) {
      return 'FR';
    }

    const normalizedSource = source.includes('@') ? source.split('@')[0] : source;
    const words = normalizedSource.split(/[\s._-]+/).filter(Boolean);
    const initials = words.length > 1 ? `${words[0][0]}${words[1][0]}` : normalizedSource.slice(0, 2);

    return initials.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 2) || 'FR';
  }
</script>

<header class="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm md:px-6">
  <div class="flex max-w-md flex-1 items-center">
    <div class="relative hidden w-full md:block">
      <DashboardSearch {placeholder} />
    </div>
    <a class="block text-lg font-bold text-slate-900 no-underline md:hidden" href="/">FundRadar</a>
  </div>

  <div class="ml-4 flex items-center gap-2 md:gap-4">
    <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Notifications">
      <span class="material-symbols-outlined">notifications</span>
    </button>
    <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Help">
      <span class="material-symbols-outlined">help_outline</span>
    </button>
    {#if user}
      <a
        class="ml-1 flex min-w-0 items-center gap-2 rounded-lg px-1.5 py-1 text-slate-700 no-underline transition hover:bg-slate-50 md:ml-2"
        href="/dashboard/profile"
        aria-label="Account Profile"
      >
        <span class="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-emerald-700 text-xs font-black text-white">
          {#if avatarUrl}
            <img class="h-full w-full object-cover" src={avatarUrl} alt="" />
          {:else}
            {accountInitials}
          {/if}
        </span>
        <span class="hidden min-w-0 text-left leading-tight sm:block">
          <span class="block max-w-36 truncate text-sm font-bold text-slate-900">{accountName}</span>
          {#if accountDetail}
            <span class="block max-w-36 truncate text-xs text-slate-500">{accountDetail}</span>
          {/if}
        </span>
      </a>
      <form method="POST" action="/logout">
        <button class="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 text-sm font-semibold text-slate-600 no-underline transition hover:bg-slate-50 hover:text-slate-900" type="submit">
        <span class="material-symbols-outlined text-[20px]" aria-hidden="true">logout</span>
        <span class="hidden sm:inline">Log out</span>
        </button>
      </form>
    {:else}
      <a class="inline-flex h-9 items-center rounded-lg border border-[#c6c6cd] px-3 text-sm font-semibold text-[#191c1e] no-underline transition hover:bg-[#eceef0]" href="/login">
        Sign in
      </a>
    {/if}
  </div>
</header>
