"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { api, type GraphData } from "@/lib/api";

// ── D3 simulation types ───────────────────────────────────────────────────────

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  value: number;
}

interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  value: number;
}

// ── colour scale (violet → amber gradient by node weight) ────────────────────

const nodeColor = d3.scaleSequential()
  .domain([0, 1])   // normalised [0,1]
  .interpolator(d3.interpolateRgb("#7c3aed", "#fbbf24"));

// ── tooltip component ─────────────────────────────────────────────────────────

interface TooltipState {
  x: number;
  y: number;
  label: string;
  value: number;
  visible: boolean;
}

// ── empty state ───────────────────────────────────────────────────────────────

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
        ✦
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: 14, textAlign: "center", maxWidth: 300 }}>
        Your symbol map will emerge here as Gemma extracts patterns from your entries.
        Submit a few journal entries to begin.
      </p>
    </div>
  );
}

// ── legend ────────────────────────────────────────────────────────────────────

function Legend({ maxVal }: { maxVal: number }) {
  const stops = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div style={{
      position: "absolute", bottom: 24, left: 24,
      display: "flex", flexDirection: "column", gap: 6,
    }}>
      <span style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        Co-occurrence weight
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {stops.map((s) => (
          <div key={s} style={{
            width: 16, height: 16, borderRadius: "50%",
            background: nodeColor(s),
            boxShadow: `0 0 6px ${nodeColor(s)}88`,
          }} />
        ))}
        <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: 4 }}>→ {maxVal}</span>
      </div>
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function MapPage() {
  const svgRef    = useRef<SVGSVGElement>(null);
  const wrapRef   = useRef<HTMLDivElement>(null);
  const simRef    = useRef<d3.Simulation<SimNode, SimEdge> | null>(null);

  const [graph, setGraph]     = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({
    x: 0, y: 0, label: "", value: 0, visible: false,
  });
  const [selected, setSelected] = useState<string | null>(null);

  // ── fetch ──
  useEffect(() => {
    api.graph.get()
      .then(setGraph)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load graph")
      )
      .finally(() => setLoading(false));
  }, []);

  // ── build D3 simulation ──
  const buildGraph = useCallback(() => {
    if (!svgRef.current || !wrapRef.current || !graph) return;
    if (!graph.nodes.length) return;

    const width  = wrapRef.current.clientWidth;
    const height = wrapRef.current.clientHeight;

    // ── clear previous render ──
    d3.select(svgRef.current).selectAll("*").remove();
    simRef.current?.stop();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // ── zoom container ──
    const g = svg.append("g");

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.3, 4])
        .on("zoom", ({ transform }) => g.attr("transform", transform.toString()))
    );

    // ── normalise weights for colour scale ──
    const maxVal = Math.max(...graph.nodes.map((n) => n.value), 1);
    const norm   = (v: number) => v / maxVal;

    // ── copies for D3 mutation ──
    const nodes: SimNode[] = graph.nodes.map((n) => ({ ...n }));
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const edges: SimEdge[] = graph.edges.map((e) => ({
      source: nodeMap.get(e.source) ?? e.source,
      target: nodeMap.get(e.target) ?? e.target,
      value:  e.value,
    }));

    const maxEdgeVal = Math.max(...graph.edges.map((e) => e.value), 1);

    // ── edge radius scale ──
    const nodeRadius = d3.scaleSqrt()
      .domain([0, maxVal])
      .range([8, 36]);

    // ── force simulation ──
    const sim = d3.forceSimulation<SimNode>(nodes)
      .force("link",
        d3.forceLink<SimNode, SimEdge>(edges)
          .id((d) => d.id)
          .distance((d) => 80 + (1 - (d.value / maxEdgeVal)) * 120)
      )
      .force("charge", d3.forceManyBody<SimNode>().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision",
        d3.forceCollide<SimNode>().radius((d) => nodeRadius(d.value) + 8)
      );

    simRef.current = sim as unknown as d3.Simulation<SimNode, SimEdge>;

    // ── draw edges ──
    const link = g.append("g")
      .selectAll<SVGLineElement, SimEdge>("line")
      .data(edges)
      .join("line")
      .attr("stroke", "rgba(139,92,246,0.25)")
      .attr("stroke-width", (d) => 1 + (d.value / maxEdgeVal) * 4);

    // ── draw nodes ──
    const node = g.append("g")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .on("mouseover", function (event: MouseEvent, d) {
        d3.select(this).select("circle")
          .transition().duration(150)
          .attr("r", nodeRadius(d.value) * 1.2);
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top - 12,
          label: d.id,
          value: d.value,
          visible: true,
        });
      })
      .on("mousemove", function (event: MouseEvent) {
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip((prev) => ({
          ...prev,
          x: event.clientX - rect.left,
          y: event.clientY - rect.top - 12,
        }));
      })
      .on("mouseout", function (_event, d) {
        d3.select(this).select("circle")
          .transition().duration(150)
          .attr("r", nodeRadius(d.value));
        setTooltip((prev) => ({ ...prev, visible: false }));
      })
      .on("click", (_event, d) => {
        setSelected((prev) => (prev === d.id ? null : d.id));
      })
      .call(
        d3.drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x; d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null; d.fy = null;
          })
      );

    // glow filter
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");
    const merge = filter.append("feMerge");
    merge.append("feMergeNode").attr("in", "coloredBlur");
    merge.append("feMergeNode").attr("in", "SourceGraphic");

    // circles
    node.append("circle")
      .attr("r", (d) => nodeRadius(d.value))
      .attr("fill", (d) => nodeColor(norm(d.value)))
      .attr("fill-opacity", 0.85)
      .attr("stroke", (d) => nodeColor(norm(d.value)))
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.4)
      .attr("filter", "url(#glow)");

    // labels
    node.append("text")
      .text((d) => d.id)
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", (d) => Math.min(11, Math.max(8, nodeRadius(d.value) * 0.55)))
      .attr("fill", "#fff")
      .attr("fill-opacity", 0.9)
      .attr("pointer-events", "none")
      .attr("font-family", "Inter, sans-serif")
      .attr("font-weight", "600");

    // ── tick ──
    sim.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    return maxVal;
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

  // ── highlight selected node's connections ──
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);

    if (!selected) {
      svg.selectAll<SVGCircleElement, SimNode>("circle").attr("opacity", 1);
      svg.selectAll<SVGLineElement, SimEdge>("line").attr("opacity", 1);
      return;
    }

    svg.selectAll<SVGCircleElement, SimNode>("circle")
      .attr("opacity", (d) => (d.id === selected ? 1 : 0.25));

    svg.selectAll<SVGLineElement, SimEdge>("line")
      .attr("opacity", (d) => {
        const s = (d.source as SimNode).id;
        const t = (d.target as SimNode).id;
        return s === selected || t === selected ? 1 : 0.08;
      });
  }, [selected]);

  const maxVal = graph ? Math.max(...graph.nodes.map((n) => n.value), 1) : 1;
  const hasData = !!graph?.nodes.length;

  return (
    <div style={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", gap: 16 }}>

      {/* header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Symbol Map</h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "4px 0 0" }}>
            {hasData
              ? `${graph!.nodes.length} symbols · ${graph!.edges.length} co-occurrences — click a node to highlight its connections`
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
            }}
          >
            Clear selection: <strong>{selected}</strong> ✕
          </button>
        )}
      </div>

      {/* canvas */}
      <div
        ref={wrapRef}
        className="glass-card"
        style={{
          flex: 1, position: "relative", overflow: "hidden",
          padding: 0, minHeight: 400,
        }}
      >
        {/* loading */}
        {loading && (
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: 12,
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%",
              border: "2px solid #7c3aed", borderTopColor: "transparent",
              animation: "spin 1s linear infinite",
            }} />
            <span style={{ color: "var(--text-muted)", fontSize: 13 }}>Loading symbol network…</span>
          </div>
        )}

        {/* error */}
        {!loading && error && (
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <p style={{ color: "#f87171", fontSize: 14 }}>{error}</p>
          </div>
        )}

        {/* empty */}
        {!loading && !error && !hasData && <EmptyMap />}

        {/* D3 svg */}
        {!loading && !error && hasData && (
          <svg ref={svgRef} style={{ width: "100%", height: "100%", display: "block" }} />
        )}

        {/* tooltip */}
        {tooltip.visible && (
          <div style={{
            position: "absolute",
            left: tooltip.x + 12,
            top:  tooltip.y - 36,
            pointerEvents: "none",
            background: "rgba(15,10,30,0.92)",
            border: "1px solid rgba(124,58,237,0.4)",
            borderRadius: 8, padding: "6px 12px",
            backdropFilter: "blur(8px)",
          }}>
            <span style={{ color: "#c4b5fd", fontWeight: 600, fontSize: 13 }}>{tooltip.label}</span>
            <span style={{ color: "var(--text-muted)", fontSize: 11, marginLeft: 8 }}>
              weight {tooltip.value}
            </span>
          </div>
        )}

        {/* legend */}
        {hasData && <Legend maxVal={maxVal} />}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
