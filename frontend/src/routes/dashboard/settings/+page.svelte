<script lang="ts">
  import WorkspaceSidebar from '$lib/WorkspaceSidebar.svelte';
  import WorkspaceTopbar from '$lib/WorkspaceTopbar.svelte';
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
    ['Saved programs', 'Available in this workspace'],
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

<div class="flex h-screen overflow-hidden bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e]">
  <WorkspaceSidebar active="settings" />

  <div class="relative flex h-screen min-w-0 flex-1 flex-col bg-[#f7f9fb]">
    <WorkspaceTopbar placeholder="Search settings, pages, or funding data..." />

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
            <a class="flex items-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0]" href="/dashboard/persona">
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
                    <option>Overview</option>
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
              <a class="inline-flex items-center gap-2 rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0]" href="/dashboard/persona">
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
