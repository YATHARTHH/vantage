import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Layers, TestTube2, AlertTriangle, Activity, BarChart3, Search, Bell } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header style={{ borderBottom: '1px solid var(--border-glass)', background: 'rgba(11, 15, 25, 0.85)', backdropFilter: 'blur(20px)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
        
        {/* Brand Logo & Name matching Banner */}
        <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'flex-start' }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #06b6d4, #6366f1)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            boxShadow: '0 0 20px rgba(6, 182, 212, 0.4)',
            color: '#ffffff',
            fontWeight: 900,
            fontSize: '1.2rem'
          }}>
            V
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
              Vantage <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '0.95rem' }}>AI Observability</span>
            </h1>
          </div>
        </NavLink>

        {/* Global Search Input Bar matching Banner */}
        <div style={{ flex: 1, maxWidth: '400px', position: 'relative' }}>
          <Search size={16} color="#6b7280" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search traces, models, projects..."
            style={{
              width: '100%',
              background: 'rgba(18, 24, 36, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '9999px',
              padding: '8px 40px 8px 38px',
              color: '#ffffff',
              fontSize: '0.85rem',
              outline: 'none',
              transition: 'all 0.2s ease'
            }}
          />
          <span style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.7rem', color: '#6b7280', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
            Ctrl+K
          </span>
        </div>

        {/* Center Nav Links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: isActive ? '#ffffff' : '#9ca3af',
              background: isActive ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <LayoutDashboard size={16} />
            Overview
          </NavLink>

          <NavLink
            to="/projects"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: isActive ? '#ffffff' : '#9ca3af',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <Layers size={16} />
            Projects
          </NavLink>

          <NavLink
            to="/experiments"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: isActive ? '#ffffff' : '#9ca3af',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <TestTube2 size={16} />
            Experiments
          </NavLink>

          <NavLink
            to="/alerts"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: isActive ? '#ffffff' : '#9ca3af',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <AlertTriangle size={16} />
            Alerts
          </NavLink>

          <NavLink
            to="/telemetry"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: isActive ? '#ffffff' : '#9ca3af',
              background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              transition: 'all 0.2s ease',
            })}
          >
            <Activity size={16} />
            Agent Cost
          </NavLink>

          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: '#34d399',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              marginLeft: '4px',
              transition: 'all 0.2s ease',
            }}
          >
            <BarChart3 size={16} />
            Grafana
          </a>
        </nav>

        {/* Right Header Actions matching Banner */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ position: 'relative', cursor: 'pointer' }}>
            <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(255, 255, 255, 0.05)', color: '#ffffff', border: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Bell size={16} />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f43f5e' }}>Alerts</span>
              <span style={{ background: '#f43f5e', color: '#ffffff', fontSize: '0.65rem', fontWeight: 800, borderRadius: '9999px', padding: '1px 6px' }}>3</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 8px', borderRadius: '9999px', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'linear-gradient(135deg, #818cf8, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#ffffff', fontSize: '0.75rem' }}>
              Y
            </div>
          </div>
        </div>

      </div>
    </header>
  );
};
