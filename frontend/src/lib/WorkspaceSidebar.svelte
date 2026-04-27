<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';

  type ActiveSection =
    | 'overview'
    | 'discovery'
    | 'grants'
    | 'benefits'
    | 'analytics'
    | 'profile'
    | 'matches'
    | 'account'
    | 'settings';

  type NavItem = {
    id: ActiveSection;
    href: string;
    icon: string;
    label: string;
  };

  let { active = 'overview' }: { active?: ActiveSection } = $props();

  const SIDEBAR_STORAGE_KEY = 'fundradar.sidebarCollapsed';
  const SIDEBAR_WIDTH_STORAGE_KEY = 'fundradar.sidebarWidth';
  const COLLAPSED_WIDTH = 80;
  const DEFAULT_WIDTH = 256;
  const MIN_WIDTH = 220;
  const MAX_WIDTH = 380;

  let collapsed = $state(false);
  let sidebarWidth = $state(DEFAULT_WIDTH);
  let resizing = $state(false);
  let removeResizeListeners: (() => void) | null = null;

  const navItems: NavItem[] = [
    { id: 'overview', href: '/dashboard', icon: 'dashboard', label: 'Overview' },
    { id: 'discovery', href: '/dashboard/discovery', icon: 'explore', label: 'Discovery' },
    { id: 'grants', href: '/dashboard/grants-contributions', icon: 'request_quote', label: 'Grants and Contributions' },
    { id: 'benefits', href: '/dashboard/business-benefits-finder', icon: 'domain', label: 'Business Benefits Finder' },
    { id: 'analytics', href: '/dashboard/live-view', icon: 'insert_chart', label: 'Analytics' },
    { id: 'profile', href: '/dashboard/persona', icon: 'business_center', label: 'Company Profile' },
    { id: 'matches', href: '/dashboard/persona/matches', icon: 'description', label: 'Opportunity Matches' },
    { id: 'account', href: '/dashboard/profile', icon: 'account_circle', label: 'Account Profile' },
    { id: 'settings', href: '/dashboard/settings', icon: 'settings', label: 'Settings' }
  ];

  onMount(() => {
    if (!browser) return;

    collapsed = localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
    sidebarWidth = clampSidebarWidth(Number(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY)) || DEFAULT_WIDTH);

    return () => {
      stopResize();
    };
  });

  function toggleCollapsed(): void {
    collapsed = !collapsed;

    if (browser) {
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(collapsed));
    }
  }

  function clampSidebarWidth(width: number): number {
    return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
  }

  function persistSidebarWidth(): void {
    if (browser) {
      localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth));
    }
  }

  function startResize(event: PointerEvent): void {
    if (collapsed || !browser) {
      return;
    }

    event.preventDefault();
    resizing = true;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';

    const handlePointerMove = (moveEvent: PointerEvent) => {
      sidebarWidth = clampSidebarWidth(moveEvent.clientX);
    };
    const handlePointerUp = () => {
      persistSidebarWidth();
      stopResize();
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp, { once: true });

    removeResizeListeners = () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }

  function resizeWithKeyboard(event: KeyboardEvent): void {
    if (collapsed) {
      return;
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      sidebarWidth = clampSidebarWidth(sidebarWidth - 16);
      persistSidebarWidth();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      sidebarWidth = clampSidebarWidth(sidebarWidth + 16);
      persistSidebarWidth();
    } else if (event.key === 'Home') {
      event.preventDefault();
      sidebarWidth = MIN_WIDTH;
      persistSidebarWidth();
    } else if (event.key === 'End') {
      event.preventDefault();
      sidebarWidth = MAX_WIDTH;
      persistSidebarWidth();
    }
  }

  function stopResize(): void {
    removeResizeListeners?.();
    removeResizeListeners = null;
    resizing = false;

    if (browser) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  }

  function navClass(id: ActiveSection): string {
    const baseClass = id === active
      ? 'flex items-center gap-3 rounded-md bg-emerald-50 px-3 py-2.5 text-emerald-700'
      : 'flex items-center gap-3 rounded-md px-3 py-2.5 text-slate-600 transition hover:bg-slate-200 hover:text-slate-900';

    return `${baseClass} ${collapsed ? 'justify-center px-2' : ''}`;
  }

  function iconClass(id: ActiveSection): string {
    return id === active ? 'material-symbols-outlined text-emerald-600' : 'material-symbols-outlined';
  }
</script>

<nav
  class={`relative hidden shrink-0 flex-col border-r border-slate-200 bg-slate-50 md:flex ${resizing ? '' : 'transition-[width] duration-200'}`}
  style={`width: ${collapsed ? COLLAPSED_WIDTH : sidebarWidth}px;`}
  aria-label="FundRadar workspace navigation"
>
  <div class="flex h-full flex-col gap-2 p-4">
    <div class={`mb-4 flex items-center gap-2 ${collapsed ? 'flex-col justify-center' : 'justify-between'}`}>
      <a
        class={`flex min-w-0 items-center gap-2 rounded-md text-left no-underline transition hover:bg-slate-100 ${collapsed ? 'h-9 w-9 justify-center p-0' : 'px-2 py-3'}`}
        href="/"
        aria-label="FundRadar home"
        title={collapsed ? 'FundRadar home' : undefined}
      >
        <span
          class="material-symbols-outlined flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[28px] text-emerald-700"
          style="font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;"
          aria-hidden="true"
        >
          radar
        </span>
        {#if !collapsed}
          <div class="min-w-0">
            <h1 class="m-0 truncate font-[Public_Sans] text-lg font-black leading-none tracking-normal text-slate-900">FundRadar</h1>
            <span class="block truncate text-[11px] leading-4 text-slate-500">Enterprise Funding</span>
          </div>
        {/if}
      </a>

      <button
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-slate-600 transition hover:bg-slate-200 hover:text-slate-900"
        type="button"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-expanded={!collapsed}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        onclick={toggleCollapsed}
      >
        <span class="material-symbols-outlined text-[20px]">
          {collapsed ? 'keyboard_double_arrow_right' : 'keyboard_double_arrow_left'}
        </span>
      </button>
    </div>

    <div class="flex flex-1 flex-col gap-1">
      {#each navItems as item (item.id)}
        <a
          class={navClass(item.id)}
          href={item.href}
          aria-current={item.id === active ? 'page' : undefined}
          aria-label={collapsed ? item.label : undefined}
          title={collapsed ? item.label : undefined}
        >
          <span class={iconClass(item.id)}>{item.icon}</span>
          {#if !collapsed}
            <span class="truncate">{item.label}</span>
          {/if}
        </a>
      {/each}
    </div>

    <div class={`my-4 ${collapsed ? 'px-0' : 'px-2'}`}>
      <a
        class={`flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 text-center font-semibold text-white no-underline transition hover:bg-emerald-700 ${collapsed ? 'h-10 px-0' : 'py-2.5'}`}
        href="/dashboard/persona/matches"
        aria-label={collapsed ? 'Find Funding' : undefined}
        title={collapsed ? 'Find Funding' : undefined}
      >
        {#if collapsed}
          <span class="material-symbols-outlined text-[20px]">search</span>
        {:else}
          Find Funding
        {/if}
      </a>
    </div>

    <div class="flex flex-col gap-1 border-t border-slate-200 pt-4">
      <a
        class={`flex items-center gap-3 rounded-md px-3 py-2 text-slate-600 no-underline transition hover:bg-slate-200 hover:text-slate-900 ${collapsed ? 'justify-center px-2' : ''}`}
        href="/"
        aria-label={collapsed ? 'Support' : undefined}
        title={collapsed ? 'Support' : undefined}
      >
        <span class="material-symbols-outlined">contact_support</span>
        {#if !collapsed}
          <span>Support</span>
        {/if}
      </a>
      <form method="POST" action="/logout">
        <button
          class={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-slate-600 no-underline transition hover:bg-slate-200 hover:text-slate-900 ${collapsed ? 'justify-center px-2' : ''}`}
          type="submit"
          aria-label={collapsed ? 'Log Out' : undefined}
          title={collapsed ? 'Log Out' : undefined}
        >
          <span class="material-symbols-outlined">logout</span>
          {#if !collapsed}
            <span>Log Out</span>
          {/if}
        </button>
      </form>
    </div>
  </div>

  {#if !collapsed}
    <button
      class="group absolute -right-1 top-0 h-full w-2 cursor-ew-resize rounded-none border-0 bg-transparent p-0 outline-none transition hover:bg-emerald-500/20 focus-visible:bg-emerald-500/20 focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-0"
      type="button"
      aria-label={`Resize sidebar, ${sidebarWidth} pixels wide`}
      title="Drag to resize sidebar"
      onpointerdown={startResize}
      onkeydown={resizeWithKeyboard}
    >
      <span class="mx-auto block h-full w-px bg-transparent transition group-hover:bg-emerald-600" aria-hidden="true"></span>
    </button>
  {/if}
</nav>
