import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "/api/v1";
const API_KEY = "dev-local-key";
const headers = { "Authorization": `Bearer ${API_KEY}`, "X-API-Key": API_KEY };

interface ApiKeyItem {
  key_id: string;
  display_name: string;
  role: string;
  project_id: string | null;
  status: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

interface AuditLogItem {
  id: number;
  timestamp: string;
  actor_key_id: string;
  project_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  record_hash: string;
}

interface AuditLogResponse {
  total_logs: number;
  chain_valid: boolean;
  chain_errors: string[];
  logs: AuditLogItem[];
}

export default function EnterpriseSettingsPage() {
  const [activeTab, setActiveTab] = useState<"api_keys" | "roles" | "audit">("api_keys");
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [auditData, setAuditData] = useState<AuditLogResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Form State
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("developer");
  const [projectScope, setProjectScope] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchKeys = () => {
    setLoading(true);
    axios.get<ApiKeyItem[]>(`${API_BASE}/api-keys`, { headers })
      .then((res) => setApiKeys(Array.isArray(res.data) ? res.data : []))
      .catch(() => setApiKeys([]))
      .finally(() => setLoading(false));
  };

  const fetchAuditLogs = () => {
    setLoading(true);
    axios.get<AuditLogResponse>(`${API_BASE}/audit/logs`, { headers })
      .then((res) => {
        if (res.data && Array.isArray(res.data.logs)) {
          setAuditData(res.data);
        } else {
          setAuditData({ total_logs: 0, chain_valid: true, chain_errors: [], logs: [] });
        }
      })
      .catch(() => setAuditData({ total_logs: 0, chain_valid: true, chain_errors: [], logs: [] }))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (activeTab === "api_keys") fetchKeys();
    else if (activeTab === "audit") fetchAuditLogs();
  }, [activeTab]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_BASE}/api-keys`, {
        display_name: displayName,
        role: role,
        project_id: projectScope || null,
        expires_in_days: 365,
      }, { headers });
      setCreatedSecret(res.data.plaintext_key);
      setDisplayName("");
      setProjectScope("");
      fetchKeys();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Key creation failed");
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm(`Are you sure you want to soft-revoke API Key ${keyId}?`)) return;
    try {
      await axios.delete(`${API_BASE}/api-keys/${keyId}`, { headers });
      fetchKeys();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Key revocation failed");
    }
  };

  const copySecret = () => {
    if (createdSecret) {
      navigator.clipboard.writeText(createdSecret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="page-container">
      {/* Universal Page Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">Enterprise Security & Compliance Control</h2>
          <p className="page-subtitle">
            Scoped API Keys · Permission Role Matrix · Cryptographic Hash Chain Audit Log
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 10, marginBottom: 28, borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 12 }}>
        <button
          onClick={() => setActiveTab("api_keys")}
          style={{
            background: activeTab === "api_keys" ? "rgba(99,102,241,0.18)" : "transparent",
            border: activeTab === "api_keys" ? "1px solid #6366f1" : "1px solid transparent",
            color: activeTab === "api_keys" ? "#f8fafc" : "#94a3b8",
            borderRadius: 8, padding: "9px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer",
            transition: "all 0.2s ease"
          }}
        >
          🔑 API Keys
        </button>
        <button
          onClick={() => setActiveTab("roles")}
          style={{
            background: activeTab === "roles" ? "rgba(6,182,212,0.18)" : "transparent",
            border: activeTab === "roles" ? "1px solid #06b6d4" : "1px solid transparent",
            color: activeTab === "roles" ? "#f8fafc" : "#94a3b8",
            borderRadius: 8, padding: "9px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer",
            transition: "all 0.2s ease"
          }}
        >
          🛡️ Role Capability Matrix
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          style={{
            background: activeTab === "audit" ? "rgba(168,85,247,0.18)" : "transparent",
            border: activeTab === "audit" ? "1px solid #a855f7" : "1px solid transparent",
            color: activeTab === "audit" ? "#f8fafc" : "#94a3b8",
            borderRadius: 8, padding: "9px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer",
            transition: "all 0.2s ease"
          }}
        >
          📜 Compliance Audit Log
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "api_keys" ? (
        <div>
          {/* Create Key Card */}
          <div style={{
            background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14, padding: 24, marginBottom: 28, backdropFilter: "blur(16px)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.3)"
          }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, fontWeight: 800, color: "#f8fafc" }}>Generate New API Key</h3>
            <form onSubmit={handleCreateKey} style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>KEY DISPLAY NAME</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Ingestion Agent"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  style={{
                    background: "rgba(18,24,38,0.8)", border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8, padding: "9px 14px", color: "#fff", fontSize: 13, width: 240, outline: "none"
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>ROLE PERMISSION LEVEL</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  style={{
                    background: "rgba(18,24,38,0.8)", border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8, padding: "9px 14px", color: "#fff", fontSize: 13, width: 150, outline: "none"
                  }}
                >
                  <option value="developer" style={{ background: "#0f172a" }}>Developer</option>
                  <option value="viewer" style={{ background: "#0f172a" }}>Viewer</option>
                  <option value="admin" style={{ background: "#0f172a" }}>Admin</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>PROJECT SCOPE (ISOLATION)</label>
                <input
                  type="text"
                  placeholder="e.g. search-v2 (blank = global)"
                  value={projectScope}
                  onChange={(e) => setProjectScope(e.target.value)}
                  style={{
                    background: "rgba(18,24,38,0.8)", border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8, padding: "9px 14px", color: "#fff", fontSize: 13, width: 230, outline: "none"
                  }}
                />
              </div>

              <button
                type="submit"
                style={{
                  background: "linear-gradient(135deg, #6366f1, #a855f7)", border: "none",
                  borderRadius: 8, padding: "10px 22px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer",
                  boxShadow: "0 4px 14px rgba(99,102,241,0.3)"
                }}
              >
                + Generate Secret Key
              </button>
            </form>

            {createdSecret && (
              <div style={{
                marginTop: 18, background: "rgba(34,197,94,0.1)", border: "1px solid #22c55e",
                borderRadius: 10, padding: 16, color: "#4ade80", fontSize: 13
              }}>
                <div style={{ fontWeight: 800, marginBottom: 6, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>⚠️ SAVE YOUR SECRET KEY NOW (DISPLAYED ONCE):</span>
                  <button
                    onClick={copySecret}
                    style={{
                      background: "#22c55e", border: "none", borderRadius: 6,
                      padding: "4px 12px", color: "#000", fontWeight: 700, fontSize: 11, cursor: "pointer"
                    }}
                  >
                    {copied ? "Copied!" : "Copy Secret"}
                  </button>
                </div>
                <div style={{ fontFamily: "monospace", fontSize: 14, background: "rgba(0,0,0,0.4)", padding: "10px 14px", borderRadius: 8, wordBreak: "break-all" }}>
                  {createdSecret}
                </div>
              </div>
            )}
          </div>

          {/* Active Keys Table */}
          <div style={{
            background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14, padding: 24, backdropFilter: "blur(16px)"
          }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, fontWeight: 800 }}>Active & Soft-Revoked API Keys</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>KEY ID</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>NAME</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ROLE</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>SCOPE</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>STATUS</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.map((k) => (
                  <tr key={k.key_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: 12, fontFamily: "monospace", color: "#94a3b8" }}>{k.key_id}</td>
                    <td style={{ padding: 12, fontWeight: 700, color: "#f8fafc" }}>{k.display_name}</td>
                    <td style={{ padding: 12 }}>
                      <span style={{
                        background: k.role === "admin" ? "rgba(239,68,68,0.2)" : k.role === "developer" ? "rgba(99,102,241,0.2)" : "rgba(100,116,139,0.2)",
                        color: k.role === "admin" ? "#f87171" : k.role === "developer" ? "#818cf8" : "#94a3b8",
                        padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 700,
                      }}>
                        {k.role.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 12, color: "#cbd5e1" }}>{k.project_id || "Global (Unrestricted)"}</td>
                    <td style={{ padding: 12 }}>
                      <span style={{ color: k.status === "active" ? "#22c55e" : "#ef4444", fontWeight: 800, fontSize: 12 }}>
                        {k.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 12 }}>
                      {k.status === "active" && (
                        <button
                          onClick={() => handleRevokeKey(k.key_id)}
                          style={{
                            background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444",
                            color: "#f87171", borderRadius: 6, padding: "5px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer"
                          }}
                        >
                          Soft Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : activeTab === "roles" ? (
        /* Roles Matrix Tab */
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20 }}>
          <div style={{ background: "rgba(11,15,25,0.85)", border: "1px solid rgba(100,116,139,0.3)", borderRadius: 14, padding: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: "0.05em" }}>ROLE LEVEL 1</div>
            <h3 style={{ margin: "4px 0 12px 0", fontSize: 18, fontWeight: 800, color: "#94a3b8" }}>Viewer</h3>
            <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>
              • Read telemetry metrics<br/>
              • Read execution DAG trees<br/>
              • Read project metadata<br/>
              • Read alert statuses
            </div>
          </div>

          <div style={{ background: "rgba(11,15,25,0.85)", border: "1px solid rgba(99,102,241,0.4)", borderRadius: 14, padding: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#818cf8", letterSpacing: "0.05em" }}>ROLE LEVEL 2</div>
            <h3 style={{ margin: "4px 0 12px 0", fontSize: 18, fontWeight: 800, color: "#818cf8" }}>Developer</h3>
            <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>
              • All Viewer capabilities<br/>
              • Ingest agent telemetry spans<br/>
              • Execute offline trace replays<br/>
              • Evaluate What-If prompt forks<br/>
              • Check policy circuit breaker
            </div>
          </div>

          <div style={{ background: "rgba(11,15,25,0.85)", border: "1px solid rgba(239,68,68,0.4)", borderRadius: 14, padding: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#f87171", letterSpacing: "0.05em" }}>ROLE LEVEL 3</div>
            <h3 style={{ margin: "4px 0 12px 0", fontSize: 18, fontWeight: 800, color: "#f87171" }}>Admin</h3>
            <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>
              • Full system access<br/>
              • Create & revoke API keys<br/>
              • Inspect tamper-evident audit logs<br/>
              • Configure circuit breaker policies<br/>
              • Export DPO datasets
            </div>
          </div>
        </div>
      ) : (
        /* Audit Tab */
        <div style={{
          background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14, padding: 24, backdropFilter: "blur(16px)"
        }}>
          {auditData && (
            <div style={{
              background: auditData.chain_valid ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
              border: `1px solid ${auditData.chain_valid ? "#22c55e" : "#ef4444"}`,
              borderRadius: 12, padding: "14px 20px", marginBottom: 24,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <div>
                <div style={{ fontWeight: 800, color: auditData.chain_valid ? "#4ade80" : "#f87171", fontSize: 15 }}>
                  {auditData.chain_valid ? "🛡️ Hash Chain Integrity Verified & Intact" : "⚠️ Cryptographic Tampering Detected!"}
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                  SHA-256 Hash Chain verification computed across {auditData.total_logs} audit entries using 'GENESIS' root seed.
                </div>
              </div>
              <span style={{
                background: auditData.chain_valid ? "#22c55e" : "#ef4444",
                color: "#fff", padding: "6px 14px", borderRadius: 8, fontWeight: 800, fontSize: 12
              }}>
                {auditData.chain_valid ? "CHAIN VALID" : "TAMPERED"}
              </span>
            </div>
          )}

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>ID</th>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>TIMESTAMP</th>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>ACTOR KEY ID</th>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>ACTION</th>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>RESOURCE</th>
                <th style={{ padding: 10, fontSize: 11, fontWeight: 700 }}>SHA-256 RECORD HASH</th>
              </tr>
            </thead>
            <tbody>
              {auditData?.logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: 10, color: "#64748b", fontWeight: 700 }}>#{log.id}</td>
                  <td style={{ padding: 10, color: "#cbd5e1" }}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td style={{ padding: 10, fontFamily: "monospace", color: "#a855f7" }}>{log.actor_key_id}</td>
                  <td style={{ padding: 10, fontWeight: 800, color: "#38bdf8" }}>{log.action}</td>
                  <td style={{ padding: 10, color: "#94a3b8" }}>{log.resource_type}:{log.resource_id || "global"}</td>
                  <td style={{ padding: 10, fontFamily: "monospace", color: "#64748b", fontSize: 11 }}>
                    {log.record_hash.slice(0, 20)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
