<script lang="ts">
  const overviewStats = [
    {
      label: 'Programs indexed',
      value: '200+',
      detail: 'Grants, loans, tax credits, and wage subsidies'
    },
    {
      label: 'Funding surfaced',
      value: '$50M+',
      detail: 'Matched public support tracked in one workspace'
    },
    {
      label: 'Profile stages',
      value: '3',
      detail: 'Company profile, ranked matches, application review'
    }
  ];

  const platformCards = [
    {
      icon: 'travel_explore',
      title: 'Centralized Discovery',
      copy: 'Browse Canadian government funding programs without moving between agency portals.'
    },
    {
      icon: 'rule_settings',
      title: 'Precision Matching',
      copy: 'Use company profile signals to identify programs that are realistic for your team to pursue.'
    },
    {
      icon: 'leaderboard',
      title: 'Ranked Pipeline',
      copy: 'Compare opportunities by fit, funding type, amount, sector, and application readiness.'
    }
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Build the company profile',
      detail: 'Capture sector, stage, location, team size, and funding goals before searching.'
    },
    {
      step: '02',
      title: 'Review eligible programs',
      detail: 'Move from a broad dataset into ranked grants, credits, subsidies, and support programs.'
    },
    {
      step: '03',
      title: 'Shortlist next actions',
      detail: 'Save promising records and move the strongest opportunities into application prep.'
    }
  ];

  const coverageItems = [
    { label: 'Grants', status: 'Open intake', tone: 'emerald' },
    { label: 'Tax credits', status: 'Profile dependent', tone: 'slate' },
    { label: 'Loans', status: 'Repayable', tone: 'slate' },
    { label: 'Wage subsidies', status: 'Hiring signals', tone: 'slate' }
  ];
</script>

<svelte:head>
  <title>FundRadar Overview</title>
  <meta
    name="description"
    content="FundRadar helps Canadian businesses discover, match, and rank government funding opportunities."
  />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="fundradar-dashboard flex h-screen overflow-hidden bg-[#f7f9fb] text-[#191c1e]">
  <nav class="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50 md:flex" aria-label="Workspace navigation">
    <div class="flex h-full flex-col gap-2 p-4">
      <div class="mb-4 flex items-center gap-3 px-2 py-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 font-bold text-white">FR</div>
        <div>
          <h1 class="m-0 font-[Public_Sans] text-xl font-black leading-none tracking-normal text-slate-900">FundRadar</h1>
          <span class="text-xs text-slate-500">Enterprise Funding</span>
        </div>
      </div>

      <div class="flex flex-1 flex-col gap-1">
        <a class="flex items-center gap-3 rounded-md bg-emerald-50 px-3 py-2.5 text-emerald-700" href="/" aria-current="page">
          <span class="material-symbols-outlined text-emerald-600">dashboard</span>
          <span>Overview</span>
        </a>
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
        <a class="flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 hover:bg-slate-200 hover:text-slate-900" href="/settings">
          <span class="material-symbols-outlined">settings</span>
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
            placeholder="Search programs, sectors, or agencies..."
            type="search"
          />
        </div>
        <span class="block text-lg font-bold text-slate-900 md:hidden">FundRadar</span>
      </div>

      <div class="ml-4 flex items-center gap-2 md:gap-4">
        <a class="hidden rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#191c1e] transition hover:bg-[#eceef0] sm:inline-flex" href="/dashboard">
          Open Grants
        </a>
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
            <p class="m-0 mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">Workspace Overview</p>
            <h2 class="m-0 mb-2 font-[Public_Sans] text-4xl font-semibold leading-tight tracking-normal text-[#191c1e]">
              Funding intelligence for Canadian growth teams
            </h2>
            <p class="m-0 max-w-3xl text-base leading-6 text-[#45464d]">
              FundRadar brings funding discovery, eligibility matching, and application prioritization into a single
              operating view.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800" href="/persona">
              Build Profile
            </a>
            <a class="rounded-lg border border-[#c6c6cd] px-4 py-2 text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0]" href="/dashboard">
              Browse Grants
            </a>
          </div>
        </div>

        <section class="grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="FundRadar platform statistics">
          {#each overviewStats as stat (stat.label)}
            <article class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
              <p class="m-0 mb-3 text-xs font-semibold uppercase tracking-normal text-[#45464d]">{stat.label}</p>
              <strong class="mb-2 block font-[Public_Sans] text-4xl font-semibold leading-tight text-[#191c1e]">{stat.value}</strong>
              <p class="m-0 text-sm leading-6 text-[#45464d]">{stat.detail}</p>
            </article>
          {/each}
        </section>

        <div class="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
          <section class="flex flex-col gap-6 lg:col-span-8" aria-labelledby="platform-heading">
            <article class="overflow-hidden rounded-xl border border-[#c6c6cd] bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
              <div class="flex flex-col gap-6 bg-[#131b2e] p-6 md:flex-row md:items-end md:justify-between">
                <div>
                  <span class="mb-3 inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-white">
                    <span class="material-symbols-outlined text-[14px]">radar</span>
                    Overview
                  </span>
                  <h3 id="platform-heading" class="m-0 mb-2 font-[Public_Sans] text-3xl font-semibold leading-tight text-[#dae2fd]">
                    Replace scattered program research with a managed funding pipeline.
                  </h3>
                  <p class="m-0 max-w-2xl text-sm leading-6 text-[#dae2fd]/80">
                    Concise status, direct entry points, and grounded workflow context help teams move from discovery
                    into application prep.
                  </p>
                </div>
                <a class="shrink-0 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700" href="/dashboard">
                  View Grants
                </a>
              </div>

              <div class="grid grid-cols-1 gap-px bg-[#c6c6cd] md:grid-cols-3">
                {#each platformCards as card (card.title)}
                  <div class="bg-white p-5">
                    <div class="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                      <span class="material-symbols-outlined">{card.icon}</span>
                    </div>
                    <h4 class="m-0 mb-2 text-lg font-semibold leading-snug text-[#191c1e]">{card.title}</h4>
                    <p class="m-0 text-sm leading-6 text-[#45464d]">{card.copy}</p>
                  </div>
                {/each}
              </div>
            </article>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="workflow-heading">
              <div class="mb-5 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <div>
                  <h3 id="workflow-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Recommended Workflow</h3>
                  <p class="m-0 mt-1 text-sm text-[#45464d]">A dashboard-first path from overview to application prep.</p>
                </div>
                <span class="material-symbols-outlined text-emerald-700">account_tree</span>
              </div>

              <div class="grid gap-4">
                {#each workflowSteps as item (item.step)}
                  <article class="grid gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-[4rem_1fr_auto] md:items-center">
                    <span class="font-[Public_Sans] text-2xl font-semibold text-emerald-700">{item.step}</span>
                    <div>
                      <h4 class="m-0 mb-1 text-base font-semibold text-[#191c1e]">{item.title}</h4>
                      <p class="m-0 text-sm leading-6 text-[#45464d]">{item.detail}</p>
                    </div>
                    <span class="material-symbols-outlined hidden text-slate-400 md:block">chevron_right</span>
                  </article>
                {/each}
              </div>
            </section>
          </section>

          <aside class="flex flex-col gap-6 lg:sticky lg:top-4 lg:col-span-4">
            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="coverage-heading">
              <div class="mb-4 flex items-center justify-between border-b border-[#c6c6cd] pb-3">
                <h3 id="coverage-heading" class="m-0 text-sm font-semibold text-[#191c1e]">Funding Coverage</h3>
                <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-normal text-emerald-700">Live</span>
              </div>

              <div class="grid gap-3">
                {#each coverageItems as item (item.label)}
                  <div class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
                    <div class="flex items-center gap-3">
                      <span
                        class={`h-2.5 w-2.5 rounded-full ${item.tone === 'emerald' ? 'bg-emerald-600' : 'bg-slate-400'}`}
                        aria-hidden="true"
                      ></span>
                      <span class="text-sm font-semibold text-[#191c1e]">{item.label}</span>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-normal text-[#45464d]">{item.status}</span>
                  </div>
                {/each}
              </div>
            </section>

            <section class="rounded-xl border border-[#c6c6cd] bg-white p-5 shadow-[0_4px_20px_rgba(0,0,0,0.03)]" aria-labelledby="next-heading">
              <div class="mb-4 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#131b2e] text-[#dae2fd]">
                  <span class="material-symbols-outlined">task_alt</span>
                </div>
                <div>
                  <h3 id="next-heading" class="m-0 text-base font-semibold text-[#191c1e]">Next best action</h3>
                  <p class="m-0 text-sm text-[#45464d]">Create or update your profile before ranking matches.</p>
                </div>
              </div>
              <a class="mb-3 block rounded-lg bg-emerald-700 px-4 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-emerald-800" href="/persona">
                Continue to Profile
              </a>
              <a class="block rounded-lg border border-[#c6c6cd] px-4 py-2.5 text-center text-sm font-semibold text-[#0b1c30] transition hover:bg-[#eceef0]" href="/live-view">
                Open Analytics
              </a>
            </section>
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
