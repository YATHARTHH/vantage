import React, { useEffect, useState } from 'react';
import { VantageAPI, Experiment } from '../api/client';
import { TestTube2, CheckCircle, Clock, AlertCircle, Sparkles, User, FileText } from 'lucide-react';

export const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null);

  const loadExperiments = async () => {
    try {
      setLoading(true);
      const data = await VantageAPI.getExperiments();
      setExperiments(data);
    } catch (err) {
      console.error('Failed to load experiments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExperiments();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-emerald"><CheckCircle size={12} /> COMPLETED</span>;
      case 'active':
        return <span className="badge badge-blue"><Clock size={12} /> ACTIVE</span>;
      case 'planned':
        return <span className="badge badge-amber"><Sparkles size={12} /> PLANNED</span>;
      default:
        return <span className="badge badge-rose">{status}</span>;
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Experiment Registry</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
          Link model hyper-parameters, datasets, accuracy benchmarks, and cost outcomes directly to production telemetry.
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>Loading experiment registry...</div>
      ) : experiments.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>No experiments registered yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {experiments.map((exp) => (
            <div key={exp.id} className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  {getStatusBadge(exp.status)}
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Slug: {exp.slug}</span>
                  {exp.project_id && <span style={{ fontSize: '0.8rem', color: '#60a5fa' }}>Project: {exp.project_id}</span>}
                </div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '6px' }}>{exp.title}</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{exp.hypothesis}</p>
              </div>

              <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <User size={14} />
                  <span>{exp.owner_name} ({exp.owner_team})</span>
                </div>
                <button className="glass-button" style={{ fontSize: '0.8rem', padding: '6px 12px' }} onClick={() => setSelectedExp(exp)}>
                  <FileText size={14} /> View Results & Metrics
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedExp && (
        <div className="modal-overlay" onClick={() => setSelectedExp(null)}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '650px', padding: '32px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{selectedExp.title}</h3>
              {getStatusBadge(selectedExp.status)}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '0.9rem' }}>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Hypothesis:</strong>
                <p style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                  {selectedExp.hypothesis}
                </p>
              </div>

              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Objective:</strong>
                <p>{selectedExp.objective}</p>
              </div>

              {selectedExp.result ? (
                <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Sparkles size={18} color="#34d399" />
                    <strong style={{ fontSize: '1rem', color: '#34d399' }}>Outcome: {selectedExp.result.outcome.toUpperCase()}</strong>
                  </div>

                  <p style={{ marginBottom: '12px' }}>{selectedExp.result.summary}</p>

                  <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Evaluated Metrics:</strong>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                    {Object.entries(selectedExp.result.metrics).map(([k, v]) => (
                      <div key={k} style={{ background: 'rgba(99,102,241,0.1)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(99,102,241,0.2)', textAlign: 'center' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>{k}</span>
                        <strong style={{ fontSize: '1.1rem', color: '#ffffff' }}>{v}</strong>
                      </div>
                    ))}
                  </div>

                  <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Key Learnings:</strong>
                  <p style={{ fontStyle: 'italic', color: '#d1d5db' }}>"{selectedExp.result.learnings}"</p>
                </div>
              ) : (
                <div style={{ padding: '24px', textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px dashed var(--border-glass)', color: 'var(--text-muted)' }}>
                  Results pending for this active experiment.
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
                <button className="glass-button" onClick={() => setSelectedExp(null)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
