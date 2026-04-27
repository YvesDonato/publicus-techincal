<script lang="ts">
  const notificationSettings = [
    {
      title: 'New high-fit programs',
      description: 'Alert when a program matches your company profile and sector filters.',
      enabled: true
    },
    {
      title: 'Deadline reminders',
      description: 'Send reminders before saved programs reach intake or application dates.',
      enabled: true
    },
    {
      title: 'Weekly funding digest',
      description: 'Bundle lower-priority updates into one workspace summary.',
      enabled: false
    }
  ];

  const dataControls = [
    ['Company profile', 'Stored locally in this browser'],
    ['Saved programs', 'Synced to this workspace view'],
    ['Export format', 'CSV and application brief']
  ];
</script>

<svelte:head>
  <title>Settings | FundRadar</title>
  <meta name="description" content="Manage FundRadar workspace, account, and notification settings." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="fundradar-dashboard flex h-screen overflow-hidden bg-[#f7f9fb] text-[#191c1e]">
  <nav class="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50 md:flex" aria-label="FundRadar workspace navigation">
    <div class="flex h-full flex-col gap-2 p-4">
      <div class="mb-4 flex items-center gap-3 px-2 py-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 font-bold text-white">FR</div>
        <div>
          <h1 class="m-0 font-[Public_Sans] text-xl font-black leading-none tracking-normal text-slate-900">FundRadar</h1>
          <span class="text-xs text-slate-500">Enterprise Funding</span>
        </div>
      </div>

      <div class="flex flex-1 flex-col gap-1">
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/dashboard">
          <span class="material-symbols-outlined">explore</span>
          <span>Discovery</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/persona">
          <span class="material-symbols-outlined">business_center</span>
          <span>Company Profile</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/live-view">
          <span class="material-symbols-outlined">insert_chart</span>
          <span>Analytics</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/persona/matches">
          <span class="material-symbols-outlined">description</span>
          <span>Opportunity Matches</span>
        </a>
        <a class="flex items-center gap-3 rounded-md bg-emerald-50 px-3 py-2.5 text-emerald-700" href="/settings" aria-current="page">
          <span class="material-symbols-outlined text-emerald-600">settings</span>
          <span>Settings</span>
        </a>
      </div>

      <div class="my-4 px-2">
        <a class="block w-full rounded-lg bg-emerald-600 py-2.5 text-center font-semibold text-white hover:bg-emerald-700" href="/persona/matches">
          Find Funding
        </a>
      </div>

      <div class="flex flex-col gap-1 border-t border-slate-200 pt-4">
        <a class="flex items-center gap-3 rounded-md px-3 py-2 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/">
          <span class="material-symbols-outlined">contact_support</span>
          <span>Support</span>
        </a>
        <a class="flex items-center gap-3 rounded-md px-3 py-2 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/">
          <span class="material-symbols-outlined">logout</span>
          <span>Log Out</span>
        </a>
      </div>
    </div>
  </nav>

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <header class="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div class="flex max-w-md flex-1 items-center">
        <div class="relative hidden w-full md:block">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-slate-400">search</span>
          <input
            class="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
            placeholder="Search settings..."
            type="search"
          />
        </div>
        <span class="block text-lg font-bold text-slate-900 md:hidden">FundRadar</span>
      </div>

      <div class="ml-4 flex items-center gap-2 md:gap-4">
        <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Notifications">
          <span class="material-symbols-outlined">notifications</span>
        </button>
        <button class="rounded-full p-2 text-emerald-600 transition hover:bg-slate-50" type="button" aria-label="Help">
          <span class="material-symbols-outlined">help_outline</span>
        </button>
        <div class="ml-2 flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-emerald-700 text-xs font-black text-white">
          FR
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto p-4 md:p-6">
      <div class="mx-auto max-w-[1440px]">
        <div class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h2 class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">Settings</h2>
            <p class="m-0 max-w-2xl text-base leading-6 text-[#45464d]">
              Manage workspace preferences, alerts, account access, and data controls separately from your company profile.
            </p>
          </div>
          <div class="flex gap-2">
            <a class="flex items-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0]" href="/persona">
              <span class="material-symbols-outlined text-[18px]">badge</span>
              Company Profile
            </a>
            <button class="flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" type="button">
              <span class="material-symbols-outlined text-[18px]">save</span>
              Save Changes
            </button>
          </div>
        </div>

        <section class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4" aria-label="Workspace status">
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Workspace</span>
            <strong class="block text-lg font-semibold text-[#191c1e]">AccessBuild AI</strong>
            <span class="mt-2 inline-flex items-center gap-1 text-sm text-emerald-700">
              <span class="material-symbols-outlined text-[16px]">verified</span>
              Active
            </span>
          </article>
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Role</span>
            <strong class="block text-lg font-semibold text-[#191c1e]">Owner</strong>
            <span class="mt-2 block text-sm text-[#45464d]">Full workspace access</span>
          </article>
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Alerts</span>
            <strong class="block text-lg font-semibold text-[#191c1e]">2 enabled</strong>
            <span class="mt-2 block text-sm text-[#45464d]">Digest paused</span>
          </article>
          <article class="rounded-xl border border-[#c6c6cd] bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-[#45464d]">Data</span>
            <strong class="block text-lg font-semibold text-[#191c1e]">Local profile</strong>
            <span class="mt-2 block text-sm text-[#45464d]">Browser storage</span>
          </article>
        </section>

        <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
          <section class="flex flex-col gap-6 lg:col-span-8" aria-label="Settings controls">
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4 border-b border-[#c6c6cd] pb-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Account</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Workspace Access</h3>
                  <p class="m-0 mt-1 text-sm leading-6 text-[#45464d]">Review the visible workspace identity and routing defaults for this account.</p>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">admin_panel_settings</span>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Workspace name
                  <input class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20" value="AccessBuild AI" />
                </label>
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Account role
                  <select class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20">
                    <option>Owner</option>
                    <option>Administrator</option>
                    <option>Viewer</option>
                  </select>
                </label>
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Default route
                  <select class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20">
                    <option>Funding Discovery</option>
                    <option>Company Profile</option>
                    <option>Discovery</option>
                  </select>
                </label>
                <label class="grid gap-2 text-sm font-semibold text-[#45464d]">
                  Program volume
                  <select class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-normal text-[#191c1e] focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20">
                    <option>100 records</option>
                    <option>200 records</option>
                    <option>500 records</option>
                  </select>
                </label>
              </div>
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-5 flex items-start justify-between gap-4 border-b border-[#c6c6cd] pb-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Notifications</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Funding Alerts</h3>
                  <p class="m-0 mt-1 text-sm leading-6 text-[#45464d]">Control how FundRadar surfaces new programs and application reminders.</p>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">notifications_active</span>
              </div>

              <div class="divide-y divide-[#c6c6cd]">
                {#each notificationSettings as setting (setting.title)}
                  <label class="flex cursor-pointer items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
                    <span>
                      <strong class="block text-sm font-semibold text-[#191c1e]">{setting.title}</strong>
                      <span class="mt-1 block text-sm leading-6 text-[#45464d]">{setting.description}</span>
                    </span>
                    <input
                      class="h-5 w-5 shrink-0 rounded border-slate-400 text-emerald-700 focus:ring-emerald-700"
                      type="checkbox"
                      checked={setting.enabled}
                    />
                  </label>
                {/each}
              </div>
            </article>
          </section>

          <aside class="flex flex-col gap-6 lg:col-span-4" aria-label="Settings summary">
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-4 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Profile</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Company Profile</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">badge</span>
              </div>
              <p class="m-0 mb-5 text-sm leading-6 text-[#45464d]">
                Settings are managed separately from eligibility details, funding criteria, and saved application context.
              </p>
              <a class="inline-flex items-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0]" href="/persona">
                Open Company Profile
                <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
              </a>
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <div class="mb-4 flex items-start justify-between gap-4">
                <div>
                  <span class="mb-1 block text-xs font-semibold uppercase tracking-normal text-emerald-700">Data & Privacy</span>
                  <h3 class="m-0 text-xl font-semibold text-[#191c1e]">Storage Controls</h3>
                </div>
                <span class="material-symbols-outlined rounded-lg bg-emerald-50 p-2 text-emerald-700">database</span>
              </div>

              <dl class="m-0 grid gap-3">
                {#each dataControls as control (control[0])}
                  <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <dt class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">{control[0]}</dt>
                    <dd class="m-0 mt-1 text-sm font-semibold text-[#191c1e]">{control[1]}</dd>
                  </div>
                {/each}
              </dl>
            </article>

            <article class="rounded-xl border border-[#c6c6cd] bg-[#131b2e] p-5 text-[#dae2fd] shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
              <span class="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-white">
                <span class="material-symbols-outlined text-[14px]">shield</span>
                Secure workspace
              </span>
              <h3 class="m-0 mb-2 text-xl font-semibold">Access Review</h3>
              <p class="m-0 mb-5 text-sm leading-6 text-[#dae2fd]/80">
                Keep team access aligned with the people preparing applications and reviewing program eligibility.
              </p>
              <button class="rounded border border-[#dae2fd]/30 px-4 py-2 text-sm font-semibold text-[#dae2fd] transition hover:bg-white/10" type="button">
                Review Access
              </button>
            </article>
          </aside>
        </div>
      </div>
    </main>
  </div>
</div>

<style>
  .fundradar-dashboard {
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  }

  .material-symbols-outlined {
    font-family: "Material Symbols Outlined";
    font-weight: normal;
    font-style: normal;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    overflow-wrap: normal;
    direction: ltr;
    font-feature-settings: "liga";
    -webkit-font-feature-settings: "liga";
    -webkit-font-smoothing: antialiased;
    font-variation-settings:
      "FILL" 0,
      "wght" 400,
      "GRAD" 0,
      "opsz" 24;
  }
</style>
