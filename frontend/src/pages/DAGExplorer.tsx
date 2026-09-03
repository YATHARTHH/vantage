import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API_BASE = "/api/v1";
const API_KEY = "dev-local-key";
const headers = { "X-API-Key": API_KEY };

// ─── Types ───────────────────────────────────────────────────────────────────

interface DAGNodeData {
  id: str;
  parent_id: string | null;
  type: string;
  name: string;
  depth: number;
  duration_ms: number;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
  status: "success" | "error" | "running" | "blocked";
  is_retry: boolean;
  attempt_number: number;
  retry_group_id?: string | null;
  has_payload: boolean;
  children: string[];
}

interface DAGEdgeData {
  source: string;
  target: string;
  edge_type: "child_execution" | "retry_loop" | "handoff";
}

interface DAGSummaryData {
  total_nodes: number;
  total_cost_usd: number;
  total_tokens: number;
  total_duration_ms: number;
  max_depth: number;
  retry_count: number;
  status: string;
  has_cycles: boolean;
}

interface DAGGraphData {
  trace_id: string;
  project_id: string;
  root_node_id: string;
  summary: DAGSummaryData;
  nodes: DAGNodeData[];
  edges: DAGEdgeData[];
}

interface TraceListItem {
  trace_id: string;
  project_id: string;
  root_operation: string;
  span_count: number;
  total_cost_usd: number;
  total_tokens: number;
  status: string;
}

interface NodeDetailPayload {
  span_id: string;
  trace_id: string;
  project_id: string;
  model_name?: string;
  event_kind?: string;
  status?: string;
  duration_ms?: number;
  cost_usd?: number;
  tokens_input?: number;
  tokens_output?: number;
  log_prompts_enabled: boolean;
  payload_preview?: string | null;
  privacy_notice?: string | null;
}

// ─── Colors ──────────────────────────────────────────────────────────────────

const NODE_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  agent_run: { border: "#a855f7", bg: "rgba(168,85,247,0.12)", text: "#c084fc" },
  llm_call: { border: "#22d3ee", bg: "rgba(34,211,238,0.12)", text: "#67e8f9" },
  tool_execution: { border: "#f97316", bg: "rgba(249,115,22,0.12)", text: "#fdba74" },
  synthetic_root: { border: "#64748b", bg: "rgba(100,116,139,0.15)", text: "#94a3b8" },
};

export default function DAGExplorer() {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string>("");
  const [graph, setGraph] = useState<DAGGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeDetail, setNodeDetail] = useState<NodeDetailPayload | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Fetch list of traces
  useEffect(() => {
    axios.get<TraceListItem[]>(`${API_BASE}/analytics/dag/traces`, { headers })
      .then((res) => {
        setTraces(res.data);
        if (res.data.length > 0) {
          setSelectedTraceId(res.data[0].trace_id);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch DAG topology graph
  const fetchGraph = useCallback(async () => {
    if (!selectedTraceId) return;
    setLoading(true);
    setSelectedNodeId(null);
    setNodeDetail(null);
    try {
      const res = await axios.get<DAGGraphData>(`${API_BASE}/analytics/dag/${selectedTraceId}`, { headers });
      setGraph(res.data);
    } catch {
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [selectedTraceId]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  // Fetch lazy-loaded node payload detail when a node is clicked
  const handleNodeClick = async (node: DAGNodeData) => {
    setSelectedNodeId(node.id);
    if (node.type === "synthetic_root") {
      setNodeDetail(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const res = await axios.get<NodeDetailPayload>(
        `${API_BASE}/analytics/dag/${selectedTraceId}/node/${node.id}`,
        { headers }
      );
      setNodeDetail(res.data);
    } catch {
      setNodeDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Group nodes by depth for hierarchical SVG layout
  const nodesByDepth: Record<number, DAGNodeData[]> = {};
  if (graph) {
    graph.nodes.forEach((n) => {
      const d = n.depth || 0;
      if (!nodesByDepth[d]) nodesByDepth[d] = [];
      nodesByDepth[d].push(n);
    });
  }

  const depthKeys = Object.keys(nodesByDepth).map(Number).sort((a, b) => a - b);
  const canvasHeight = Math.max(500, depthKeys.length * 140 + 60);

  // Position map for SVG edge drawing: node_id -> { x, y }
  const nodePositions: Record<string, { x: number; y: number }> = {};
  depthKeys.forEach((d, rowIndex) => {
    const rowNodes = nodesByDepth[d];
    const rowWidth = rowNodes.length * 220;
    const startX = Math.max(100, (1100 - rowWidth) / 2 + 110);

    rowNodes.forEach((node, colIndex) => {
      nodePositions[node.id] = {
        x: startX + colIndex * 220,
        y: 80 + rowIndex * 140,
      };
    });
  });

  return (
    <div style={{
      minHeight: "calc(100vh - 65px)",
      background: "linear-gradient(135deg, #020617 0%, #0a0c1a 50%, #0d0a1a 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
      color: "#e2e8f0",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Sub-Header Bar */}
      <div style={{
        padding: "14px 24px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(10,12,26,0.85)",
        backdropFilter: "blur(12px)",
        zIndex: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg, #a855f7, #06b6d4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18,
          }}>🔀</div>
          <div>
            <div style={{ color: "#e2e8f0", fontWeight: 800, fontSize: 16 }}>Multi-Agent Execution DAG</div>
            <div style={{ color: "#475569", fontSize: 12 }}>Directed Execution Topology · Inter-Agent Handoffs · Retry Loops</div>
          </div>
        </div>

        {/* Trace Selector */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ fontSize: 13, color: "#64748b" }}>Select Trace:</span>
          <select
            value={selectedTraceId}
            onChange={(e) => setSelectedTraceId(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#e2e8f0",
              fontSize: 13,
              outline: "none",
              cursor: "pointer",
              minWidth: 260,
            }}
          >
            {traces.map((t) => (
              <option key={t.trace_id} value={t.trace_id} style={{ background: "#0f172a", color: "#e2e8f0" }}>
                {t.root_operation} ({t.span_count} spans - ${t.total_cost_usd}) [{t.trace_id.slice(0, 8)}...]
              </option>
            ))}
          </select>
          <button
            onClick={fetchGraph}
            disabled={loading}
            style={{
              background: "linear-gradient(135deg, #a855f7, #06b6d4)",
              border: "none",
              borderRadius: 8,
              padding: "8px 16px",
              color: "#fff",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden" }}>
        {/* Left/Center Canvas */}
        <div style={{ flex: 1, position: "relative", overflow: "auto", padding: 20 }}>
          {graph && graph.summary && (
            /* Summary Metrics Strip */
            <div style={{
              position: "sticky", top: 0, zIndex: 10,
              background: "rgba(10,12,26,0.9)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 12, padding: "10px 20px",
              display: "flex", gap: 24, alignItems: "center",
              marginBottom: 20, backdropFilter: "blur(12px)",
              width: "fit-content",
            }}>
              <div>
                <div style={{ fontSize: 10, color: "#64748b" }}>TRACE STATUS</div>
                <div style={{
                  fontSize: 13, fontWeight: 700,
                  color: graph.summary.status === "success" ? "#22c55e" : "#ef4444"
                }}>{graph.summary.status.toUpperCase()}</div>
              </div>
              <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b" }}>TOTAL NODES</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>{graph.summary.total_nodes}</div>
              </div>
              <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b" }}>TOTAL COST</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#22d3ee" }}>${graph.summary.total_cost_usd.toFixed(4)}</div>
              </div>
              <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b" }}>TOTAL TOKENS</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#a855f7" }}>{graph.summary.total_tokens.toLocaleString()}</div>
              </div>
              <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b" }}>LATENCY</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>{graph.summary.total_duration_ms} ms</div>
              </div>
              {graph.summary.retry_count > 0 && (
                <>
                  <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)" }} />
                  <div>
                    <div style={{ fontSize: 10, color: "#f97316" }}>RETRY LOOPS</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#f97316" }}>{graph.summary.retry_count}</div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* SVG Canvas for DAG Edges & Nodes */}
          {graph ? (
            <div style={{ position: "relative", minWidth: 1100, height: canvasHeight }}>
              <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
                {graph.edges.map((edge, idx) => {
                  const srcPos = nodePositions[edge.source];
                  const tgtPos = nodePositions[edge.target];
                  if (!srcPos || !tgtPos) return null;

                  const isRetry = edge.edge_type === "retry_loop";
                  const color = isRetry ? "#f97316" : "rgba(255,255,255,0.2)";

                  return (
                    <g key={`edge-${idx}`}>
                      <path
                        d={`M ${srcPos.x} ${srcPos.y + 25} C ${srcPos.x} ${srcPos.y + 70}, ${tgtPos.x} ${tgtPos.y - 70}, ${tgtPos.x} ${tgtPos.y - 25}`}
                        fill="none"
                        stroke={color}
                        strokeWidth={isRetry ? 2.5 : 1.5}
                        strokeDasharray={isRetry ? "4,4" : undefined}
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Node Cards */}
              {graph.nodes.map((node) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;

                const isSelected = selectedNodeId === node.id;
                const styleCfg = NODE_COLORS[node.type] || NODE_COLORS.agent_run;
                const isOrphanRoot = node.type === "synthetic_root";

                return (
                  <div
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    style={{
                      position: "absolute",
                      left: pos.x - 90,
                      top: pos.y - 25,
                      width: 180,
                      background: isOrphanRoot ? styleCfg.bg : "rgba(15,23,42,0.92)",
                      border: `2px ${isOrphanRoot ? "dashed" : "solid"} ${isSelected ? "#38bdf8" : styleCfg.border}`,
                      borderRadius: 10,
                      padding: "10px 12px",
                      cursor: "pointer",
                      backdropFilter: "blur(8px)",
                      boxShadow: isSelected ? `0 0 16px ${styleCfg.border}` : "0 4px 12px rgba(0,0,0,0.3)",
                      transition: "all 0.2s",
                      zIndex: isSelected ? 5 : 1,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: styleCfg.text, textTransform: "uppercase" }}>
                        {node.type.replace("_", " ")}
                      </span>
                      {node.is_retry && (
                        <span style={{
                          background: "rgba(249,115,22,0.2)", color: "#f97316",
                          border: "1px solid #f97316", borderRadius: 4,
                          fontSize: 9, padding: "1px 4px", fontWeight: 700
                        }}>
                          Retry #{node.attempt_number}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#e2e8f0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {node.name}
                    </div>
                    {!isOrphanRoot && (
                      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10, color: "#64748b" }}>
                        <span>{node.duration_ms}ms</span>
                        <span style={{ color: "#22d3ee" }}>${node.cost_usd.toFixed(4)}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ padding: 40, color: "#64748b", textAlign: "center" }}>
              Select a trace above to load execution DAG topology.
            </div>
          )}
        </div>

        {/* Right Node Detail Inspector Panel */}
        {selectedNodeId && (
          <div style={{
            width: 320,
            borderLeft: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(10,12,26,0.95)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 16,
            backdropFilter: "blur(12px)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 700, fontSize: 14 }}>Node Inspector</span>
              <button
                onClick={() => setSelectedNodeId(null)}
                style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}
              >×</button>
            </div>

            {loadingDetail ? (
              <div style={{ color: "#64748b", fontSize: 13 }}>Loading payload detail…</div>
            ) : nodeDetail ? (
              <>
                <div style={{ fontSize: 11, color: "#64748b" }}>SPAN ID</div>
                <div style={{ fontSize: 12, fontFamily: "monospace", color: "#94a3b8", wordBreak: "break-all" }}>{nodeDetail.span_id}</div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                    <div style={{ fontSize: 10, color: "#64748b" }}>MODEL</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{nodeDetail.model_name || "N/A"}</div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                    <div style={{ fontSize: 10, color: "#64748b" }}>STATUS</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: nodeDetail.status === "success" ? "#22c55e" : "#ef4444" }}>
                      {(nodeDetail.status || "success").toUpperCase()}
                    </div>
                  </div>
                </div>

                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                  <div style={{ fontSize: 10, color: "#64748b", marginBottom: 4 }}>TOKENS & COST</div>
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    In: <strong style={{ color: "#e2e8f0" }}>{nodeDetail.tokens_input || 0}</strong> · Out: <strong style={{ color: "#e2e8f0" }}>{nodeDetail.tokens_output || 0}</strong>
                  </div>
                  <div style={{ fontSize: 12, color: "#22d3ee", marginTop: 2, fontWeight: 700 }}>
                    Cost: ${Number(nodeDetail.cost_usd || 0).toFixed(6)}
                  </div>
                </div>

                {/* Privacy-Guarded Prompt Payload */}
                <div>
                  <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>PROMPT / PAYLOAD PREVIEW</div>
                  {nodeDetail.privacy_notice ? (
                    <div style={{
                      background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                      borderRadius: 8, padding: "10px 12px", color: "#f87171", fontSize: 12,
                    }}>
                      🔒 {nodeDetail.privacy_notice}
                    </div>
                  ) : nodeDetail.payload_preview ? (
                    <div style={{
                      background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 8, padding: 10, fontSize: 12, color: "#cbd5e1",
                      maxHeight: 180, overflowY: "auto", fontFamily: "monospace", whiteSpace: "pre-wrap"
                    }}>
                      {nodeDetail.payload_preview}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: "#64748b", fontStyle: "italic" }}>
                      No prompt preview stored for this span.
                    </div>
                  )}
                </div>

                {/* Offline Replay & What-If Buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
                  <button
                    onClick={async () => {
                      try {
                        const res = await axios.post(`/api/v1/replay/trace/${selectedTraceId}`, {}, { headers });
                        alert(`Replay Status: ${res.data.status}\nExecuted Nodes: ${res.data.executed_nodes_count}\nCost: $0.00 (Offline Mocked)`);
                      } catch (err: any) {
                        alert(err.response?.data?.detail || "Replay failed");
                      }
                    }}
                    style={{
                      background: "rgba(168,85,247,0.15)",
                      border: "1px solid #a855f7",
                      color: "#c084fc",
                      borderRadius: 8,
                      padding: "8px 12px",
                      fontWeight: 600,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                    }}
                  >
                    ⏳ Trigger Offline Replay
                  </button>

                  <button
                    onClick={() => {
                      const candidate = prompt("Enter candidate modified prompt text for What-If estimation:", nodeDetail.payload_preview || "");
                      if (candidate) {
                        axios.post('/api/v1/replay/what-if', {
                          trace_id: selectedTraceId,
                          modified_prompts: { [nodeDetail.span_id]: candidate }
                        }, { headers }).then(res => {
                          const d = res.data;
                          alert(
                            `Local Estimated Impact:\n\n` +
                            `Faithfulness Delta: ${d.delta.faithfulness}\n` +
                            `Security Risk Delta: ${d.delta.security_risk}\n\n` +
                            `Disclaimer: ${d.disclaimer}`
                          );
                        }).catch(err => alert(err.response?.data?.detail || "What-If failed"));
                      }
                    }}
                    style={{
                      background: "rgba(34,211,238,0.15)",
                      border: "1px solid #22d3ee",
                      color: "#67e8f9",
                      borderRadius: 8,
                      padding: "8px 12px",
                      fontWeight: 600,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                    }}
                  >
                    🔮 Evaluate What-If Prompt
                  </button>
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
