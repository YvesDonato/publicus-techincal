<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';

  const settingsLinks = [
    {
      icon: 'manage_accounts',
      title: 'Account Profile',
      description: 'Update your name, organization, and role.',
      href: '/dashboard/profile',
      label: 'Open account profile'
    },
    {
      icon: 'business_center',
      title: 'Company Profile',
      description: 'Edit the company details used for opportunity matching.',
      href: '/dashboard/persona',
      label: 'Open company profile'
    },
    {
      icon: 'description',
      title: 'Opportunity Shortlist',
      description: 'Review ranked matches and saved opportunities.',
      href: '/dashboard/persona/matches',
      label: 'Open opportunity matches'
    }
  ];
</script>

<svelte:head>
  <title>Settings | FundRadar</title>
  <meta name="description" content="Open implemented FundRadar account and workspace controls." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="settings" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search settings, pages, or funding data..." />

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1180px]">
        <div class="mb-6">
          <p class="m-0 mb-2 text-xs font-black uppercase text-emerald-700">Settings</p>
          <h1 class="m-0 font-[Public_Sans] text-4xl font-black leading-tight text-[#191c1e]">Settings</h1>
          <p class="m-0 mt-2 max-w-2xl text-base leading-6 text-[#45464d]">
            Use the implemented account and workspace controls below.
          </p>
        </div>

        <section class="grid gap-4 md:grid-cols-3" aria-label="Available settings">
          {#each settingsLinks as item (item.href)}
            <a
              class="flex min-h-56 flex-col justify-between rounded-xl border border-[#c6c6cd] bg-white p-5 text-[#191c1e] no-underline shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]"
              href={item.href}
            >
              <span>
                <span class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                  <span class="material-symbols-outlined">{item.icon}</span>
                </span>
                <span class="block font-[Public_Sans] text-xl font-black leading-tight">{item.title}</span>
                <span class="mt-2 block text-sm leading-6 text-[#45464d]">{item.description}</span>
              </span>
              <span class="mt-6 inline-flex items-center gap-2 text-sm font-black text-emerald-700">
                {item.label}
                <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
              </span>
            </a>
          {/each}
        </section>

        <section class="mt-6 rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="session-heading">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 id="session-heading" class="m-0 font-[Public_Sans] text-xl font-black text-[#191c1e]">Session</h2>
              <p class="m-0 mt-1 text-sm leading-6 text-[#45464d]">End the current authenticated session on this device.</p>
            </div>
            <form method="POST" action="/logout">
              <button class="inline-flex items-center justify-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0]" type="submit">
                <span class="material-symbols-outlined text-[18px]">logout</span>
                Sign out
              </button>
            </form>
          </div>
        </section>
      </div>
    </main>
  </div>
</div>
