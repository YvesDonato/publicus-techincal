<script module lang="ts">
  import type { LinkObject, NodeObject } from 'force-graph';

  export type OpportunityForceNode = NodeObject & {
    id: string;
    label: string;
    kind: 'company' | 'opportunity';
    score: number;
    color: string;
    sponsor?: string;
    fundingLabel?: string;
    deadlineLabel?: string;
    statusLabel?: string;
    reasons?: string[];
    saved?: boolean;
  };

  export type OpportunityForceLink = LinkObject<OpportunityForceNode> & {
    source: string | OpportunityForceNode;
    target: string | OpportunityForceNode;
    similarity: number;
    distance: number;
  };
</script>

<script lang="ts">
  import { onMount } from 'svelte';
  import type ForceGraph from 'force-graph';
  import type { GraphData } from 'force-graph';

  let {
    nodes = [],
    links = [],
    selectedId = null,
    fill = false,
    onSelect
  }: {
    nodes?: OpportunityForceNode[];
    links?: OpportunityForceLink[];
    selectedId?: string | null;
    fill?: boolean;
    onSelect?: (id: string | null) => void;
  } = $props();

  let containerElement: HTMLDivElement;
  let graph: ForceGraph<OpportunityForceNode, OpportunityForceLink> | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let graphReady = $state(false);
  let hoveredNodeId = $state<string | null>(null);
  let recenteringRoot = false;
  let nodeDragActive = false;

  const ROOT_NODE_ID = 'company';
  const ROOT_ZOOM = 1.15;
  const graphData = $derived(cloneGraphData(nodes, links));

  onMount(() => {
    let disposed = false;

    void initializeGraph(() => disposed);

    return () => {
      disposed = true;
      graphReady = false;
      resizeObserver?.disconnect();
      resizeObserver = null;
      graph?.pauseAnimation();
      graph?._destructor();
      graph = null;
    };
  });

  async function initializeGraph(isDisposed: () => boolean) {
    const ForceGraphConstructor = (await import('force-graph')).default;
    if (isDisposed()) {
      return;
    }

    graph = new ForceGraphConstructor<OpportunityForceNode, OpportunityForceLink>(containerElement)
      .backgroundColor('#f8fafc')
      .nodeId('id')
      .nodeVal((node) => (node.kind === 'company' ? 24 : Math.max(8, node.score / 5)))
      .nodeLabel((node) => getNodeTooltip(node))
      .nodeCanvasObject((node, context, scale) => drawNode(node, context, scale))
      .nodePointerAreaPaint((node, color, context) => paintNodePointerArea(node, color, context))
      .linkLabel((link) => `Match strength: ${Math.round(link.similarity * 100)}%`)
      .linkColor((link) => getLinkColor(link))
      .linkWidth((link) => getLinkWidth(link))
      .linkDirectionalParticles((link) => (isSelectedLink(link) ? 3 : 0))
      .linkDirectionalParticleWidth(2)
      .linkDirectionalParticleSpeed(0.004)
      .minZoom(0.35)
      .maxZoom(5)
      .enableNodeDrag(true)
      .enablePanInteraction(true)
      .showPointerCursor((item) => Boolean(item))
      .onNodeHover((node) => {
        hoveredNodeId = node?.id ?? null;
        refreshGraphStyles();
      })
      .onNodeClick((node) => {
        onSelect?.(node.id);
      })
      .onNodeDrag((node) => {
        nodeDragActive = true;

        if (node.id === ROOT_NODE_ID) {
          pinRootNode();
        }
      })
      .onNodeDragEnd((node) => {
        nodeDragActive = false;

        if (node.id === ROOT_NODE_ID) {
          pinRootNode();
        }

        centerRootNode(360);
      })
      .onBackgroundClick(() => {
        onSelect?.(null);
      })
      .onZoomEnd(() => {
        if (recenteringRoot || nodeDragActive) {
          return;
        }

        centerRootNode(360);
      })
      .cooldownTicks(140)
      .onEngineTick(() => {
        pinRootNode();
      })
      .graphData(graphData);

    configureForces();
    resizeGraph();
    window.setTimeout(() => centerRootNode(0, { resetZoom: true }), 120);

    resizeObserver = new ResizeObserver(resizeGraph);
    resizeObserver.observe(containerElement);
    graphReady = true;
  }

  $effect(() => {
    const data = graphData;

    if (!graphReady || !graph) {
      return;
    }

    graph.graphData(data);
    configureForces();
    window.setTimeout(() => {
      if (data.nodes.length > 1) {
        centerRootNode(0, { resetZoom: true });
      }
    }, 80);
  });

  $effect(() => {
    const selectionState = `${selectedId ?? ''}:${hoveredNodeId ?? ''}`;
    void selectionState;

    if (!graphReady) {
      return;
    }

    refreshGraphStyles();
  });

  function cloneGraphData(
    inputNodes: OpportunityForceNode[],
    inputLinks: OpportunityForceLink[]
  ): GraphData<OpportunityForceNode, OpportunityForceLink> {
    return {
      nodes: inputNodes.map((node) => ({
        ...node,
        x: node.id === ROOT_NODE_ID ? 0 : node.x,
        y: node.id === ROOT_NODE_ID ? 0 : node.y,
        fx: node.id === ROOT_NODE_ID ? 0 : undefined,
        fy: node.id === ROOT_NODE_ID ? 0 : undefined
      })),
      links: inputLinks.map((link) => ({ ...link }))
    };
  }

  function configureForces() {
    if (!graph) {
      return;
    }

    const linkForce = graph.d3Force('link') as
      | {
          distance: (distance: (link: OpportunityForceLink) => number) => unknown;
          strength: (strength: (link: OpportunityForceLink) => number) => unknown;
        }
      | undefined;
    const chargeForce = graph.d3Force('charge') as { strength: (strength: number) => unknown } | undefined;

    linkForce?.distance((link) => link.distance);
    linkForce?.strength((link) => Math.max(0.35, link.similarity));
    chargeForce?.strength(-150);
    graph.d3ReheatSimulation();
  }

  function resizeGraph() {
    if (!graph || !containerElement) {
      return;
    }

    const rect = containerElement.getBoundingClientRect();
    graph.width(Math.max(320, Math.floor(rect.width))).height(Math.max(420, Math.floor(rect.height)));
    centerRootNode(0);
  }

  function refreshGraphStyles() {
    graph
      ?.nodeCanvasObject((node, context, scale) => drawNode(node, context, scale))
      ?.linkColor((link) => getLinkColor(link))
      .linkWidth((link) => getLinkWidth(link))
      .linkDirectionalParticles((link) => (isSelectedLink(link) ? 3 : 0));
  }

  function centerRootNode(durationMs = 0, options: { resetZoom?: boolean } = {}) {
    if (!graph) {
      return;
    }

    recenteringRoot = true;
    pinRootNode();

    if (options.resetZoom) {
      graph.zoom(ROOT_ZOOM, durationMs);
    }

    graph.centerAt(0, 0, durationMs);
    window.setTimeout(() => {
      recenteringRoot = false;
    }, durationMs + 80);
  }

  function pinRootNode() {
    const rootNode = graph?.graphData().nodes.find((node) => node.id === ROOT_NODE_ID);

    if (!rootNode) {
      return;
    }

    rootNode.x = 0;
    rootNode.y = 0;
    rootNode.fx = 0;
    rootNode.fy = 0;
  }

  function drawNode(node: OpportunityForceNode, context: CanvasRenderingContext2D, scale: number) {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const radius = getNodeRadius(node);
    const selected = node.id === selectedId;
    const hovered = node.id === hoveredNodeId;

    if (selected || hovered || node.kind === 'company') {
      context.beginPath();
      context.arc(x, y, radius + (selected ? 9 : 6), 0, 2 * Math.PI);
      context.fillStyle = selected ? 'rgba(11, 28, 48, 0.18)' : 'rgba(0, 108, 73, 0.12)';
      context.fill();
    }

    context.beginPath();
    context.arc(x, y, radius, 0, 2 * Math.PI);
    context.fillStyle = selected ? '#0b1c30' : node.color;
    context.fill();
    context.lineWidth = selected ? 3 : 1.5;
    context.strokeStyle = node.kind === 'company' ? '#6cf8bb' : '#ffffff';
    context.stroke();

    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = '#ffffff';
    context.font = `${Math.max(10, 12 / scale)}px Inter, sans-serif`;
    context.fillText(node.kind === 'company' ? 'FR' : `${node.score}%`, x, y);

    const label = node.kind === 'company' ? node.label : truncate(node.label, 26);
    const labelFontSize = Math.max(10, 13 / scale);
    context.font = `700 ${labelFontSize}px Inter, sans-serif`;
    context.fillStyle = node.kind === 'company' ? '#0b1c30' : '#191c1e';
    context.textBaseline = 'top';
    context.fillText(label, x, y + radius + 8);

    if (node.kind === 'opportunity') {
      context.font = `600 ${Math.max(9, 10 / scale)}px Inter, sans-serif`;
      context.fillStyle = '#64748b';
      context.fillText(node.statusLabel ?? 'Opportunity', x, y + radius + 8 + labelFontSize + 3);
    }
  }

  function paintNodePointerArea(node: OpportunityForceNode, color: string, context: CanvasRenderingContext2D) {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    context.fillStyle = color;
    context.beginPath();
    context.arc(x, y, getNodeRadius(node) + 18, 0, 2 * Math.PI);
    context.fill();
  }

  function getNodeRadius(node: OpportunityForceNode): number {
    if (node.kind === 'company') {
      return 22;
    }

    return Math.max(10, Math.min(18, 9 + node.score / 12));
  }

  function getLinkColor(link: OpportunityForceLink): string {
    if (isSelectedLink(link)) {
      return '#006c49';
    }

    return `rgba(100, 116, 139, ${Math.max(0.22, link.similarity * 0.55)})`;
  }

  function getLinkWidth(link: OpportunityForceLink): number {
    return isSelectedLink(link) ? 3 : Math.max(1.1, link.similarity * 2.4);
  }

  function isSelectedLink(link: OpportunityForceLink): boolean {
    if (!selectedId) {
      return false;
    }

    return getNodeId(link.source) === selectedId || getNodeId(link.target) === selectedId;
  }

  function getNodeId(node: string | number | OpportunityForceNode | undefined): string | null {
    if (node === undefined) {
      return null;
    }

    return typeof node === 'object' ? node.id : String(node);
  }

  function getNodeTooltip(node: OpportunityForceNode): string {
    if (node.kind === 'company') {
      return `<strong>${escapeHtml(node.label)}</strong><br/>Company profile root`;
    }

    return [
      `<strong>${escapeHtml(node.label)}</strong>`,
      `${node.score}% match`,
      escapeHtml(node.sponsor ?? 'Program source unavailable'),
      escapeHtml(node.fundingLabel ?? 'Funding unavailable'),
      escapeHtml(node.deadlineLabel ?? 'Deadline unavailable'),
      ...((node.reasons ?? []).slice(0, 4).map(escapeHtml))
    ].join('<br/>');
  }

  function truncate(value: string, maxLength: number): string {
    return value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value;
  }

  function escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }
</script>

<div
  class={fill
    ? 'h-full min-h-0 flex-1 overflow-hidden rounded-lg border border-slate-200 bg-[#f8fafc]'
    : 'h-[68vh] min-h-[460px] max-h-[720px] overflow-hidden rounded-lg border border-slate-200 bg-[#f8fafc]'}
  bind:this={containerElement}
  aria-label="Interactive opportunity match graph"
></div>
