<script lang="ts">
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  type SearchItem = {
    label: string;
    href: string;
    icon: string;
    group: string;
    description: string;
    keywords: string[];
  };

  let {
    placeholder = 'Search pages, tools, or funding data...'
  }: {
    placeholder?: string;
  } = $props();

  let query = $state('');
  let isOpen = $state(false);
  let activeIndex = $state(0);
  let inputElement: HTMLInputElement;

  const searchItems: SearchItem[] = [
    {
      label: 'Overview',
      href: '/dashboard',
      icon: 'dashboard',
      group: 'Workspace',
      description: 'Return to the FundRadar workspace overview.',
      keywords: ['home', 'overview', 'workspace', 'fundradar']
    },
    {
      label: 'Grants and Contributions',
      href: '/dashboard/grants-contributions',
      icon: 'request_quote',
      group: 'Funding data',
      description: 'Open the grants and contributions dataset route.',
      keywords: ['grants', 'contributions', 'dataset', 'open canada', 'funding']
    },
    {
      label: 'Business Benefits Finder',
      href: '/dashboard/business-benefits-finder',
      icon: 'domain',
      group: 'Funding data',
      description: 'Open Business Benefits Finder programs.',
      keywords: ['business benefits finder', 'benefits', 'programs', 'ised', 'business']
    },
    {
      label: 'Analytics',
      href: '/dashboard/live-view',
      icon: 'insert_chart',
      group: 'Funding data',
      description: 'Open aggregate grants and Business Benefits Finder analytics.',
      keywords: ['analytics', 'business finder', 'business benefits', 'benefits', 'program data']
    },
    {
      label: 'Company Profile',
      href: '/dashboard/persona',
      icon: 'business_center',
      group: 'Workspace',
      description: 'Edit organization identity, jurisdiction, scale, and funding objectives.',
      keywords: ['company', 'profile', 'portfolio', 'organization', 'settings']
    },
    {
      label: 'Opportunity Matches',
      href: '/dashboard/persona/matches',
      icon: 'description',
      group: 'Workspace',
      description: 'Review ranked funding matches and saved opportunities.',
      keywords: ['matches', 'opportunities', 'applications', 'shortlist', 'ranked', 'apply']
    },
    {
      label: 'Graph View',
      href: '/dashboard/graph-view',
      icon: 'hub',
      group: 'Workspace',
      description: 'Explore company-centered opportunity matches as an interactive graph.',
      keywords: ['graph', 'network', 'nodes', 'interactive', 'matches', 'opportunities']
    },
    {
      label: 'Account Profile',
      href: '/dashboard/profile',
      icon: 'account_circle',
      group: 'Workspace',
      description: 'Review authenticated account identity and profile details.',
      keywords: ['account', 'profile', 'user', 'identity', 'authenticated', 'avatar']
    },
    {
      label: 'Settings',
      href: '/dashboard/settings',
      icon: 'settings',
      group: 'Workspace',
      description: 'Open account, profile, and sign-out controls.',
      keywords: ['settings', 'account', 'profile', 'sign out', 'logout']
    }
  ];

  const normalizedQuery = $derived(normalize(query));
  const filteredItems = $derived(getFilteredItems(normalizedQuery));
  const activeItem = $derived(filteredItems[activeIndex] ?? filteredItems[0] ?? null);

  onMount(() => {
    if (!browser) {
      return;
    }

    const handleGlobalKeydown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTypingTarget =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable;

      const isCommandK = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
      const isSlash = event.key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !isTypingTarget;

      if (!isCommandK && !isSlash) {
        return;
      }

      event.preventDefault();
      inputElement?.focus();
      isOpen = true;
    };

    window.addEventListener('keydown', handleGlobalKeydown);

    return () => {
      window.removeEventListener('keydown', handleGlobalKeydown);
    };
  });

  function normalize(value: string): string {
    return value.toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function getFilteredItems(search: string): SearchItem[] {
    if (!search) {
      return searchItems;
    }

    return searchItems.filter((item) => {
      const haystack = normalize([item.label, item.group, item.description, ...item.keywords].join(' '));
      return haystack.includes(search);
    });
  }

  function openSearch() {
    isOpen = true;
    activeIndex = 0;
  }

  function closeSearch() {
    window.setTimeout(() => {
      isOpen = false;
      activeIndex = 0;
    }, 120);
  }

  function handleInput(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    isOpen = true;
    activeIndex = 0;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      isOpen = true;
      activeIndex = filteredItems.length === 0 ? 0 : (activeIndex + 1) % filteredItems.length;
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      isOpen = true;
      activeIndex = filteredItems.length === 0 ? 0 : (activeIndex - 1 + filteredItems.length) % filteredItems.length;
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      if (activeItem) {
        void selectItem(activeItem);
      }
      return;
    }

    if (event.key === 'Escape') {
      isOpen = false;
      activeIndex = 0;
      inputElement?.blur();
    }
  }

  async function selectItem(item: SearchItem) {
    query = '';
    isOpen = false;
    activeIndex = 0;
    await goto(item.href);
  }
</script>

<div class="relative w-full max-w-[420px]">
  <span class="material-symbols-outlined pointer-events-none absolute top-1/2 left-3 z-10 -translate-y-1/2 text-[20px] text-slate-400" aria-hidden="true">search</span>
  <input
    bind:this={inputElement}
    value={query}
    class="min-h-10 w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pr-10 pl-10 font-[inherit] text-slate-900 transition focus:border-emerald-600 focus:bg-white focus:outline-none focus:ring-4 focus:ring-emerald-600/20"
    type="search"
    {placeholder}
    aria-label="Search dashboard pages"
    aria-controls="dashboard-search-results"
    autocomplete="off"
    onfocus={openSearch}
    onblur={closeSearch}
    oninput={handleInput}
    onkeydown={handleKeydown}
  />
  <span class="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 rounded border border-slate-300 px-1.5 py-0.5 text-xs leading-none font-bold text-slate-500" aria-hidden="true">/</span>

  {#if isOpen}
    <div
      class="absolute top-[calc(100%+8px)] left-0 z-80 max-h-[min(430px,calc(100vh-96px))] w-[min(560px,calc(100vw-32px))] overflow-auto rounded-[10px] border border-slate-300 bg-white p-1.5 shadow-[0_18px_45px_rgba(15,23,42,0.18)] max-sm:right-0 max-sm:w-[calc(100vw-32px)]"
      id="dashboard-search-results"
      role="listbox"
      aria-label="Dashboard search results"
    >
      {#if filteredItems.length > 0}
        {#each filteredItems as item, index (item.href)}
          <button
            class={`grid w-full cursor-pointer grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-2.5 rounded-lg border-0 bg-transparent p-2.5 text-left text-[#191c1e] hover:bg-emerald-50 max-sm:grid-cols-[32px_minmax(0,1fr)] ${index === activeIndex ? 'bg-emerald-50' : ''}`}
            type="button"
            role="option"
            aria-selected={index === activeIndex}
            onmousedown={(event) => event.preventDefault()}
            onclick={() => selectItem(item)}
          >
            <span class="material-symbols-outlined inline-flex h-8 w-8 items-center justify-center rounded-lg border border-green-200 bg-green-50 text-[20px] text-emerald-700" aria-hidden="true">{item.icon}</span>
            <span class="grid min-w-0 gap-0.5">
              <strong class="truncate text-sm font-extrabold">{item.label}</strong>
              <small class="truncate text-xs text-slate-500">{item.description}</small>
            </span>
            <span class="text-[11px] font-extrabold text-slate-500 uppercase max-sm:hidden">{item.group}</span>
          </button>
        {/each}
      {:else}
        <div class="grid gap-1 p-3.5 text-[13px] text-slate-600" role="status">
          <strong class="text-slate-900">No matching pages</strong>
          <span>Try Overview, Grants and Contributions, Business Benefits Finder, Analytics, Company Profile, Opportunity Matches, Graph View, Account Profile, or Settings.</span>
        </div>
      {/if}
    </div>
  {/if}
</div>
