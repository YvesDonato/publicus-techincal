<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
  import type { ActionData, PageData } from './$types';

  type ProfileValues = {
    email: string;
    fullName: string;
    organizationName: string;
    title: string;
  };
  type ProfileResult = {
    success?: boolean;
    message?: string;
    warning?: string;
    error?: string;
    values?: ProfileValues;
  };
  type ProfilePageData = PageData & {
    accountProfile: ProfileValues;
    profileWarning: string;
  };

  let {
    data,
    form
  }: {
    data: ProfilePageData;
    form?: ActionData;
  } = $props();

  const result = $derived((form ?? {}) as ProfileResult);
  const profile = $derived(result.values ?? data.accountProfile);
  const warning = $derived(result.warning || data.profileWarning);
  const initials = $derived(getInitials(profile.fullName || profile.email));

  function getInitials(value: string): string {
    const parts = value
      .split(/[ @._-]+/)
      .map((part) => part.trim())
      .filter(Boolean);

    return (parts[0]?.[0] ?? 'F') + (parts[1]?.[0] ?? 'R');
  }
</script>

<svelte:head>
  <title>Account Profile | FundRadar</title>
  <meta name="description" content="Manage your FundRadar account profile." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="account" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search profile, settings, or funding data..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1180px]">
        <div class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p class="m-0 mb-2 text-xs font-black uppercase text-emerald-700">Account Profile</p>
            <h1 class="m-0 font-[Public_Sans] text-4xl font-black leading-tight text-[#191c1e]">Account Profile</h1>
            <p class="m-0 mt-2 max-w-2xl text-base leading-6 text-[#45464d]">
              Manage the account identity FundRadar uses across the workspace.
            </p>
          </div>
          <form method="POST" action="/logout">
            <button class="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] no-underline transition hover:bg-[#eceef0]" type="submit">
              <span class="material-symbols-outlined text-[18px]">logout</span>
              Sign out
            </button>
          </form>
        </div>

        <div class="grid gap-6 lg:grid-cols-[0.72fr_0.28fr]">
          <section class="rounded-lg border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)] md:p-6" aria-labelledby="profile-form-heading">
            <div class="mb-5 flex items-start justify-between gap-4 border-b border-[#c6c6cd] pb-5">
              <div>
                <p class="m-0 mb-1 text-xs font-black uppercase text-emerald-700">Workspace identity</p>
                <h2 id="profile-form-heading" class="m-0 text-2xl font-black text-[#191c1e]">Account details</h2>
              </div>
              <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">manage_accounts</span>
            </div>

            <div class="mb-5 grid gap-3" aria-live="polite">
              {#if result.error}
                <p class="m-0 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700" role="alert">
                  {result.error}
                </p>
              {:else if result.message}
                <p class="m-0 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800" role="status">
                  {result.message}
                </p>
              {/if}

              {#if warning}
                <p class="m-0 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800" role="status">
                  {warning}
                </p>
              {/if}
            </div>

            <form class="grid gap-5" method="POST">
              <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                Email
                <input
                  class="rounded-lg border border-slate-200 bg-slate-100 px-3 py-2.5 font-normal text-[#191c1e]"
                  name="email"
                  type="email"
                  value={profile.email}
                  readonly
                />
              </label>

              <div class="grid gap-5 md:grid-cols-2">
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Full name
                  <input
                    class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                    autocomplete="name"
                    name="full_name"
                    value={profile.fullName}
                  />
                </label>
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Organization
                  <input
                    class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                    autocomplete="organization"
                    name="organization_name"
                    value={profile.organizationName}
                  />
                </label>
                <label class="grid gap-2 text-sm font-semibold text-[#45464d] md:col-span-2">
                  Role/title
                  <input
                    class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                    autocomplete="organization-title"
                    name="title"
                    value={profile.title}
                  />
                </label>
              </div>

              <div class="flex flex-col-reverse gap-3 border-t border-[#c6c6cd] pt-5 sm:flex-row sm:items-center sm:justify-between">
                <a class="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] no-underline transition hover:bg-[#eceef0]" href="/dashboard/settings">
                  <span class="material-symbols-outlined text-[18px]">settings</span>
                  Settings
                </a>
                <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" type="submit">
                  <span class="material-symbols-outlined text-[18px]">save</span>
                  Save profile
                </button>
              </div>
            </form>
          </section>

          <aside class="grid gap-6 content-start" aria-label="Account summary">
            <article class="rounded-lg border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-4 flex items-center gap-3">
                <div class="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-700 text-sm font-black uppercase text-white">
                  {initials}
                </div>
                <div class="min-w-0">
                  <strong class="block truncate text-base font-black text-[#191c1e]">{profile.fullName || 'FundRadar user'}</strong>
                  <span class="block truncate text-sm text-[#45464d]">{profile.email}</span>
                </div>
              </div>
              <dl class="m-0 grid gap-3">
                <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <dt class="text-xs font-black uppercase text-[#45464d]">Organization</dt>
                  <dd class="m-0 mt-1 text-sm font-semibold text-[#191c1e]">{profile.organizationName || 'Not set'}</dd>
                </div>
                <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <dt class="text-xs font-black uppercase text-[#45464d]">Role/title</dt>
                  <dd class="m-0 mt-1 text-sm font-semibold text-[#191c1e]">{profile.title || 'Not set'}</dd>
                </div>
              </dl>
            </article>

            <article class="rounded-lg border border-[#c6c6cd] bg-[#131b2e] p-5 text-[#dae2fd] shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
              <span class="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-black uppercase text-white">
                <span class="material-symbols-outlined text-[14px]">verified_user</span>
                Auth metadata
              </span>
              <h2 class="m-0 mb-2 text-xl font-black text-white">Primary storage</h2>
              <p class="m-0 text-sm leading-6 text-[#dae2fd]/80">
                Profile changes are saved to Supabase auth metadata first. The workspace profile table is used when it is available.
              </p>
            </article>
          </aside>
        </div>
      </div>
    </main>
  </div>
</div>
