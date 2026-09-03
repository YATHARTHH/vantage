import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API_BASE = "/api/v1";
const API_KEY = "dev-local-key";
const headers = { "X-API-Key": API_KEY, "Authorization": `Bearer ${API_KEY}` };

// ─── Types ───────────────────────────────────────────────────────────────────

interface DAGNodeData {
  id: string;
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

interface ReplayResultData {
  replay_id: string;
  trace_id: string;
  project_id: string;
  status: string;
  reason?: string;
  executed_nodes_count: number;
  total_cost_usd: number;
  is_offline: boolean;
}

interface WhatIfResponseData {
  replay_id: string;
  trace_id: string;
  label: string;
  disclaimer: string;
  baseline: { faithfulness_score: number; unsupported_claim_ratio: number; security_risk: number };
  what_if: { faithfulness_score: number; unsupported_claim_ratio: number; security_risk: number };
  delta: { faithfulness: number; unsupported_claim_ratio: number; security_risk: number };
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

  // Replay Modal State
  const [replayModalOpen, setReplayModalOpen] = useState(false);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayResult, setReplayResult] = useState<ReplayResultData | null>(null);

  // What-If Modal State
  const [whatIfModalOpen, setWhatIfModalOpen] = useState(false);
  const [whatIfInputText, setWhatIfInputText] = useState("");
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponseData | null>(null);

  // Fetch list of traces
  useEffect(() => {
    axios.get<TraceListItem[]>(`${API_BASE}/analytics/dag/traces`, { headers })
      .then((res) => {
        const traceList = Array.isArray(res.data) ? res.data : [];
        setTraces(traceList);
        if (traceList.length > 0) {
          setSelectedTraceId(traceList[0].trace_id);
        }
      })
      .catch(() => setTraces([]));
  }, []);

  // Fetch DAG topology graph
  const fetchGraph = useCallback(async () => {
    if (!selectedTraceId) return;
    setLoading(true);
    setSelectedNodeId(null);
    setNodeDetail(null);
    try {
      const res = await axios.get<DAGGraphData>(`${API_BASE}/analytics/dag/${selectedTraceId}`, { headers });
      setGraph(res.data && Array.isArray(res.data.nodes) ? res.data : null);
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

  // Trigger Offline Replay
  const handleTriggerReplay = async () => {
    setReplayModalOpen(true);
    setReplayLoading(true);
    setReplayResult(null);
    try {
      const res = await axios.post<ReplayResultData>(`${API_BASE}/replay/trace/${selectedTraceId}`, {}, { headers });
      setReplayResult(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Replay failed");
      setReplayModalOpen(false);
    } finally {
      setReplayLoading(false);
    }
  };

  // Open What-If Modal
  const openWhatIfModal = () => {
    setWhatIfInputText(nodeDetail?.payload_preview || "System Prompt: Act as a search assistant.");
    setWhatIfResult(null);
    setWhatIfModalOpen(true);
  };

  // Submit What-If Evaluation
  const handleEvaluateWhatIf = async () => {
    if (!nodeDetail) return;
    setWhatIfLoading(true);
    try {
      const res = await axios.post<WhatIfResponseData>(`${API_BASE}/replay/what-if`, {
        trace_id: selectedTraceId,
        modified_prompts: { [nodeDetail.span_id]: whatIfInputText }
      }, { headers });
      setWhatIfResult(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || "What-If estimation failed");
    } finally {
      setWhatIfLoading(false);
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
      width: "100%",
      maxWidth: "100vw",
      overflowX: "hidden",
      background: "linear-gradient(135deg, #030712 0%, #0b0f19 50%, #0f172a 100%)",
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
        background: "rgba(11,15,25,0.85)",
        backdropFilter: "blur(16px)",
        zIndex: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg, #a855f7, #06b6d4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, boxShadow: "0 0 16px rgba(168,85,247,0.3)"
          }}>🔀</div>
          <div>
            <div style={{ color: "#f8fafc", fontWeight: 800, fontSize: 16, letterSpacing: "-0.01em" }}>
              Multi-Agent Execution DAG & Offline Replay
            </div>
            <div style={{ color: "#64748b", fontSize: 12 }}>
              Directed Topology · Deterministic Offline Replay · Local Impact Estimator
            </div>
          </div>
        </div>

        {/* Trace Selector */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>Select Trace:</span>
          <select
            value={selectedTraceId}
            onChange={(e) => setSelectedTraceId(e.target.value)}
            style={{
              background: "rgba(18,24,38,0.8)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#f8fafc",
              fontSize: 13,
              outline: "none",
              cursor: "pointer",
              minWidth: 280,
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
            {loading ? "Loading…" : "Refresh Graph"}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden" }}>
        {/* Canvas Area */}
        <div style={{ flex: 1, position: "relative", overflow: "auto", padding: 20 }}>
          {graph && graph.summary && (
            <div style={{
              position: "sticky", top: 0, zIndex: 10,
              background: "rgba(11,15,25,0.9)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 12, padding: "12px 24px",
              display: "flex", gap: 28, alignItems: "center",
              marginBottom: 20, backdropFilter: "blur(16px)",
              width: "fit-content",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)"
            }}>
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, letterSpacing: "0.05em" }}>TRACE STATUS</div>
                <div style={{
                  fontSize: 13, fontWeight: 800,
                  color: graph.summary.status === "success" ? "#22c55e" : "#ef4444"
                }}>{graph.summary.status.toUpperCase()}</div>
              </div>
              <div style={{ width: 1, height: 26, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, letterSpacing: "0.05em" }}>TOTAL NODES</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>{graph.summary.total_nodes}</div>
              </div>
              <div style={{ width: 1, height: 26, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, letterSpacing: "0.05em" }}>TOTAL COST</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#22d3ee" }}>${graph.summary.total_cost_usd.toFixed(4)}</div>
              </div>
              <div style={{ width: 1, height: 26, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, letterSpacing: "0.05em" }}>TOTAL TOKENS</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#a855f7" }}>{graph.summary.total_tokens.toLocaleString()}</div>
              </div>
              <div style={{ width: 1, height: 26, background: "rgba(255,255,255,0.1)" }} />
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, letterSpacing: "0.05em" }}>LATENCY</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>{graph.summary.total_duration_ms} ms</div>
              </div>
              {graph.summary.retry_count > 0 && (
                <>
                  <div style={{ width: 1, height: 26, background: "rgba(255,255,255,0.1)" }} />
                  <div>
                    <div style={{ fontSize: 10, color: "#f97316", fontWeight: 700, letterSpacing: "0.05em" }}>RETRY LOOPS</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#f97316" }}>{graph.summary.retry_count}</div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* SVG Canvas */}
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
                      boxShadow: isSelected ? `0 0 20px ${styleCfg.border}` : "0 4px 12px rgba(0,0,0,0.3)",
                      transition: "all 0.2s ease",
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
            <div style={{ padding: 60, color: "#64748b", textAlign: "center" }}>
              Select a trace above to load execution DAG topology.
            </div>
          )}
        </div>

        {/* Right Inspector Panel */}
        {selectedNodeId && (
          <div style={{
            width: 330,
            borderLeft: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(11,15,25,0.95)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 16,
            backdropFilter: "blur(16px)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 800, fontSize: 14, color: "#f8fafc" }}>Node Inspector</span>
              <button
                onClick={() => setSelectedNodeId(null)}
                style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}
              >×</button>
            </div>

            {loadingDetail ? (
              <div style={{ color: "#64748b", fontSize: 13 }}>Loading payload detail…</div>
            ) : nodeDetail ? (
              <>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>SPAN ID</div>
                <div style={{ fontSize: 12, fontFamily: "monospace", color: "#94a3b8", wordBreak: "break-all" }}>{nodeDetail.span_id}</div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>MODEL</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{nodeDetail.model_name || "N/A"}</div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>STATUS</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: nodeDetail.status === "success" ? "#22c55e" : "#ef4444" }}>
                      {(nodeDetail.status || "success").toUpperCase()}
                    </div>
                  </div>
                </div>

                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 8 }}>
                  <div style={{ fontSize: 10, color: "#64748b", marginBottom: 4, fontWeight: 700 }}>TOKENS & COST</div>
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    In: <strong style={{ color: "#e2e8f0" }}>{nodeDetail.tokens_input || 0}</strong> · Out: <strong style={{ color: "#e2e8f0" }}>{nodeDetail.tokens_output || 0}</strong>
                  </div>
                  <div style={{ fontSize: 12, color: "#22d3ee", marginTop: 2, fontWeight: 700 }}>
                    Cost: ${Number(nodeDetail.cost_usd || 0).toFixed(6)}
                  </div>
                </div>

                {/* Prompt Preview */}
                <div>
                  <div style={{ fontSize: 10, color: "#64748b", marginBottom: 6, fontWeight: 700 }}>PROMPT / PAYLOAD PREVIEW</div>
                  {nodeDetail.privacy_notice ? (
                    <div style={{
                      background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                      borderRadius: 8, padding: "10px 12px", color: "#f87171", fontSize: 12,
                    }}>
                      🔒 {nodeDetail.privacy_notice}
                    </div>
                  ) : nodeDetail.payload_preview ? (
                    <div style={{
                      background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.08)",
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

                {/* Offline Replay & What-If Action Buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                  <button
                    onClick={handleTriggerReplay}
                    style={{
                      background: "linear-gradient(135deg, rgba(168,85,247,0.2), rgba(147,51,234,0.2))",
                      border: "1px solid #a855f7",
                      color: "#e9d5ff",
                      borderRadius: 8,
                      padding: "10px 14px",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                      boxShadow: "0 4px 12px rgba(168,85,247,0.25)"
                    }}
                  >
                    ⏳ Trigger Offline Replay
                  </button>

                  <button
                    onClick={openWhatIfModal}
                    style={{
                      background: "linear-gradient(135deg, rgba(6,182,212,0.2), rgba(14,165,233,0.2))",
                      border: "1px solid #06b6d4",
                      color: "#cffaffe0",
                      borderRadius: 8,
                      padding: "10px 14px",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                      boxShadow: "0 4px 12px rgba(6,182,212,0.25)"
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

      {/* ─── CUSTOM REPLAY MODAL ─────────────────────────────────────────────── */}
      {replayModalOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 20
        }}>
          <div style={{
            background: "#0f172a", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 16, width: "100%", maxWidth: 480, padding: 24,
            boxShadow: "0 20px 50px rgba(0,0,0,0.6)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 20 }}>⏳</span>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Deterministic Offline Replay</h3>
              </div>
              <button onClick={() => setReplayModalOpen(false)} style={{ background: "none", border: "none", color: "#64748b", fontSize: 20, cursor: "pointer" }}>×</button>
            </div>

            {replayLoading ? (
              <div style={{ padding: "30px 0", textAlign: "center", color: "#94a3b8", fontSize: 14 }}>
                Executing 100% mocked offline trace replay…
              </div>
            ) : replayResult ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{
                  background: replayResult.status === "COMPLETED" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                  border: `1px solid ${replayResult.status === "COMPLETED" ? "#22c55e" : "#ef4444"}`,
                  borderRadius: 10, padding: 14, display: "flex", justifyContent: "space-between", alignItems: "center"
                }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700 }}>REPLAY STATUS</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: replayResult.status === "COMPLETED" ? "#4ade80" : "#f87171" }}>
                      {replayResult.status}
                    </div>
                  </div>
                  <span style={{
                    background: "rgba(255,255,255,0.06)", padding: "4px 10px", borderRadius: 6,
                    fontSize: 11, fontFamily: "monospace", color: "#a855f7"
                  }}>
                    {replayResult.replay_id.slice(0, 14)}…
                  </span>
                </div>

                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 14 }}>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
                    Reason: <strong style={{ color: "#e2e8f0" }}>{replayResult.reason}</strong>
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    Executed Nodes: <strong style={{ color: "#a855f7" }}>{replayResult.executed_nodes_count}</strong>
                  </div>
                  <div style={{ fontSize: 12, color: "#22d3ee", marginTop: 4, fontWeight: 700 }}>
                    Cost: $0.0000 (100% Mocked Deterministic Replay)
                  </div>
                </div>

                <button
                  onClick={() => setReplayModalOpen(false)}
                  style={{
                    background: "linear-gradient(135deg, #a855f7, #06b6d4)", border: "none",
                    borderRadius: 8, padding: "10px", color: "#fff", fontWeight: 700, cursor: "pointer", marginTop: 6
                  }}
                >
                  Close
                </button>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ─── CUSTOM WHAT-IF ESTIMATOR MODAL ─────────────────────────────────── */}
      {whatIfModalOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 20
        }}>
          <div style={{
            background: "#0f172a", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 16, width: "100%", maxWidth: 560, padding: 24,
            boxShadow: "0 20px 50px rgba(0,0,0,0.6)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 20 }}>🔮</span>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Local Impact Estimator ("What-If")</h3>
              </div>
              <button onClick={() => setWhatIfModalOpen(false)} style={{ background: "none", border: "none", color: "#64748b", fontSize: 20, cursor: "pointer" }}>×</button>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>
                CANDIDATE MODIFIED PROMPT / SYSTEM TEXT
              </label>
              <textarea
                rows={3}
                value={whatIfInputText}
                onChange={(e) => setWhatIfInputText(e.target.value)}
                style={{
                  width: "100%", background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8, padding: 10, color: "#fff", fontSize: 12, fontFamily: "monospace", outline: "none"
                }}
              />
            </div>

            <button
              onClick={handleEvaluateWhatIf}
              disabled={whatIfLoading}
              style={{
                width: "100%", background: "linear-gradient(135deg, #06b6d4, #6366f1)",
                border: "none", borderRadius: 8, padding: "10px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer"
              }}
            >
              {whatIfLoading ? "Estimating Local Metric Deltas…" : "Evaluate Candidate Prompt"}
            </button>

            {whatIfResult && (
              <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{
                  background: "rgba(6,182,212,0.1)", border: "1px solid #06b6d4",
                  borderRadius: 10, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center"
                }}>
                  <span style={{ fontWeight: 800, color: "#67e8f9", fontSize: 13 }}>{whatIfResult.label}</span>
                  <span style={{ fontSize: 10, color: "#94a3b8" }}>No Live Execution Performed</span>
                </div>

                {/* Metric Comparison Cards */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 10, textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>FAITHFULNESS</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#e2e8f0", margin: "4px 0" }}>{whatIfResult.what_if.faithfulness_score}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: whatIfResult.delta.faithfulness >= 0 ? "#22c55e" : "#ef4444" }}>
                      {whatIfResult.delta.faithfulness >= 0 ? `+${whatIfResult.delta.faithfulness}` : whatIfResult.delta.faithfulness}
                    </div>
                  </div>

                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 10, textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>UNSUPPORTED RATIO</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#e2e8f0", margin: "4px 0" }}>{whatIfResult.what_if.unsupported_claim_ratio}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: whatIfResult.delta.unsupported_claim_ratio <= 0 ? "#22c55e" : "#ef4444" }}>
                      {whatIfResult.delta.unsupported_claim_ratio > 0 ? `+${whatIfResult.delta.unsupported_claim_ratio}` : whatIfResult.delta.unsupported_claim_ratio}
                    </div>
                  </div>

                  <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 10, textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700 }}>SECURITY RISK</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#e2e8f0", margin: "4px 0" }}>{whatIfResult.what_if.security_risk}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: whatIfResult.delta.security_risk <= 0 ? "#22c55e" : "#ef4444" }}>
                      {whatIfResult.delta.security_risk > 0 ? `+${whatIfResult.delta.security_risk}` : whatIfResult.delta.security_risk}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: 11, color: "#64748b", fontStyle: "italic", textAlign: "center" }}>
                  {whatIfResult.disclaimer}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
