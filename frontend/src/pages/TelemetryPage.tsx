import React, { useEffect, useState } from 'react';
import { VantageAPI, AgentRunCost } from '../api/client';
import { Cpu, DollarSign, Zap, Hash, Activity } from 'lucide-react';

export const TelemetryPage: React.FC = () => {
  const [runs, setRuns] = useState<AgentRunCost[]>([]);
  const [projectId, setProjectId] = useState('search-v2');
  const [loading, setLoading] = useState(true);

  const loadAgentRuns = async () => {
    try {
      setLoading(true);
      const data = await VantageAPI.getAgentCost(projectId);
      setRuns(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load agent runs:', err);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgentRuns();
  }, [projectId]);

  const safeRuns = Array.isArray(runs) ? runs : [];
  const totalSpend = safeRuns.reduce((acc, r) => acc + (r.total_cost_usd || 0), 0);
  const totalTokens = safeRuns.reduce((acc, r) => acc + (r.tokens_input || 0) + (r.tokens_output || 0), 0);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Agent Cost & Telemetry Explorer</h2>
          <p className="page-subtitle">
            Query-time agent total cost aggregation matching root agent spans (`parent_span_id IS NULL`).
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Project Filter:</label>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            style={{ padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff', fontSize: '0.9rem' }}
          >
            <option value="search-v2">search-v2 (RAG Search Agent)</option>
            <option value="e2e-search-v1">e2e-search-v1 (E2E Test Assistant)</option>
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '32px' }}>
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '12px', borderRadius: '12px' }}>
            <DollarSign size={28} color="#34d399" />
          </div>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>Total Agent Cost (USD)</span>
            <strong style={{ fontSize: '1.5rem', fontWeight: 700, color: '#34d399' }}>${totalSpend.toFixed(4)}</strong>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: 'rgba(99, 102, 241, 0.15)', padding: '12px', borderRadius: '12px' }}>
            <Cpu size={28} color="#60a5fa" />
          </div>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>Total Tokens Processed</span>
            <strong style={{ fontSize: '1.5rem', fontWeight: 700, color: '#60a5fa' }}>{totalTokens.toLocaleString()}</strong>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '12px', borderRadius: '12px' }}>
            <Zap size={28} color="#fbbf24" />
          </div>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>Root Agent Executions</span>
            <strong style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fbbf24' }}>{runs.length}</strong>
          </div>
        </div>
      </div>

      {/* Traces Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>Loading telemetry traces...</div>
      ) : runs.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>No root agent executions found for project '{projectId}'.</p>
        </div>
      ) : (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '16px 20px' }}>Trace ID</th>
                <th style={{ padding: '16px 20px' }}>Agent Name</th>
                <th style={{ padding: '16px 20px' }}>Child LLM Calls</th>
                <th style={{ padding: '16px 20px' }}>Input Tokens</th>
                <th style={{ padding: '16px 20px' }}>Output Tokens</th>
                <th style={{ padding: '16px 20px' }}>Total Cost (USD)</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.trace_id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <td style={{ padding: '16px 20px', fontFamily: 'monospace', color: '#60a5fa' }}>{r.trace_id}</td>
                  <td style={{ padding: '16px 20px', fontWeight: 600 }}>{r.agent_name}</td>
                  <td style={{ padding: '16px 20px' }}>
                    <span className="badge badge-blue">{r.llm_call_count} calls</span>
                  </td>
                  <td style={{ padding: '16px 20px', color: 'var(--text-muted)' }}>{r.tokens_input.toLocaleString()}</td>
                  <td style={{ padding: '16px 20px', color: 'var(--text-muted)' }}>{r.tokens_output.toLocaleString()}</td>
                  <td style={{ padding: '16px 20px', fontWeight: 700, color: '#34d399' }}>${r.total_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
