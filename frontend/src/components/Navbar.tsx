import React from 'react';
import { NavLink } from 'react-router-dom';
import { Layers, TestTube2, AlertTriangle, Activity, BarChart3 } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header style={{ borderBottom: '1px solid var(--border-glass)', background: 'var(--bg-glass)', backdropFilter: 'blur(16px)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'linear-gradient(135deg, #6366f1, #3b82f6)', padding: '10px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)' }}>
            <Activity size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', background: 'linear-gradient(to right, #ffffff, #9ca3af)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              VANTAGE
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>AI & Engineering Observability Hub</p>
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <Layers size={18} />
            Projects
          </NavLink>

          <NavLink
            to="/experiments"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <TestTube2 size={18} />
            Experiments
          </NavLink>

          <NavLink
            to="/alerts"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <AlertTriangle size={18} />
            Alerts
          </NavLink>

          <NavLink
            to="/telemetry"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <Activity size={18} />
            Agent Cost
          </NavLink>

          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: '#34d399',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              marginLeft: '8px',
              transition: 'all 0.2s ease',
            }}
          >
            <BarChart3 size={18} />
            Grafana
          </a>
        </nav>
      </div>
    </header>
  );
};
