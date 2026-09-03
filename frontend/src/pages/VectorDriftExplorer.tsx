import { useRef, useState, useEffect, Suspense, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Stars } from "@react-three/drei";
import * as THREE from "three";
import axios from "axios";

const API_BASE = "/api/v1";
const API_KEY = "dev-local-key";
const headers = { "X-API-Key": API_KEY };

// ─── Types ───────────────────────────────────────────────────────────────────

interface VectorPoint {
  trace_id: string;
  x: number;
  y: number;
  z: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  threat_score: number;
}

interface DriftMetrics {
  baseline_centroid: number[];
  current_centroid: number[];
  centroid_shift_distance: number;
  drift_score: number;
  drift_status: "ok" | "moderate_drift" | "significant_drift" | "insufficient_data";
  baseline_count: number;
  current_count: number;
}

interface VectorDriftData {
  points: VectorPoint[];
  drift_metrics: DriftMetrics;
  total_traces: number;
}

// ─── Colour mapping ───────────────────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  LOW: "#22d3ee",
  MEDIUM: "#facc15",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

const getRiskColor = (risk: string) =>
  RISK_COLORS[risk] ?? RISK_COLORS["LOW"];

// ─── Drift status badge config ────────────────────────────────────────────────

const DRIFT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  ok: { label: "Stable", color: "#22d3ee", bg: "rgba(34,211,238,0.1)" },
  moderate_drift: { label: "Moderate Drift", color: "#facc15", bg: "rgba(250,204,21,0.1)" },
  significant_drift: { label: "Significant Drift", color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  insufficient_data: { label: "Insufficient Data", color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
};

// ─── Single 3D point ─────────────────────────────────────────────────────────

function TracePoint({
  point,
  selected,
  onClick,
}: {
  point: VectorPoint;
  selected: boolean;
  onClick: (p: VectorPoint) => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const color = getRiskColor(point.risk_level);

  useFrame((_, delta) => {
    if (meshRef.current && selected) {
      meshRef.current.rotation.y += delta * 2;
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={[point.x * 8, point.y * 8, point.z * 8]}
      onClick={(e) => { e.stopPropagation(); onClick(point); }}
    >
      <sphereGeometry args={[selected ? 0.18 : 0.10, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={selected ? 0.9 : 0.4}
        transparent
        opacity={selected ? 1.0 : 0.82}
      />
    </mesh>
  );
}

// ─── Centroid markers ─────────────────────────────────────────────────────────

function CentroidMarker({
  position,
  color,
  label,
}: {
  position: [number, number, number];
  color: string;
  label: string;
}) {
  return (
    <mesh position={position}>
      <octahedronGeometry args={[0.28, 0]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.7} wireframe />
      <Html distanceFactor={10}>
        <div style={{
          background: "rgba(10,10,20,0.85)",
          border: `1px solid ${color}`,
          borderRadius: 6,
          padding: "2px 8px",
          fontSize: 11,
          color,
          whiteSpace: "nowrap",
          backdropFilter: "blur(4px)",
        }}>
          {label}
        </div>
      </Html>
    </mesh>
  );
}

// ─── Axis lines ───────────────────────────────────────────────────────────────

function AxisLines() {
  const len = 6;
  const axes = [
    { dir: [len, 0, 0] as [number, number, number], color: "#ef4444" },
    { dir: [0, len, 0] as [number, number, number], color: "#22d3ee" },
    { dir: [0, 0, len] as [number, number, number], color: "#a855f7" },
  ];
  return (
    <>
      {axes.map(({ dir, color }, i) => {
        const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(...dir)];
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        const mat = new THREE.LineBasicMaterial({ color, opacity: 0.35, transparent: true });
        const lineObj = new THREE.Line(geo, mat);
        return <primitive key={i} object={lineObj} />;
      })}
    </>
  );
}

// ─── Main scene ───────────────────────────────────────────────────────────────

function Scene({
  points,
  driftMetrics,
  onSelect,
  selected,
}: {
  points: VectorPoint[];
  driftMetrics: DriftMetrics;
  onSelect: (p: VectorPoint | null) => void;
  selected: VectorPoint | null;
}) {
  const baseC = driftMetrics.baseline_centroid;
  const curC = driftMetrics.current_centroid;
  const hasCentroids = baseC.length === 3 && curC.length === 3;

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#7c3aed" />
      <Stars radius={60} depth={40} count={800} factor={3} fade />
      <AxisLines />

      {hasCentroids && (
        <>
          <CentroidMarker
            position={[baseC[0] * 8, baseC[1] * 8, baseC[2] * 8]}
            color="#22d3ee"
            label="Baseline Centroid"
          />
          <CentroidMarker
            position={[curC[0] * 8, curC[1] * 8, curC[2] * 8]}
            color="#f97316"
            label="Current Centroid"
          />
        </>
      )}

      {points.map((p) => (
        <TracePoint
          key={p.trace_id}
          point={p}
          selected={selected?.trace_id === p.trace_id}
          onClick={onSelect}
        />
      ))}

      <OrbitControls enablePan enableZoom enableRotate makeDefault />
    </>
  );
}

// ─── Inspector panel ──────────────────────────────────────────────────────────

function InspectorPanel({
  point,
  onClose,
}: {
  point: VectorPoint;
  onClose: () => void;
}) {
  const riskColor = getRiskColor(point.risk_level);
  return (
    <div style={{
      position: "absolute",
      top: 16,
      right: 16,
      width: 280,
      background: "rgba(10,12,26,0.92)",
      border: `1px solid ${riskColor}`,
      borderRadius: 12,
      padding: "16px 20px",
      backdropFilter: "blur(16px)",
      zIndex: 10,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ color: "#e2e8f0", fontWeight: 700, fontSize: 14 }}>Trace Inspector</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}>×</button>
      </div>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>TRACE ID</div>
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 12, wordBreak: "break-all", fontFamily: "monospace" }}>{point.trace_id}</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 12 }}>
        {[["X", point.x], ["Y", point.y], ["Z", point.z]].map(([axis, val]) => (
          <div key={String(axis)} style={{ textAlign: "center", background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "6px 4px" }}>
            <div style={{ fontSize: 10, color: "#64748b" }}>{axis}</div>
            <div style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 600 }}>{Number(val).toFixed(3)}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "8px 10px" }}>
          <div style={{ fontSize: 10, color: "#64748b", marginBottom: 2 }}>RISK</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: riskColor }}>{point.risk_level}</div>
        </div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "8px 10px" }}>
          <div style={{ fontSize: 10, color: "#64748b", marginBottom: 2 }}>THREAT</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: riskColor }}>{(point.threat_score * 100).toFixed(0)}%</div>
        </div>
      </div>
    </div>
  );
}

// ─── Drift Index Banner ───────────────────────────────────────────────────────

function DriftBanner({ metrics }: { metrics: DriftMetrics }) {
  const cfg = DRIFT_CONFIG[metrics.drift_status] ?? DRIFT_CONFIG.ok;
  const pct = Math.round(metrics.drift_score * 100);

  return (
    <div style={{
      position: "absolute",
      top: 72,
      left: "50%",
      transform: "translateX(-50%)",
      background: cfg.bg,
      border: `1px solid ${cfg.color}`,
      borderRadius: 12,
      padding: "10px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
      backdropFilter: "blur(16px)",
      zIndex: 10,
      minWidth: 360,
    }}>
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>VECTOR DRIFT INDEX</div>
        <div style={{ fontSize: 22, fontWeight: 800, color: cfg.color }}>{pct}%</div>
      </div>
      <div style={{ width: 1, height: 36, background: "rgba(255,255,255,0.1)" }} />
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>STATUS</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: cfg.color }}>{cfg.label}</div>
      </div>
      <div style={{ width: 1, height: 36, background: "rgba(255,255,255,0.1)" }} />
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>CENTROID SHIFT</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>{metrics.centroid_shift_distance.toFixed(4)}</div>
      </div>
      <div style={{ width: 1, height: 36, background: "rgba(255,255,255,0.1)" }} />
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>TRACES</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>
          {metrics.baseline_count}b / {metrics.current_count}c
        </div>
      </div>
    </div>
  );
}

// ─── Legend ───────────────────────────────────────────────────────────────────

function Legend() {
  return (
    <div style={{
      position: "absolute",
      bottom: 20,
      left: 20,
      background: "rgba(10,12,26,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 10,
      padding: "12px 16px",
      zIndex: 10,
      backdropFilter: "blur(12px)",
    }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8, fontWeight: 600 }}>RISK LEVEL</div>
      {Object.entries(RISK_COLORS).map(([level, color]) => (
        <div key={level} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, boxShadow: `0 0 6px ${color}` }} />
          <span style={{ fontSize: 12, color: "#94a3b8" }}>{level}</span>
        </div>
      ))}
      <div style={{ marginTop: 10, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 8 }}>
        {[{ color: "#22d3ee", label: "Baseline Centroid" }, { color: "#f97316", label: "Current Centroid" }].map(({ color, label }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <div style={{ width: 10, height: 10, background: "none", border: `2px solid ${color}`, transform: "rotate(45deg)" }} />
            <span style={{ fontSize: 12, color: "#94a3b8" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────

function StatsBar({ total, baselineCount, currentCount }: { total: number; baselineCount: number; currentCount: number }) {
  return (
    <div style={{
      position: "absolute",
      bottom: 20,
      right: 20,
      background: "rgba(10,12,26,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 10,
      padding: "12px 16px",
      zIndex: 10,
      backdropFilter: "blur(12px)",
      fontSize: 12,
      color: "#94a3b8",
      lineHeight: 1.8,
    }}>
      <div style={{ color: "#e2e8f0", fontWeight: 700, marginBottom: 6, fontSize: 11 }}>WINDOW INFO</div>
      <div>Total Traces: <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{total}</span></div>
      <div>Baseline: <span style={{ color: "#22d3ee", fontWeight: 600 }}>{baselineCount}</span></div>
      <div>Current: <span style={{ color: "#f97316", fontWeight: 600 }}>{currentCount}</span></div>
      <div style={{ marginTop: 6, fontSize: 10, color: "#475569" }}>
        Drag to rotate · Scroll to zoom
      </div>
    </div>
  );
}

// ─── Main page component ──────────────────────────────────────────────────────

export default function VectorDriftExplorer() {
  const [data, setData] = useState<VectorDriftData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<VectorPoint | null>(null);
  const [projectId, setProjectId] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ baseline_count: "100", current_count: "20" });
      if (projectId) params.set("project_id", projectId);
      const res = await axios.get<VectorDriftData>(
        `${API_BASE}/analytics/vector-drift?${params}`,
        { headers }
      );
      setData(res.data);
    } catch (e: unknown) {
      setError((e as Error).message || "Failed to fetch vector data");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div style={{
      position: "relative",
      minHeight: "calc(100vh - 65px)",
      height: "calc(100vh - 65px)",
      background: "linear-gradient(135deg, #030712 0%, #0b0f19 50%, #0f172a 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      {/* Sub-Header Control Bar */}
      <div style={{
        padding: "12px 24px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(10,12,26,0.85)",
        backdropFilter: "blur(12px)",
        zIndex: 30,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18,
          }}>🌌</div>
          <div>
            <div style={{ color: "#e2e8f0", fontWeight: 800, fontSize: 16 }}>3D Vector Drift Explorer</div>
            <div style={{ color: "#475569", fontSize: 12 }}>TF-IDF · TruncatedSVD · Centroid Distribution Shift</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            placeholder="Filter by project ID..."
            value={projectId}
            onChange={e => setProjectId(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              padding: "7px 14px",
              color: "#e2e8f0",
              fontSize: 13,
              outline: "none",
              width: 200,
            }}
          />
          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
              border: "none",
              borderRadius: 8,
              padding: "8px 18px",
              color: "#fff",
              fontWeight: 600,
              fontSize: 13,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
              transition: "all 0.2s",
            }}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* Canvas area */}
      <div style={{ flex: 1, position: "relative" }}>
        {error ? (
          <div style={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center",
            justifyContent: "center", flexDirection: "column", gap: 12,
          }}>
            <div style={{ fontSize: 40 }}>⚠️</div>
            <div style={{ color: "#ef4444", fontSize: 16, fontWeight: 600 }}>{error}</div>
            <button onClick={fetchData} style={{
              background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444",
              borderRadius: 8, padding: "8px 20px", color: "#ef4444",
              cursor: "pointer", fontWeight: 600, fontSize: 14,
            }}>Retry</button>
          </div>
        ) : loading && !data ? (
          <div style={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center",
            justifyContent: "center", flexDirection: "column", gap: 16,
          }}>
            <div style={{
              width: 48, height: 48, border: "3px solid rgba(124,58,237,0.2)",
              borderTopColor: "#7c3aed", borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
            }} />
            <div style={{ color: "#64748b", fontSize: 14 }}>Computing vector projections…</div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        ) : data ? (
          <>
            <DriftBanner metrics={data.drift_metrics} />
            <Legend />
            <StatsBar
              total={data.total_traces}
              baselineCount={data.drift_metrics.baseline_count}
              currentCount={data.drift_metrics.current_count}
            />
            {selected && (
              <InspectorPanel point={selected} onClose={() => setSelected(null)} />
            )}

            {/* Empty state */}
            {data.points.length === 0 && (
              <div style={{
                position: "absolute", inset: 0, display: "flex", alignItems: "center",
                justifyContent: "center", flexDirection: "column", gap: 12, zIndex: 5,
              }}>
                <div style={{ fontSize: 48 }}>🌌</div>
                <div style={{ color: "#94a3b8", fontSize: 16, fontWeight: 600 }}>No prompt data available</div>
                <div style={{ color: "#475569", fontSize: 13 }}>Ingest at least 40 traces to enable vector analysis</div>
              </div>
            )}

            <Canvas camera={{ position: [12, 8, 12], fov: 55 }} style={{ background: "transparent" }}>
              <Suspense fallback={null}>
                <Scene
                  points={data.points}
                  driftMetrics={data.drift_metrics}
                  onSelect={setSelected}
                  selected={selected}
                />
              </Suspense>
            </Canvas>
          </>
        ) : null}
      </div>
    </div>
  );
}
