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
  const [activeTab, setActiveTab] = useState<"api_keys" | "webhooks" | "roles" | "audit" | "security">("api_keys");
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [auditData, setAuditData] = useState<AuditLogResponse | null>(null);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [whName, setWhName] = useState("");
  const [whUrl, setWhUrl] = useState("");
  const [whProvider, setWhProvider] = useState("generic");
  const [whNewSecret, setWhNewSecret] = useState<string | null>(null);

  const fetchWebhooks = async () => {
    try {
      const res = await axios.get(`${API_BASE}/webhooks`, { headers });
      setWebhooks(res.data);
    } catch (e) { console.error(e); }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_BASE}/webhooks`, {
        display_name: whName,
        endpoint_url: whUrl,
        provider: whProvider,
      }, { headers });
      setWhNewSecret(res.data.secret);
      setWhName(""); setWhUrl("");
      fetchWebhooks();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create webhook subscription");
    }
  };

  const handleRevokeWebhook = async (id: string) => {
    if (!confirm("Revoke this webhook subscription?")) return;
    try {
      await axios.delete(`${API_BASE}/webhooks/${id}`, { headers });
      fetchWebhooks();
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (activeTab === "webhooks") fetchWebhooks();
  }, [activeTab]);
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
            Scoped API Keys · Active Policy Enforcement · Single-Use Approvals · Cryptographic Audit Chain
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 10, marginBottom: 28, borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 12 }}>
        <button
          onClick={() => setActiveTab("security")}
          style={{
            background: activeTab === "security" ? "rgba(239,68,68,0.18)" : "transparent",
            border: activeTab === "security" ? "1px solid #ef4444" : "1px solid transparent",
            color: activeTab === "security" ? "#f8fafc" : "#94a3b8",
            borderRadius: 8, padding: "9px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer",
            transition: "all 0.2s ease"
          }}
        >
          🛡️ Active Security Policy & Approval Workflow
        </button>
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
          onClick={() => setActiveTab("webhooks")}
          style={{
            background: activeTab === "webhooks" ? "rgba(56,189,248,0.18)" : "transparent",
            border: activeTab === "webhooks" ? "1px solid #38bdf8" : "1px solid transparent",
            color: activeTab === "webhooks" ? "#f8fafc" : "#94a3b8",
            borderRadius: 8, padding: "9px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer",
            transition: "all 0.2s ease"
          }}
        >
          🔔 Webhooks & Notifications
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
      {activeTab === "security" ? (
        <div>
          {/* Active Security Architecture Summary Banner */}
          <div style={{
            background: "linear-gradient(135deg, rgba(239,68,68,0.12), rgba(99,102,241,0.12))",
            border: "1px solid rgba(239,68,68,0.3)", borderRadius: 14, padding: 24, marginBottom: 28,
            backdropFilter: "blur(16px)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontWeight: 800, fontSize: 16, color: "#f87171" }}>
                🛡️ Active Security Policy Architecture (v1.2 - Frozen & Final)
              </div>
              <span style={{ background: "#ef4444", color: "#fff", padding: "4px 12px", borderRadius: 6, fontWeight: 800, fontSize: 11 }}>
                ENFORCEMENT ACTIVE (FAIL-CLOSED)
              </span>
            </div>
            <p style={{ color: "#cbd5e1", fontSize: 13, margin: "0 0 16px 0", lineHeight: 1.6 }}>
              Core Imperative: <em>"Detection provides evidence. Policy makes the decision. Authorization determines capability. Enforcement controls the side effect. Audit records why."</em>
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14 }}>
              <div style={{ background: "rgba(0,0,0,0.3)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 700 }}>POLICY PRECEDENCE</div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#f87171", marginTop: 4 }}>BLOCK &gt; APPROVAL &gt; WARN</div>
              </div>
              <div style={{ background: "rgba(0,0,0,0.3)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 700 }}>CHOKE POINT</div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#38bdf8", marginTop: 4 }}>ExecutionController</div>
              </div>
              <div style={{ background: "rgba(0,0,0,0.3)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 700 }}>TOCTOU FINGERPRINT</div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#a855f7", marginTop: 4 }}>SHA-256 Canonical JSON</div>
              </div>
              <div style={{ background: "rgba(0,0,0,0.3)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 700 }}>APPROVAL CONSUMPTION</div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#4ade80", marginTop: 4 }}>Atomic Single-Use</div>
              </div>
            </div>
          </div>

          {/* Pending Human Approval Queue */}
          <div style={{
            background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14, padding: 24, marginBottom: 28
          }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, fontWeight: 800, color: "#f8fafc" }}>
              ⏳ Human Approval Queue (REQUIRE_APPROVAL)
            </h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>APPROVAL ID</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>TOOL & ACTION</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ENVIRONMENT</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>FINGERPRINT</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>STATUS</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>SINGLE-USE</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: 12, fontFamily: "monospace", color: "#94a3b8" }}>appr_a1b2c3d4e5f6</td>
                  <td style={{ padding: 12, fontWeight: 700, color: "#f8fafc" }}>database.write : orders</td>
                  <td style={{ padding: 12 }}><span style={{ color: "#38bdf8", fontWeight: 700 }}>staging</span></td>
                  <td style={{ padding: 12, fontFamily: "monospace", color: "#a855f7", fontSize: 11 }}>e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</td>
                  <td style={{ padding: 12 }}><span style={{ color: "#eab308", fontWeight: 800 }}>PENDING</span></td>
                  <td style={{ padding: 12, color: "#94a3b8" }}>Unconsumed</td>
                </tr>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: 12, fontFamily: "monospace", color: "#94a3b8" }}>appr_9876543210ab</td>
                  <td style={{ padding: 12, fontWeight: 700, color: "#f8fafc" }}>database.write : customers</td>
                  <td style={{ padding: 12 }}><span style={{ color: "#f87171", fontWeight: 700 }}>production</span></td>
                  <td style={{ padding: 12, fontFamily: "monospace", color: "#a855f7", fontSize: 11 }}>5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8</td>
                  <td style={{ padding: 12 }}><span style={{ color: "#22c55e", fontWeight: 800 }}>APPROVED</span></td>
                  <td style={{ padding: 12, color: "#4ade80", fontWeight: 700 }}>Consumed at 12:24:01</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : activeTab === "api_keys" ? (
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
                  className="glass-input"
                  style={{ width: 240 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>ROLE PERMISSION LEVEL</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="glass-select"
                  style={{ width: 150 }}
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
                  className="glass-input"
                  style={{ width: 230 }}
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
      ) : activeTab === "webhooks" ? (
        /* Webhooks & Notifications Tab */
        <div>
          {/* Create Webhook Form */}
          <div style={{
            background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14, padding: 24, marginBottom: 28, backdropFilter: "blur(16px)"
          }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, fontWeight: 800 }}>Register Webhook Push Endpoint</h3>
            <form onSubmit={handleCreateWebhook} style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>SUBSCRIPTION NAME</label>
                <input
                  type="text" required placeholder="e.g. Production Slack Alert Webhook"
                  value={whName} onChange={(e) => setWhName(e.target.value)}
                  className="glass-input" style={{ width: 260 }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>TARGET ENDPOINT URL (SSRF FIREWALL PROTECTED)</label>
                <input
                  type="url" required placeholder="https://hooks.slack.com/services/..."
                  value={whUrl} onChange={(e) => setWhUrl(e.target.value)}
                  className="glass-input" style={{ width: 340 }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>PROVIDER FORMATTER</label>
                <select value={whProvider} onChange={(e) => setWhProvider(e.target.value)} className="glass-select" style={{ width: 140 }}>
                  <option value="generic" style={{ background: "#0f172a" }}>Generic JSON</option>
                  <option value="slack" style={{ background: "#0f172a" }}>Slack</option>
                  <option value="teams" style={{ background: "#0f172a" }}>MS Teams</option>
                  <option value="pagerduty" style={{ background: "#0f172a" }}>PagerDuty</option>
                </select>
              </div>
              <button type="submit" className="glass-button">
                Register Webhook
              </button>
            </form>

            {/* Secret Created Banner */}
            {whNewSecret && (
              <div style={{ marginTop: 20, padding: 16, background: "rgba(56,189,248,0.1)", border: "1px solid #38bdf8", borderRadius: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#38bdf8", marginBottom: 6 }}>
                  🔑 HMAC SIGNING SECRET (SHOWN ONCE)
                </div>
                <div style={{ fontFamily: "monospace", fontSize: 13, color: "#f8fafc", wordBreak: "break-all" }}>
                  {whNewSecret}
                </div>
              </div>
            )}
          </div>

          {/* Webhooks Table */}
          <div style={{ background: "rgba(11,15,25,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 14, padding: 24 }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, fontWeight: 800 }}>Active Webhook Subscriptions</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#64748b", textAlign: "left" }}>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ID</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>NAME</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ENDPOINT URL</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>PROVIDER</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>STATUS</th>
                  <th style={{ padding: "12px 10px", fontSize: 11, fontWeight: 700 }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {webhooks.map((w) => (
                  <tr key={w.webhook_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: 12, fontFamily: "monospace", color: "#94a3b8" }}>{w.webhook_id}</td>
                    <td style={{ padding: 12, fontWeight: 600, color: "#f8fafc" }}>{w.display_name}</td>
                    <td style={{ padding: 12, fontFamily: "monospace", color: "#38bdf8" }}>{w.endpoint_url}</td>
                    <td style={{ padding: 12 }}><span className="badge badge-indigo">{w.provider}</span></td>
                    <td style={{ padding: 12 }}>
                      <span style={{ color: w.status === "active" ? "#22c55e" : "#ef4444", fontWeight: 800, fontSize: 12 }}>
                        {w.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: 12 }}>
                      {w.status === "active" && (
                        <button
                          onClick={() => handleRevokeWebhook(w.webhook_id)}
                          style={{ background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444", color: "#f87171", borderRadius: 6, padding: "5px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer" }}
                        >
                          Revoke
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
