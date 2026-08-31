import React, { useEffect, useState } from 'react';
import { VantageAPI, Project } from '../api/client';
import { FolderGit2, Cpu, ShieldAlert, Plus, CheckCircle2 } from 'lucide-react';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    display_name: '',
    project_type: 'ai_llm' as 'ai_llm' | 'software',
    owner_team: '',
    owner_email: '',
    description: '',
    log_prompts: false,
  });

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await VantageAPI.getProjects();
      setProjects(data);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await VantageAPI.createProject(formData);
      setShowModal(false);
      setFormData({
        id: '',
        display_name: '',
        project_type: 'ai_llm',
        owner_team: '',
        owner_email: '',
        description: '',
        log_prompts: false,
      });
      loadProjects();
    } catch (err) {
      alert('Failed to create project.');
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Registered Projects</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
            Telemetry identity mapping and source connector configurations.
          </p>
        </div>
        <button className="glass-button" onClick={() => setShowModal(true)}>
          <Plus size={18} /> Register Project
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>No projects registered yet.</p>
        </div>
      ) : (
        <div className="grid-container">
          {projects.map((p) => (
            <div key={p.id} className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <span className={`badge ${p.project_type === 'ai_llm' ? 'badge-blue' : 'badge-emerald'}`}>
                    {p.project_type === 'ai_llm' ? <Cpu size={14} /> : <FolderGit2 size={14} />}
                    {p.project_type === 'ai_llm' ? 'AI / LLM' : 'SOFTWARE'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {p.id}</span>
                </div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '8px' }}>{p.display_name}</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '16px', minHeight: '40px' }}>
                  {p.description || 'No description provided.'}
                </p>
              </div>

              <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <div>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>Team:</span> {p.owner_team}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldAlert size={14} color={p.log_prompts ? '#fbbf24' : '#34d399'} />
                  <span>PII Safe: {p.log_prompts ? 'Prompts Enabled' : 'Sanitized'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass-panel" style={{ width: '100%', maxWidth: '500px', padding: '32px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px' }}>Register New Project</h3>
            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-muted)' }}>Project Slug ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. search-v2"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-muted)' }}>Display Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. LLM Search Agent"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-muted)' }}>Type</label>
                  <select
                    value={formData.project_type}
                    onChange={(e) => setFormData({ ...formData, project_type: e.target.value as any })}
                    style={{ width: '100%', padding: '10px', background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff' }}
                  >
                    <option value="ai_llm">AI / LLM Agent</option>
                    <option value="software">Software Service</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-muted)' }}>Owner Team</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. AI Platform"
                    value={formData.owner_team}
                    onChange={(e) => setFormData({ ...formData, owner_team: e.target.value })}
                    style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-muted)' }}>Owner Email</label>
                <input
                  type="email"
                  required
                  placeholder="team@company.com"
                  value={formData.owner_email}
                  onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
                <button type="button" onClick={() => setShowModal(false)} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--border-glass)', color: '#fff', borderRadius: '8px', cursor: 'pointer' }}>
                  Cancel
                </button>
                <button type="submit" className="glass-button">
                  <CheckCircle2 size={16} /> Save Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
