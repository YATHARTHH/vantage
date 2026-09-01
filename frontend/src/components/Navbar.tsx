import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Layers, 
  TestTube2, 
  AlertTriangle, 
  Activity, 
  BarChart3, 
  Search, 
  Bell, 
  Key, 
  ExternalLink, 
  Check, 
  Copy, 
  ShieldAlert, 
  ChevronRight,
  BookOpen,
  HeartPulse,
  CheckCircle2
} from 'lucide-react';
import { VantageAPI, AlertRecord } from '../api/client';

export const Navbar: React.FC = () => {
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchNavbarAlerts = async () => {
      try {
        const data = await VantageAPI.getAlerts(true);
        let savedResolved: string[] = [];
        try {
          const raw = localStorage.getItem('vantage_resolved_alerts');
          savedResolved = raw ? JSON.parse(raw) : [];
        } catch {}
        const active = data.filter((a) => !a.resolved_at && !savedResolved.includes(a.alert_id || a.id || ''));
        setAlerts(active);
      } catch (err) {
        console.error('Failed to fetch navbar alerts:', err);
      }
    };

    fetchNavbarAlerts();

    window.addEventListener('vantage-alerts-updated', fetchNavbarAlerts);
    return () => {
      window.removeEventListener('vantage-alerts-updated', fetchNavbarAlerts);
    };
  }, []);

  const handleCopyKey = () => {
    navigator.clipboard.writeText('dev-local-key');
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <header style={{ borderBottom: '1px solid var(--border-glass)', background: 'rgba(11, 15, 25, 0.85)', backdropFilter: 'blur(20px)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
        
        {/* Brand Logo & Name */}
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

        {/* Global Search Bar */}
        <div style={{ flex: 1, maxWidth: '380px', position: 'relative' }}>
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
              outline: 'none'
            }}
          />
          <span style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.7rem', color: '#6b7280', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
            Ctrl+K
          </span>
        </div>

        {/* Navigation Links */}
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

        {/* Right Header Interactive Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', position: 'relative' }}>
          
          {/* Interactive Alerts Dropdown Button */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => {
                setAlertsOpen(!alertsOpen);
                setUserMenuOpen(false);
              }}
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                background: alerts.length > 0 ? 'rgba(244, 63, 94, 0.15)' : 'rgba(52, 211, 153, 0.15)',
                color: '#ffffff',
                border: alerts.length > 0 ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(52, 211, 153, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <Bell size={16} color={alerts.length > 0 ? '#f87171' : '#34d399'} />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: alerts.length > 0 ? '#f87171' : '#34d399' }}>Alerts</span>
              <span style={{ background: alerts.length > 0 ? '#f43f5e' : '#10b981', color: '#ffffff', fontSize: '0.65rem', fontWeight: 800, borderRadius: '9999px', padding: '1px 6px' }}>
                {alerts.length}
              </span>
            </button>

            {/* Alerts Dropdown Modal */}
            {alertsOpen && (
              <div 
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '48px',
                  width: '320px',
                  background: 'rgba(18, 24, 36, 0.95)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  borderRadius: '16px',
                  padding: '16px',
                  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6)',
                  zIndex: 100,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={16} color="#22d3ee" />
                    <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.875rem' }}>Active Anomaly Feed</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#22d3ee', background: 'rgba(6, 182, 212, 0.2)', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                    {alerts.length} Active
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem', maxHeight: '240px', overflowY: 'auto' }}>
                  {alerts.length === 0 && (
                    <div style={{ padding: '16px', textAlign: 'center', color: '#9ca3af', fontSize: '0.8rem' }}>
                      <CheckCircle2 size={20} color="#34d399" style={{ margin: '0 auto 6px' }} />
                      No active anomalies. All services operating normally.
                    </div>
                  )}

                  {alerts.map((a) => (
                    <div key={a.id} style={{ padding: '8px 10px', borderRadius: '8px', background: a.severity === 'critical' ? 'rgba(244, 63, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)', borderLeft: a.severity === 'critical' ? '3px solid #f43f5e' : '3px solid #f59e0b' }}>
                      <p style={{ fontWeight: 600, color: '#ffffff' }}>{a.title}</p>
                      <p style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Value: {a.observed_value} (Threshold: {a.threshold_value})</p>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => {
                    setAlertsOpen(false);
                    navigate('/alerts');
                  }}
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '8px',
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: '1px solid rgba(99, 102, 241, 0.4)',
                    color: '#ffffff',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  View All Alerts in Dashboard <ChevronRight size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Interactive User Profile Avatar ('Y' - Yatharth Singhai) */}
          <div style={{ position: 'relative' }}>
            <div
              onClick={() => {
                setUserMenuOpen(!userMenuOpen);
                setAlertsOpen(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '4px 10px 4px 6px',
                borderRadius: '9999px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ 
                width: '28px', 
                height: '28px', 
                borderRadius: '50%', 
                background: 'linear-gradient(135deg, #06b6d4, #6366f1)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                fontWeight: 800, 
                color: '#ffffff', 
                fontSize: '0.8rem',
                boxShadow: '0 0 10px rgba(6, 182, 212, 0.4)'
              }}>
                Y
              </div>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ffffff' }}>Yatharth</span>
            </div>

            {/* User Profile Menu Dropdown */}
            {userMenuOpen && (
              <div 
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '48px',
                  width: '280px',
                  background: 'rgba(18, 24, 36, 0.95)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  borderRadius: '16px',
                  padding: '16px',
                  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6)',
                  zIndex: 100,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px'
                }}
              >
                {/* User Info Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'linear-gradient(135deg, #06b6d4, #6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, color: '#ffffff', fontSize: '1.1rem' }}>
                    Y
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.9rem' }}>Yatharth Singhai</p>
                    <p style={{ fontSize: '0.75rem', color: '#06b6d4', fontWeight: 500 }}>Lead AI & Observability Engineer</p>
                  </div>
                </div>

                {/* API Key Box */}
                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '10px 12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: '#9ca3af', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Key size={12} color="#06b6d4" /> API Key
                    </span>
                    <button
                      onClick={handleCopyKey}
                      style={{ background: 'none', border: 'none', color: copiedKey ? '#34d399' : '#06b6d4', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}
                    >
                      {copiedKey ? <Check size={12} /> : <Copy size={12} />}
                      {copiedKey ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <code style={{ fontSize: '0.75rem', color: '#22d3ee', fontFamily: 'monospace' }}>dev-local-key</code>
                </div>

                {/* Quick Links */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                  <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: '6px 8px', borderRadius: '6px', color: '#d1d5db', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <BookOpen size={14} color="#818cf8" /> Swagger OpenAPI Docs
                    </span>
                    <ExternalLink size={12} color="#6b7280" />
                  </a>

                  <a
                    href="http://localhost:8000/health"
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: '6px 8px', borderRadius: '6px', color: '#d1d5db', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <HeartPulse size={14} color="#34d399" /> System Health Status
                    </span>
                    <ExternalLink size={12} color="#6b7280" />
                  </a>
                </div>

                {/* Environment Info */}
                <div style={{ paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.7rem', color: '#6b7280', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>Engine: DuckDB + SQLite</span>
                  <span style={{ color: '#34d399', fontWeight: 600 }}>v1.0.0 Active</span>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    </header>
  );
};
