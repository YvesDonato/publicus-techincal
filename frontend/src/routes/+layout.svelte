<script lang="ts">
  import { page } from '$app/state';
  import '../app.css';
  import { appName } from '$lib';

  let { children } = $props();
  const showSiteHeader = $derived(
    !['/', '/business-benefits-finder', '/dashboard', '/grants-contributions', '/live-view', '/settings'].includes(
      page.url.pathname
    ) &&
      !page.url.pathname.startsWith('/persona')
  );
</script>

{#if showSiteHeader}
  <header class="site-header">
    <a class="site-brand" href="/">{appName}</a>
    <nav class="site-nav" aria-label="Primary navigation">
      <a href="/">Home</a>
      <a href="/dashboard">Discovery</a>
      <a href="/live-view">Analytics</a>
      <a href="/persona">Company Profile</a>
      <a href="/persona/matches">Opportunity Matches</a>
    </nav>
  </header>
{/if}

{@render children()}
