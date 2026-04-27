<script lang="ts">
  import type { ActionData, PageData } from './$types';

  type AuthResult = {
    error?: string;
    values?: {
      email?: string;
    };
  };

  let {
    data,
    form
  }: {
    data: PageData;
    form?: ActionData;
  } = $props();

  let showPassword = $state(false);

  const result = $derived((form ?? {}) as AuthResult);
  const email = $derived(result.values?.email ?? '');
  const signupHref = $derived(`/signup?next=${encodeURIComponent(data.next)}`);
</script>

<svelte:head>
  <title>Sign In - FundRadar</title>
  <meta name="description" content="Sign in to the FundRadar funding workspace." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Public+Sans:wght@600;700;900&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="flex min-h-screen bg-white font-[Inter,ui-sans-serif,system-ui,sans-serif] text-[#191c1e] antialiased selection:bg-[#6cf8bb] selection:text-[#00714d]">
  <section class="relative hidden w-1/2 overflow-hidden bg-[#131b2e] lg:flex" aria-label="FundRadar institutional funding">
    <img
      class="absolute inset-0 h-full w-full object-cover opacity-50 mix-blend-overlay"
      src="https://lh3.googleusercontent.com/aida-public/AB6AXuBz9e60tWbNMdnAlcYVUv4EF_JpudIqEtkQy2eqpUDQWcsRY4zdT_y2oHW3tTpVB_o0IcLh02Z8kNbhzzZfwqwhF-ygJjFYqCCOQUil-pf_K6dIMQVMr1IfkuX0E0ppHbo8iQoM4Sr2T6E5OgfdIjie4NZ5vwND8IJIvosC4M8Ckv8F2b4l7sNAXnZi2LAafUc3CXgZt0OIFw7bIYxJjt4Q-scgPFeRLJAYsUkeKQH-6Rx-jzoQl9gkwZGedB_kttj96sAv4hYslomx"
      alt=""
    />
    <div class="absolute inset-0 bg-gradient-to-t from-[#131b2e] via-[#131b2e]/80 to-transparent"></div>

    <div class="relative z-10 mt-auto flex w-full max-w-2xl flex-col justify-end p-12 text-white">
      <a class="mb-6 flex h-12 w-12 items-center justify-center rounded bg-emerald-700 text-white no-underline" href="/" aria-label="FundRadar home">
        <span class="material-symbols-outlined text-[28px]" style="font-variation-settings: 'FILL' 1;">radar</span>
      </a>
      <blockquote class="m-0 mb-4 font-[Public_Sans] text-4xl font-semibold leading-tight text-balance text-white">
        Navigating capital acquisition with institutional precision.
      </blockquote>
      <p class="m-0 max-w-lg text-lg leading-8 text-[#bec6e0]">
        FundRadar provides Canadian entrepreneurs with the definitive platform for discovering and securing non-dilutive funding.
      </p>
    </div>
  </section>

  <section class="flex h-screen w-full flex-col overflow-y-auto p-6 lg:w-1/2 lg:p-12" aria-labelledby="signin-heading">
    <div class="mb-12 flex items-center lg:hidden">
      <a class="flex items-center gap-2 text-[#191c1e] no-underline" href="/" aria-label="FundRadar home">
        <span class="flex h-8 w-8 items-center justify-center rounded bg-emerald-700 text-white">
          <span class="material-symbols-outlined text-[20px]" style="font-variation-settings: 'FILL' 1;">radar</span>
        </span>
        <span class="font-[Public_Sans] text-2xl font-semibold">FundRadar</span>
      </a>
    </div>

    <main class="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center">
      <div class="mb-12">
        <h1 id="signin-heading" class="m-0 mb-1 font-[Public_Sans] text-5xl font-bold leading-tight text-[#191c1e]">
          Sign In
        </h1>
        <p class="m-0 text-lg leading-8 text-[#45464d]">Enter your credentials to access the platform.</p>
      </div>

      {#if result.error}
        <p class="mb-6 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700" role="alert">
          {result.error}
        </p>
      {/if}

      <form class="space-y-6" method="POST">
        <input type="hidden" name="next" value={data.next} />

        <div>
          <label class="mb-2 block text-xs font-semibold uppercase leading-none tracking-normal text-[#191c1e]" for="email">
            Email Address
          </label>
          <div class="relative">
            <span class="material-symbols-outlined pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#45464d]">mail</span>
            <input
              class="w-full rounded border border-[#76777d] bg-white py-[14px] pl-11 pr-4 text-base leading-6 text-[#191c1e] shadow-sm transition placeholder:text-[#c6c6cd] focus:border-2 focus:border-[#131b2e] focus:px-[15px] focus:py-[13px] focus:pl-[43px] focus:outline-none"
              autocomplete="email"
              id="email"
              name="email"
              placeholder="name@company.com"
              type="email"
              value={email}
              required
            />
          </div>
        </div>

        <div>
          <div class="mb-2 flex items-center justify-between gap-4">
            <label class="block text-xs font-semibold uppercase leading-none tracking-normal text-[#191c1e]" for="password">
              Password
            </label>
            <a class="text-sm font-semibold leading-5 text-emerald-700 no-underline transition hover:text-emerald-900" href="/login">
              Forgot password?
            </a>
          </div>
          <div class="relative">
            <span class="material-symbols-outlined pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#45464d]">lock</span>
            <input
              class="w-full rounded border border-[#76777d] bg-white py-[14px] pl-11 pr-11 text-base leading-6 text-[#191c1e] shadow-sm transition placeholder:text-[#c6c6cd] focus:border-2 focus:border-[#131b2e] focus:py-[13px] focus:pl-[43px] focus:pr-[43px] focus:outline-none"
              autocomplete="current-password"
              id="password"
              name="password"
              placeholder="••••••••"
              type={showPassword ? 'text' : 'password'}
              required
            />
            <button
              class="absolute right-4 top-1/2 -translate-y-1/2 text-[#45464d] transition hover:text-[#191c1e] focus:outline-none"
              type="button"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onclick={() => {
                showPassword = !showPassword;
              }}
            >
              <span class="material-symbols-outlined">{showPassword ? 'visibility_off' : 'visibility'}</span>
            </button>
          </div>
        </div>

        <button
          class="mt-4 flex w-full items-center justify-center gap-1 rounded bg-emerald-700 py-4 text-sm font-semibold leading-none text-white shadow-sm transition hover:bg-emerald-900 active:scale-[0.98]"
          type="submit"
        >
          <span>Sign In</span>
          <span class="material-symbols-outlined text-[20px]">arrow_forward</span>
        </button>
      </form>

      <div class="mt-12 text-center">
        <p class="m-0 text-base leading-6 text-[#45464d]">
          Don't have an account?
          <a class="font-semibold text-emerald-700 no-underline transition hover:text-emerald-900" href={signupHref}>Request Access</a>
        </p>
      </div>
    </main>

    <footer class="mt-auto flex flex-wrap items-center justify-center gap-4 border-t border-[#e0e3e5] pt-12 sm:justify-between">
      <span class="text-sm leading-5 text-[#45464d]">© 2026 FundRadar</span>
      <div class="flex gap-6">
        <a class="text-sm leading-5 text-[#45464d] no-underline transition hover:text-[#191c1e]" href="/">Privacy Policy</a>
        <a class="text-sm leading-5 text-[#45464d] no-underline transition hover:text-[#191c1e]" href="/">Terms of Service</a>
        <a class="text-sm leading-5 text-[#45464d] no-underline transition hover:text-[#191c1e]" href="/">Contact Support</a>
      </div>
    </footer>
  </section>
</div>
