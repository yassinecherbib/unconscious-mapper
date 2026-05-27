"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { api, type GraphData, type GraphEdge, type GraphNode } from "@/lib/api";

interface SimNode extends GraphNode, d3.SimulationNodeDatum {
  orbitX?: number;
  orbitY?: number;
}

interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  value: number;
  type: "cooccurrence" | "attribution";
  decayed_value?: number;
  recency_weight?: number;
  confidence?: number;
}

interface TooltipState {
  x: number;
  y: number;
  visible: boolean;
  node: SimNode | null;
  containerWidth: number;
}

const ARCHETYPE_COLORS: Record<string, string> = {
  Self: "#f2b84b",
  Shadow: "#8f5cff",
  Anima: "#35cde0",
  Animus: "#3aa0ff",
  Hero: "#ef6f4f",
  Trickster: "#62d26f",
  Persona: "#d88ad8",
  Child: "#f7d66f",
  "Great Mother": "#5fc09f",
  "Terrible Mother": "#cf4e72",
  "Wise Old Man": "#9eb7ff",
  "Threshold Guardian": "#b6a36d",
  Death: "#a3a3a3",
  Rebirth: "#ff9f43",
};

const FALLBACK_COLOR = "#9ca3af";

function archetypeColor(name?: string | null) {
  return name ? ARCHETYPE_COLORS[name] ?? FALLBACK_COLOR : FALLBACK_COLOR;
}

function nodeId(value: string | SimNode | undefined) {
  return typeof value === "string" ? value : value?.id ?? "";
}

function nodeLabel(node: GraphNode) {
  return node.label ?? node.id.replace(/^archetype:/, "");
}

function EmptyMap() {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", height: "100%", gap: 16,
    }}>
      <div style={{
        width: 72, height: 72, borderRadius: "50%",
        background: "rgba(124,58,237,0.08)",
        border: "1px solid rgba(124,58,237,0.2)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 30,
      }}>
        *
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: 14, textAlign: "center", maxWidth: 300 }}>
        Your symbol map will emerge here as Gemma extracts patterns from your entries.
        Submit a few journal entries to begin.
      </p>
    </div>
  );
}

function Legend({ archetypes }: { archetypes: string[] }) {
  const shown = archetypes.slice(0, 8);
  return (
    <div style={{
      position: "absolute", bottom: 20, left: 20,
      display: "flex", flexDirection: "column", gap: 8,
      padding: "10px 12px",
      borderRadius: 8,
      background: "rgba(9, 8, 20, 0.72)",
      border: "1px solid rgba(255,255,255,0.08)",
      backdropFilter: "blur(10px)",
      maxWidth: "calc(100% - 40px)",
    }}>
      <span style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        Archetype color
      </span>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 12px" }}>
        {shown.map((name) => (
          <span key={name} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#e5e7eb" }}>
            <span style={{
              width: 10, height: 10, borderRadius: "50%",
              background: archetypeColor(name),
              boxShadow: `0 0 8px ${archetypeColor(name)}88`,
            }} />
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function MapPage() {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const simRef = useRef<d3.Simulation<SimNode, SimEdge> | null>(null);

  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, visible: false, node: null, containerWidth: 320 });

  useEffect(() => {
    api.graph.get()
      .then(setGraph)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load graph"))
      .finally(() => setLoading(false));
  }, []);

  const buildGraph = useCallback(() => {
    if (!svgRef.current || !wrapRef.current || !graph?.nodes.length) return;

    const width = wrapRef.current.clientWidth;
    const height = wrapRef.current.clientHeight;
    const centerX = width / 2;
    const centerY = height / 2 + 24;

    d3.select(svgRef.current).selectAll("*").remove();
    simRef.current?.stop();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height);
    const g = svg.append("g");

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.35, 3.5])
        .on("zoom", ({ transform }) => g.attr("transform", transform.toString()))
    );

    const normalizedNodes = graph.nodes.map((node) => ({
      ...node,
      type: node.type ?? "symbol",
      label: nodeLabel(node),
    })) as SimNode[];
    const archetypeNodes = normalizedNodes.filter((node) => node.type === "archetype");
    const symbolNodes = normalizedNodes.filter((node) => node.type !== "archetype");
    const orbitRadiusX = Math.max(160, width * 0.36);
    const orbitRadiusY = Math.max(90, height * 0.26);

    archetypeNodes.forEach((node, index) => {
      const angle = (-Math.PI * 0.88) + (archetypeNodes.length <= 1 ? 0 : (index / (archetypeNodes.length - 1)) * Math.PI * 0.76);
      node.orbitX = centerX + Math.cos(angle) * orbitRadiusX;
      node.orbitY = centerY + Math.sin(angle) * orbitRadiusY;
      node.fx = node.orbitX;
      node.fy = node.orbitY;
    });

    const nodeMap = new Map(normalizedNodes.map((node) => [node.id, node]));
    const edges: SimEdge[] = graph.edges
      .filter((edge: GraphEdge) => nodeMap.has(edge.source) && nodeMap.has(edge.target))
      .map((edge: GraphEdge) => ({
        ...edge,
        type: edge.type ?? "cooccurrence",
        source: nodeMap.get(edge.source)!,
        target: nodeMap.get(edge.target)!,
      }));
    const coEdges = edges.filter((edge) => edge.type === "cooccurrence");
    const attributionEdges = edges.filter((edge) => edge.type === "attribution");
    const maxSymbolValue = Math.max(...symbolNodes.map((node) => node.value), 1);
    const maxRecentValue = Math.max(...coEdges.map((edge) => edge.decayed_value ?? edge.value), 1);
    const maxArchetypeValue = Math.max(...archetypeNodes.map((node) => node.value), 1);

    const symbolRadius = d3.scaleSqrt().domain([0, maxSymbolValue]).range([8, 28]);
    const archetypeRadius = d3.scaleSqrt().domain([0, maxArchetypeValue]).range([20, 42]);

    const sim = d3.forceSimulation<SimNode>(normalizedNodes)
      .force("link",
        d3.forceLink<SimNode, SimEdge>(edges)
          .id((node) => node.id)
          .distance((edge) => edge.type === "attribution" ? 110 - ((edge.confidence ?? 0.5) * 30) : 95 + (1 - ((edge.decayed_value ?? edge.value) / maxRecentValue)) * 95)
          .strength((edge) => edge.type === "attribution" ? 0.08 + ((edge.confidence ?? 0.5) * 0.2) : 0.18)
      )
      .force("charge", d3.forceManyBody<SimNode>().strength((node) => node.type === "archetype" ? -520 : -260))
      .force("center", d3.forceCenter(centerX, centerY))
      .force("x", d3.forceX<SimNode>((node) => {
        if (node.type === "archetype") return node.orbitX ?? centerX;
        const hub = node.dominant_archetype ? nodeMap.get(`archetype:${node.dominant_archetype}`) : null;
        return hub?.orbitX ?? centerX;
      }).strength((node) => node.type === "archetype" ? 0.6 : node.dominant_archetype ? 0.045 : 0.02))
      .force("y", d3.forceY<SimNode>((node) => {
        if (node.type === "archetype") return node.orbitY ?? centerY;
        const hub = node.dominant_archetype ? nodeMap.get(`archetype:${node.dominant_archetype}`) : null;
        return hub?.orbitY ? hub.orbitY + 120 : centerY + 40;
      }).strength((node) => node.type === "archetype" ? 0.6 : node.dominant_archetype ? 0.05 : 0.025))
      .force("collision", d3.forceCollide<SimNode>().radius((node) => (
        node.type === "archetype" ? archetypeRadius(node.value) + 18 : symbolRadius(node.value) + 12
      )));

    simRef.current = sim as d3.Simulation<SimNode, SimEdge>;

    const defs = svg.append("defs");
    const glow = defs.append("filter").attr("id", "glow").attr("x", "-80%").attr("y", "-80%").attr("width", "260%").attr("height", "260%");
    glow.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");
    const merge = glow.append("feMerge");
    merge.append("feMergeNode").attr("in", "coloredBlur");
    merge.append("feMergeNode").attr("in", "SourceGraphic");

    const coLink = g.append("g")
      .attr("class", "co-links")
      .selectAll<SVGLineElement, SimEdge>("line")
      .data(coEdges)
      .join("line")
      .attr("class", "graph-link co-link")
      .attr("stroke", "rgba(168, 162, 158, 0.5)")
      .attr("stroke-linecap", "round")
      .attr("stroke-opacity", (edge) => 0.08 + Math.min(0.72, ((edge.recency_weight ?? 1) * 0.72)))
      .attr("stroke-width", (edge) => 0.8 + ((edge.decayed_value ?? edge.value) / maxRecentValue) * 4.2);

    const attrLink = g.append("g")
      .attr("class", "attribution-links")
      .selectAll<SVGLineElement, SimEdge>("line")
      .data(attributionEdges)
      .join("line")
      .attr("class", "graph-link attr-link")
      .attr("stroke", (edge) => {
        const target = edge.target as SimNode;
        return archetypeColor(target.label);
      })
      .attr("stroke-opacity", (edge) => 0.14 + (edge.confidence ?? 0.5) * 0.34)
      .attr("stroke-width", (edge) => 0.7 + (edge.confidence ?? 0.5) * 1.8)
      .attr("stroke-dasharray", "3 5");

    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll<SVGGElement, SimNode>("g")
      .data(normalizedNodes)
      .join("g")
      .attr("class", "graph-node")
      .attr("cursor", "pointer")
      .on("mouseover", function (event: MouseEvent, d) {
        const rect = svgRef.current!.getBoundingClientRect();
        d3.select(this).select<SVGCircleElement>("circle.core")
          .transition().duration(140)
          .attr("r", d.type === "archetype" ? archetypeRadius(d.value) * 1.1 : symbolRadius(d.value) * 1.18);
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          visible: true,
          node: d,
          containerWidth: rect.width,
        });
      })
      .on("mousemove", (event: MouseEvent) => {
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip((prev) => ({
          ...prev,
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          containerWidth: rect.width,
        }));
      })
      .on("mouseout", function (_event, d) {
        d3.select(this).select<SVGCircleElement>("circle.core")
          .transition().duration(140)
          .attr("r", d.type === "archetype" ? archetypeRadius(d.value) : symbolRadius(d.value));
        setTooltip((prev) => ({ ...prev, visible: false, node: null }));
      })
      .on("click", (_event, d) => setSelected((prev) => prev === d.id ? null : d.id))
      .call(
        d3.drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) sim.alphaTarget(0.24).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            if (d.type !== "archetype") {
              d.fx = null;
              d.fy = null;
            }
          })
      );

    node.filter((d) => !!d.is_bridge)
      .append("circle")
      .attr("class", "bridge-halo")
      .attr("r", (d) => symbolRadius(d.value) + 8)
      .attr("fill", "none")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.75)
      .attr("stroke-dasharray", "4 4");

    node.append("circle")
      .attr("class", "core")
      .attr("r", (d) => d.type === "archetype" ? archetypeRadius(d.value) : symbolRadius(d.value))
      .attr("fill", (d) => d.type === "archetype" ? archetypeColor(d.label) : archetypeColor(d.dominant_archetype))
      .attr("fill-opacity", (d) => d.type === "archetype" ? 0.22 : 0.88)
      .attr("stroke", (d) => d.type === "archetype" ? archetypeColor(d.label) : archetypeColor(d.dominant_archetype))
      .attr("stroke-width", (d) => d.type === "archetype" ? 2.5 : d.is_bridge ? 3 : 1.4)
      .attr("stroke-opacity", (d) => d.type === "archetype" ? 0.9 : 0.7)
      .attr("filter", "url(#glow)");

    node.append("text")
      .text((d) => d.label ?? d.id)
      .attr("text-anchor", "middle")
      .attr("dy", (d) => d.type === "archetype" ? "0.35em" : "0.34em")
      .attr("font-size", (d) => d.type === "archetype" ? 12 : Math.min(11, Math.max(8, symbolRadius(d.value) * 0.52)))
      .attr("fill", "#ffffff")
      .attr("fill-opacity", (d) => d.type === "archetype" ? 0.96 : 0.9)
      .attr("pointer-events", "none")
      .attr("font-family", "Inter, sans-serif")
      .attr("font-weight", (d) => d.type === "archetype" ? "700" : "600");

    sim.on("tick", () => {
      coLink
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      attrLink
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });
  }, [graph]);

  useEffect(() => {
    buildGraph();
    const onResize = () => buildGraph();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      simRef.current?.stop();
    };
  }, [buildGraph]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);

    if (!selected) {
      svg.selectAll<SVGCircleElement, SimNode>(".core,.bridge-halo").attr("opacity", 1);
      svg.selectAll<SVGLineElement, SimEdge>(".graph-link").attr("opacity", 1);
      return;
    }

    const connected = new Set<string>([selected]);
    svg.selectAll<SVGLineElement, SimEdge>(".graph-link").each((edge) => {
      const source = nodeId(edge.source as string | SimNode);
      const target = nodeId(edge.target as string | SimNode);
      if (source === selected || target === selected) {
        connected.add(source);
        connected.add(target);
      }
    });

    svg.selectAll<SVGCircleElement, SimNode>(".core,.bridge-halo")
      .attr("opacity", (d) => connected.has(d.id) ? 1 : 0.18);

    svg.selectAll<SVGLineElement, SimEdge>(".graph-link")
      .attr("opacity", (edge) => {
        const source = nodeId(edge.source as string | SimNode);
        const target = nodeId(edge.target as string | SimNode);
        return source === selected || target === selected ? 1 : 0.08;
      });
  }, [selected]);

  const symbolCount = graph?.nodes.filter((node) => (node.type ?? "symbol") === "symbol").length ?? 0;
  const archetypes = graph?.nodes
    .filter((node) => node.type === "archetype")
    .map((node) => node.label ?? node.id.replace(/^archetype:/, "")) ?? [];
  const coEdgeCount = graph?.edges.filter((edge) => (edge.type ?? "cooccurrence") === "cooccurrence").length ?? 0;
  const hasData = symbolCount > 0;
  const selectedNode = graph?.nodes.find((node) => node.id === selected);

  return (
    <div style={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0, gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Symbol Map</h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "4px 0 0" }}>
            {hasData
              ? `${symbolCount} symbols · ${archetypes.length} archetypes · ${coEdgeCount} co-occurrences`
              : "Your symbol co-occurrence network"}
          </p>
        </div>

        {selected && (
          <button
            onClick={() => setSelected(null)}
            style={{
              background: "rgba(124,58,237,0.12)",
              border: "1px solid rgba(124,58,237,0.3)",
              borderRadius: 8, padding: "6px 14px",
              color: "#c4b5fd", fontSize: 13, cursor: "pointer",
              minWidth: 0,
            }}
          >
            Clear selection: <strong>{selectedNode?.label ?? selected.replace(/^archetype:/, "")}</strong>
          </button>
        )}
      </div>

      <div
        ref={wrapRef}
        className="glass-card"
        style={{
          flex: 1, position: "relative", overflow: "hidden",
          padding: 0, minHeight: 420,
        }}
      >
        {loading && (
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: 12,
          }}>
            <div style={{
              width: 180,
              height: 4,
              borderRadius: 999,
              overflow: "hidden",
              background: "rgba(255,255,255,0.08)",
            }}>
              <div style={{
                width: "44%",
                height: "100%",
                borderRadius: 999,
                background: "linear-gradient(90deg, #35cde0, #f2b84b)",
                animation: "loadbar 1.1s ease-in-out infinite",
              }} />
            </div>
            <span style={{ color: "var(--text-muted)", fontSize: 13 }}>Loading symbol network...</span>
          </div>
        )}

        {!loading && error && (
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <p style={{ color: "#f87171", fontSize: 14 }}>{error}</p>
          </div>
        )}

        {!loading && !error && !hasData && <EmptyMap />}

        {!loading && !error && hasData && (
          <svg ref={svgRef} style={{ width: "100%", height: "100%", display: "block" }} />
        )}

        {tooltip.visible && tooltip.node && (
          <div style={{
            position: "absolute",
            left: Math.min(tooltip.x + 12, Math.max(12, tooltip.containerWidth - 260)),
            top: Math.max(12, tooltip.y - 42),
            pointerEvents: "none",
            background: "rgba(10,10,22,0.92)",
            border: `1px solid ${archetypeColor(tooltip.node.type === "archetype" ? tooltip.node.label : tooltip.node.dominant_archetype)}66`,
            borderRadius: 8,
            padding: "8px 12px",
            backdropFilter: "blur(10px)",
            maxWidth: 248,
            boxShadow: "0 16px 40px rgba(0,0,0,0.28)",
          }}>
            <div style={{ color: "#fff", fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
              {tooltip.node.label ?? tooltip.node.id}
            </div>
            {tooltip.node.type === "archetype" ? (
              <div style={{ color: "var(--text-muted)", fontSize: 11 }}>
                archetype hub · strength {Number(tooltip.node.value).toFixed(2)}
              </div>
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: 11, lineHeight: 1.6 }}>
                weight {tooltip.node.value}
                <br />
                {tooltip.node.dominant_archetype
                  ? `${tooltip.node.dominant_archetype} · ${Math.round((tooltip.node.dominant_confidence ?? 0) * 100)}%`
                  : "unattributed"}
                {tooltip.node.is_bridge && (
                  <>
                    <br />
                    bridge node · score {tooltip.node.bridge_score}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {hasData && <Legend archetypes={archetypes} />}
      </div>

      <style>{`
        @keyframes loadbar {
          0% { transform: translateX(-110%); }
          55% { transform: translateX(80%); }
          100% { transform: translateX(240%); }
        }
      `}</style>
    </div>
  );
}
