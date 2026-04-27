<script lang="ts">
  const heroImageUrl =
    'https://lh3.googleusercontent.com/aida-public/AB6AXuBcBVuPcgYNmKqVqxs-gdunb5xUGjHnKM-9iZbHUnteUi-NE5-57dW7NtovKD2C51ZUG5RCh78Aa2xuG-nUVfvD3BNj3PBqiixQMz57y4QK7It_xjaU5TV_pxT4SOEsiP3Mmquxg_usN5DJHKz3WMG2TAc8h_dKUc6eFd4nBys3VEC51R5TR9EgfcoFWGWlgcorQM9m1cAXHZmA0IR1hAd0DN8scuxjzCMZs2amb--_1NfynwtdAcBMn3WSyqzLO_eGKeicK5QY0R4y';

  const metrics = [
    { label: 'Funding Matched', value: '$50M+' },
    { label: 'Active Programs', value: '200+' }
  ];

  const features = [
    {
      icon: 'database',
      title: 'Centralized Discovery',
      copy: 'Stop digging through government portals. Access grants, loans, tax credits, and support programs in one place.'
    },
    {
      icon: 'my_location',
      title: 'Precision Matching',
      copy: 'Create a company profile once and let FundRadar surface the programs that fit your eligibility signals.'
    },
    {
      icon: 'trending_up',
      title: 'Data-Driven Ranking',
      copy: 'Prioritize your work with relevance scores based on your business goals, industry, location, and funding needs.'
    }
  ];

  const steps = [
    {
      title: 'Build your Profile',
      copy: 'Tell us about your business, industry, and goals to set the baseline for the matching engine.'
    },
    {
      title: 'Discover Matches',
      copy: 'See ranked opportunities tailored to your eligibility criteria and the records available in FundRadar.'
    },
    {
      title: 'Apply with Confidence',
      copy: 'Review requirements, shortlist realistic programs, and focus effort on applications worth pursuing.'
    }
  ];
</script>

<svelte:head>
  <title>FundRadar - Institutional Growth</title>
  <meta
    name="description"
    content="FundRadar helps Canadian businesses discover, match, and rank government grants and support programs."
  />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@600;700;900&family=Inter:wght@400;600;700;800;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex min-h-screen flex-col bg-[#f7f9fb] font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e] antialiased">
  <header class="sticky top-0 z-50 border-b border-[#e0e3e5] bg-white px-4 py-3 md:px-10">
    <div class="mx-auto flex max-w-[1280px] items-center justify-between gap-5">
      <a class="flex min-w-0 items-center gap-3 text-[#191c1e] no-underline" href="/" aria-label="FundRadar home">
        <span
          class="material-symbols-outlined flex size-8 shrink-0 items-center justify-center text-[26px] text-emerald-700"
          style="font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;"
          aria-hidden="true"
        >
          radar
        </span>
        <span class="truncate font-[Public_Sans] text-lg font-black leading-tight tracking-normal">FundRadar</span>
      </a>

      <nav class="hidden items-center gap-9 md:flex" aria-label="Primary navigation">
        <a class="text-sm font-semibold text-[#45464d] no-underline transition hover:text-[#191c1e]" href="#features">Features</a>
        <a class="text-sm font-semibold text-[#45464d] no-underline transition hover:text-[#191c1e]" href="#how-it-works">How it Works</a>
        <a class="text-sm font-semibold text-[#45464d] no-underline transition hover:text-[#191c1e]" href="#pricing">Pricing</a>
      </nav>

      <div class="flex shrink-0 gap-2">
        <a
          class="flex h-10 min-w-20 items-center justify-center rounded bg-emerald-700 px-4 text-sm font-semibold text-white no-underline transition hover:bg-emerald-800"
          href="/signup?next=%2Fdashboard%2Fpersona"
        >
          Get Started
        </a>
        <a
          class="flex h-10 min-w-20 items-center justify-center rounded border border-[#c6c6cd] bg-[#e6e8ea] px-4 text-sm font-semibold text-[#191c1e] no-underline transition hover:bg-[#e0e3e5]"
          href="/login"
        >
          Log In
        </a>
      </div>
    </div>
  </header>

  <main class="flex w-full flex-1 flex-col items-center">
    <section class="mx-auto w-full max-w-[1280px] px-4 py-10 md:px-6 md:py-12">
      <div
        class="relative flex min-h-[500px] items-center justify-center overflow-hidden rounded-xl bg-cover bg-center px-6 py-12 text-center md:min-h-[560px] md:px-16"
        style={`background-image: linear-gradient(rgba(19, 27, 46, 0.70), rgba(19, 27, 46, 0.82)), url('${heroImageUrl}');`}
        aria-label="Modern high-rise office building complex in Toronto financial district with soft twilight lighting and glass reflections"
      >
        <div class="relative z-10 flex max-w-3xl flex-col items-center gap-5">
          <h1 class="m-0 font-[Public_Sans] text-4xl font-black leading-tight tracking-normal text-white md:text-5xl">
            Unlock the Funding Your Business Deserves.
          </h1>
          <p class="m-0 max-w-2xl text-lg leading-8 text-[#dae2fd] md:text-xl">
            The intelligent discovery tool for Canadian grants and government support. Find, match, and rank the best
            opportunities for your growth in minutes.
          </p>
          <a
            class="mt-3 flex h-12 items-center justify-center rounded-lg bg-emerald-600 px-8 text-sm font-black text-white no-underline shadow-lg transition hover:bg-emerald-700"
            href="/signup?next=%2Fdashboard%2Fpersona"
          >
            Get Started for Free
          </a>
        </div>
      </div>
    </section>

    <section class="mx-auto w-full max-w-[1280px] px-4 pb-12 md:px-6" aria-label="FundRadar statistics">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        {#each metrics as metric (metric.label)}
          <article class="rounded-lg border border-[#e0e3e5] bg-[#eceef0] p-6 text-center shadow-sm">
            <p class="m-0 text-sm font-black uppercase tracking-normal text-[#45464d]">{metric.label}</p>
            <p class="m-0 mt-2 font-[Public_Sans] text-4xl font-black leading-tight text-black">{metric.value}</p>
          </article>
        {/each}
      </div>
    </section>

    <section id="features" class="mx-auto mb-12 w-full max-w-[1280px] px-4 py-12 md:px-6">
      <div class="rounded-xl bg-[#f2f4f6] px-4 py-12 md:px-8">
        <div class="mx-auto flex max-w-2xl flex-col gap-4 text-center">
          <h2 class="m-0 font-[Public_Sans] text-4xl font-black leading-tight text-black">Why FundRadar?</h2>
          <p class="m-0 text-lg leading-8 text-[#45464d]">
            We make finding government funding simple, efficient, and targeted to your specific business needs.
          </p>
        </div>

        <div class="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
          {#each features as feature (feature.title)}
            <article class="flex flex-col gap-4 rounded-xl border border-[#c6c6cd] bg-white p-6 shadow-sm transition hover:shadow-md">
              <div class="mb-2 flex size-12 items-center justify-center rounded-lg bg-[#6ffbbe] text-emerald-900">
                <span class="material-symbols-outlined text-2xl">{feature.icon}</span>
              </div>
              <div class="flex flex-col gap-2">
                <h3 class="m-0 font-[Public_Sans] text-xl font-black leading-tight text-black">{feature.title}</h3>
                <p class="m-0 text-base leading-7 text-[#45464d]">{feature.copy}</p>
              </div>
            </article>
          {/each}
        </div>
      </div>
    </section>

    <section id="how-it-works" class="mx-auto mb-12 w-full max-w-[1280px] px-4 py-12 md:px-6">
      <div class="mx-auto flex max-w-2xl flex-col gap-4 text-center">
        <h2 class="m-0 font-[Public_Sans] text-4xl font-black leading-tight text-black">How it Works</h2>
        <p class="m-0 text-lg leading-8 text-[#45464d]">
          A streamlined process designed to get you from discovery to application without the overhead.
        </p>
      </div>

      <div class="relative mt-10 grid grid-cols-1 gap-8 md:grid-cols-3">
        <div class="absolute left-0 top-8 z-0 hidden h-px w-full bg-[#e0e3e5] md:block"></div>

        {#each steps as step, index (step.title)}
          <article class="relative z-10 flex flex-col items-center gap-4 bg-[#f7f9fb] text-center md:px-4">
            <div
              class={`flex size-16 items-center justify-center rounded-full border-4 border-[#f7f9fb] font-[Public_Sans] text-2xl font-black text-white shadow-md ${
                index === 2 ? 'bg-emerald-700' : 'bg-[#131b2e]'
              }`}
            >
              {index + 1}
            </div>
            <h3 class="m-0 font-[Public_Sans] text-xl font-black text-black">{step.title}</h3>
            <p class="m-0 text-base leading-7 text-[#45464d]">{step.copy}</p>
          </article>
        {/each}
      </div>

      <div class="mt-12 flex justify-center">
        <a
          class="flex h-12 items-center justify-center rounded-lg bg-emerald-700 px-8 text-sm font-black text-white no-underline shadow-sm transition hover:bg-emerald-800"
          href="/signup?next=%2Fdashboard%2Fpersona"
        >
          Start Building Your Profile
        </a>
      </div>
    </section>

    <section id="pricing" class="mx-auto mb-16 w-full max-w-[1280px] px-4 md:px-6">
      <div class="rounded-xl border border-[#c6c6cd] bg-white p-6 shadow-sm md:p-8">
        <div class="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <p class="m-0 mb-2 text-xs font-black uppercase tracking-normal text-emerald-700">Pricing</p>
            <h2 class="m-0 font-[Public_Sans] text-3xl font-black leading-tight text-[#191c1e]">Start with the workspace you already have.</h2>
            <p class="m-0 mt-3 max-w-3xl text-base leading-7 text-[#45464d]">
              Use FundRadar to create your profile, browse grants, and review ranked matches. Account-based persistence is powered by Supabase.
            </p>
          </div>
          <a
            class="flex h-12 items-center justify-center rounded-lg border border-[#c6c6cd] px-6 text-sm font-black text-[#191c1e] no-underline transition hover:bg-[#eceef0]"
            href="/login?next=%2Fdashboard"
          >
            View Dashboard
          </a>
        </div>
      </div>
    </section>
  </main>

  <footer class="mt-auto w-full border-t border-[#e0e3e5] bg-white py-8">
    <div class="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-4 px-4 md:flex-row md:px-6">
      <a class="flex items-center gap-2 text-[#191c1e] no-underline" href="/" aria-label="FundRadar home">
        <span
          class="material-symbols-outlined flex size-6 items-center justify-center text-[22px] text-emerald-700"
          style="font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;"
          aria-hidden="true"
        >
          radar
        </span>
        <span class="font-[Public_Sans] text-sm font-black">FundRadar</span>
      </a>
      <p class="m-0 text-sm text-[#45464d]">2026 FundRadar. All rights reserved.</p>
    </div>
  </footer>
</div>
