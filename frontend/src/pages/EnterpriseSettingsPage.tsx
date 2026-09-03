import { useState, useEffect } from "react";
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
  chain_valid: bool;
  chain_errors: string[];
  logs: AuditLogItem[];
}

export default function EnterpriseSettingsPage() {
  const [activeTab, setActiveTab] = useState<"api_keys" | "audit">("api_keys");
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [auditData, setAuditData] = useState<AuditLogResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // New key form state
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("developer");
  const [projectScope, setProjectScope] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);

  const fetchKeys = () => {
    setLoading(true);
    axios.get<ApiKeyItem[]>(`${API_BASE}/api-keys`, { headers })
      .then((res) => setApiKeys(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const fetchAuditLogs = () => {
    setLoading(true);
    axios.get<AuditLogResponse>(`${API_BASE}/audit/logs`, { headers })
      .then((res) => setAuditData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (activeTab === "api_keys") fetchKeys();
    else fetchAuditLogs();
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
    if (!confirm(`Are you sure you want to revoke API Key ${keyId}?`)) return;
    try {
      await axios.delete(`${API_BASE}/api-keys/${keyId}`, { headers });
      fetchKeys();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Key revocation failed");
    }
  };

  return (
    <div style={{
      minHeight: "calc(100vh - 65px)",
      background: "linear-gradient(135deg, #020617 0%, #0a0c1a 50%, #0d0a1a 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
      color: "#e2e8f0",
      padding: 30,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyBetween: "space-between", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 42, height: 42, borderRadius: 12,
            background: "linear-gradient(135deg, #6366f1, #a855f7)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22,
          }}>⚙️</div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#f8fafc" }}>Enterprise Control & Compliance</div>
            <div style={{ fontSize: 13, color: "#64748b" }}>API Key Management · Scope-Aware RBAC · Tamper-Evident Audit Trail</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 12 }}>
        <button
          onClick={() => setActiveTab("api_keys")}
          style={{
            background: activeTab === "api_keys" ? "rgba(99,102,241,0.2)" : "transparent",
            border: activeTab === "api_keys" ? "1px solid #6366f1" : "1px solid transparent",
            color: activeTab === "api_keys" ? "#fff" : "#94a3b8",
            borderRadius: 8, padding: "8px 18px", fontWeight: 600, fontSize: 13, cursor: "pointer"
          }}
        >
          🔑 API Keys & RBAC
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          style={{
            background: activeTab === "audit" ? "rgba(168,85,247,0.2)" : "transparent",
            border: activeTab === "audit" ? "1px solid #a855f7" : "1px solid transparent",
            color: activeTab === "audit" ? "#fff" : "#94a3b8",
            borderRadius: 8, padding: "8px 18px", fontWeight: 600, fontSize: 13, cursor: "pointer"
          }}
        >
          🛡️ Compliance Audit Log
        </button>
      </div>

      {activeTab === "api_keys" ? (
        <div>
          {/* Create Key Form */}
          <div style={{
            background: "rgba(15,23,42,0.8)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 12, padding: 20, marginBottom: 24, backdropFilter: "blur(12px)"
          }}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: 15, fontWeight: 700, color: "#e2e8f0" }}>Generate New API Key</h3>
            <form onSubmit={handleCreateKey} style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", marginBottom: 4 }}>KEY NAME</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production CI Runner"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  style={{
                    background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8, padding: "8px 12px", color: "#fff", fontSize: 13, width: 220, outline: "none"
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", marginBottom: 4 }}>ROLE</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  style={{
                    background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8, padding: "8px 12px", color: "#fff", fontSize: 13, width: 140, outline: "none"
                  }}
                >
                  <option value="developer" style={{ background: "#0f172a" }}>Developer</option>
                  <option value="viewer" style={{ background: "#0f172a" }}>Viewer</option>
                  <option value="admin" style={{ background: "#0f172a" }}>Admin</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", marginBottom: 4 }}>PROJECT SCOPE (OPTIONAL)</label>
                <input
                  type="text"
                  placeholder="e.g. search-v2 (blank = global)"
                  value={projectScope}
                  onChange={(e) => setProjectScope(e.target.value)}
                  style={{
                    background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8, padding: "8px 12px", color: "#fff", fontSize: 13, width: 220, outline: "none"
                  }}
                />
              </div>

              <button
                type="submit"
                style={{
                  background: "linear-gradient(135deg, #6366f1, #a855f7)", border: "none",
                  borderRadius: 8, padding: "9px 20px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer"
                }}
              >
                + Generate Key
              </button>
            </form>

            {createdSecret && (
              <div style={{
                marginTop: 16, background: "rgba(34,197,94,0.1)", border: "1px solid #22c55e",
                borderRadius: 8, padding: 14, color: "#4ade80", fontSize: 13
              }}>
                <div style={{ fontWeight: 700, marginBottom: 4 }}>⚠️ SAVE YOUR PLAINTEXT KEY NOW:</div>
                <div style={{ fontFamily: "monospace", fontSize: 14, background: "rgba(0,0,0,0.4)", padding: 8, borderRadius: 6 }}>
                  {createdSecret}
                </div>
                <div style={{ fontSize: 11, color: "#86efac", marginTop: 4 }}>
                  This secret will NEVER be displayed again.
                </div>
              </div>
            )}
          </div>

          {/* API Key List Table */}
          <div style={{ background: "rgba(15,23,42,0.8)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 20 }}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: 15, fontWeight: 700 }}>Active & Revoked API Keys</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                  <th style={{ padding: 10 }}>KEY ID</th>
                  <th style={{ padding: 10 }}>NAME</th>
                  <th style={{ padding: 10 }}>ROLE</th>
                  <th style={{ padding: 10 }}>SCOPE</th>
                  <th style={{ padding: 10 }}>STATUS</th>
                  <th style={{ padding: 10 }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.map((k) => (
                  <tr key={k.key_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: 10, fontFamily: "monospace", color: "#94a3b8" }}>{k.key_id}</td>
                    <td style={{ padding: 10, fontWeight: 600 }}>{k.display_name}</td>
                    <td style={{ padding: 10 }}>
                      <span style={{
                        background: k.role === "admin" ? "rgba(239,68,68,0.2)" : "rgba(99,102,241,0.2)",
                        color: k.role === "admin" ? "#f87171" : "#818cf8",
                        padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700,
                      }}>
                        {k.role.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 10, color: "#cbd5e1" }}>{k.project_id || "Global"}</td>
                    <td style={{ padding: 10 }}>
                      <span style={{ color: k.status === "active" ? "#22c55e" : "#ef4444", fontWeight: 700 }}>
                        {k.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 10 }}>
                      {k.status === "active" && (
                        <button
                          onClick={() => handleRevokeKey(k.key_id)}
                          style={{
                            background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444",
                            color: "#f87171", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer"
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
      ) : (
        /* Audit Log Tab */
        <div style={{ background: "rgba(15,23,42,0.8)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 20 }}>
          {auditData && (
            <div style={{
              background: auditData.chain_valid ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
              border: `1px solid ${auditData.chain_valid ? "#22c55e" : "#ef4444"}`,
              borderRadius: 10, padding: "12px 16px", marginBottom: 20,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <div>
                <div style={{ fontWeight: 700, color: auditData.chain_valid ? "#4ade80" : "#f87171", fontSize: 14 }}>
                  {auditData.chain_valid ? "🛡️ Hash Chain Integrity Verified & Intact" : "⚠️ Cryptographic Tampering Detected!"}
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                  SHA-256 Hash Chain verification computed across {auditData.total_logs} audit entries using 'GENESIS' root seed.
                </div>
              </div>
              <span style={{
                background: auditData.chain_valid ? "#22c55e" : "#ef4444",
                color: "#fff", padding: "4px 10px", borderRadius: 6, fontWeight: 700, fontSize: 11
              }}>
                {auditData.chain_valid ? "VALID" : "CORRUPTED"}
              </span>
            </div>
          )}

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                <th style={{ padding: 8 }}>ID</th>
                <th style={{ padding: 8 }}>TIMESTAMP</th>
                <th style={{ padding: 8 }}>ACTOR</th>
                <th style={{ padding: 8 }}>ACTION</th>
                <th style={{ padding: 8 }}>RESOURCE</th>
                <th style={{ padding: 8 }}>RECORD HASH</th>
              </tr>
            </thead>
            <tbody>
              {auditData?.logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: 8, color: "#64748b" }}>#{log.id}</td>
                  <td style={{ padding: 8, color: "#cbd5e1" }}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td style={{ padding: 8, fontFamily: "monospace", color: "#a855f7" }}>{log.actor_key_id}</td>
                  <td style={{ padding: 8, fontWeight: 700, color: "#38bdf8" }}>{log.action}</td>
                  <td style={{ padding: 8, color: "#94a3b8" }}>{log.resource_type}:{log.resource_id || "global"}</td>
                  <td style={{ padding: 8, fontFamily: "monospace", color: "#64748b", fontSize: 11 }}>
                    {log.record_hash.slice(0, 16)}…
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
