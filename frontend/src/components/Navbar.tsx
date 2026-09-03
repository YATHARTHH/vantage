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
  CheckCircle2,
  GitBranch,
  Box,
  SlidersHorizontal,
  Lock
} from 'lucide-react';
import { VantageAPI, AlertRecord } from '../api/client';

export const Navbar: React.FC = () => {
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
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
        const active = Array.isArray(data)
          ? data.filter((a) => !a.resolved_at && !savedResolved.includes(a.alert_id || a.id || ''))
          : [];
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
    <header style={{
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      background: 'rgba(8, 12, 22, 0.85)',
      backdropFilter: 'blur(20px)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      height: '64px',
      display: 'flex',
      alignItems: 'center',
    }}>
      <div style={{
        maxWidth: '1440px',
        width: '100%',
        margin: '0 auto',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
      }}>
        
        {/* Left Brand + Global Search Group */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* Logo & Brand Name */}
          <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
            <div style={{ 
              width: '32px', 
              height: '32px', 
              borderRadius: '9px', 
              background: 'linear-gradient(135deg, #38bdf8 0%, #6366f1 100%)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              boxShadow: '0 0 16px rgba(56, 189, 248, 0.35)',
              color: '#ffffff',
              fontWeight: 900,
              fontSize: '1.1rem'
            }}>
              V
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#f8fafc' }}>
                Vantage
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
                color: '#818cf8',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: '4px',
                padding: '1px 6px',
                textTransform: 'uppercase'
              }}>
                Enterprise
              </span>
            </div>
          </NavLink>

          <div style={{ width: '1px', height: '22px', background: 'rgba(255, 255, 255, 0.1)' }} />

          {/* Global Search Bar */}
          <div style={{ position: 'relative', width: searchFocused ? '280px' : '230px', transition: 'all 0.25s ease' }}>
            <Search size={14} color={searchFocused ? '#38bdf8' : '#64748b'} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', transition: 'color 0.2s ease' }} />
            <input
              type="text"
              placeholder="Search traces, models, keys..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              style={{
                width: '100%',
                background: searchFocused ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.04)',
                border: searchFocused ? '1px solid rgba(56, 189, 248, 0.5)' : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '7px 34px 7px 34px',
                color: '#f8fafc',
                fontSize: '0.8rem',
                outline: 'none',
                boxShadow: searchFocused ? '0 0 16px rgba(56, 189, 248, 0.15)' : 'none',
                transition: 'all 0.2s ease'
              }}
            />
            <span style={{
              position: 'absolute',
              right: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: '0.65rem',
              color: '#64748b',
              background: 'rgba(255, 255, 255, 0.06)',
              padding: '1px 5px',
              borderRadius: '4px',
              fontFamily: 'monospace'
            }}>
              ⌘K
            </span>
          </div>
        </div>

        {/* Center Navigation Links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <LayoutDashboard size={15} />
            Overview
          </NavLink>

          <NavLink
            to="/projects"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <Layers size={15} />
            Projects
          </NavLink>

          <NavLink
            to="/dag-explorer"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(168, 85, 247, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(168, 85, 247, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <GitBranch size={15} />
            Agent DAG
          </NavLink>

          <NavLink
            to="/vector-explorer"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(6, 182, 212, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(6, 182, 212, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <Box size={15} />
            Vectors
          </NavLink>

          <NavLink
            to="/alerts"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(239, 68, 68, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <AlertTriangle size={15} />
            Alerts
          </NavLink>

          <NavLink
            to="/telemetry"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <Activity size={15} />
            Agent Cost
          </NavLink>

          <NavLink
            to="/experiments"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <TestTube2 size={15} />
            Experiments
          </NavLink>

          <NavLink
            to="/enterprise"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '7px',
              fontWeight: 600,
              fontSize: '0.825rem',
              color: isActive ? '#f8fafc' : '#94a3b8',
              background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
              border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
            })}
          >
            <Lock size={15} />
            Enterprise
          </NavLink>
        </nav>

        {/* Right Header Interactive Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          
          {/* Grafana External Button */}
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 10px',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.75rem',
              color: '#34d399',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              textDecoration: 'none',
              transition: 'all 0.2s ease'
            }}
          >
            <BarChart3 size={13} />
            Grafana
          </a>

          {/* Interactive Alerts Dropdown Button */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => {
                setAlertsOpen(!alertsOpen);
                setUserMenuOpen(false);
              }}
              style={{
                padding: '6px 10px',
                borderRadius: '7px',
                background: alerts.length > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                color: '#f8fafc',
                border: alerts.length > 0 ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <Bell size={14} color={alerts.length > 0 ? '#ef4444' : '#94a3b8'} />
              {alerts.length > 0 && (
                <span style={{
                  background: '#ef4444',
                  color: '#ffffff',
                  fontSize: '0.65rem',
                  fontWeight: 800,
                  borderRadius: '9999px',
                  padding: '1px 5px'
                }}>
                  {alerts.length}
                </span>
              )}
            </button>

            {/* Alerts Dropdown Modal */}
            {alertsOpen && (
              <div style={{
                position: 'absolute',
                right: 0,
                top: '44px',
                width: '320px',
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '16px',
                boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6)',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={16} color="#38bdf8" />
                    <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.85rem' }}>Active Anomaly Feed</span>
                  </div>
                  <span style={{ fontSize: '0.65rem', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.15)', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                    {alerts.length} Active
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem', maxHeight: '240px', overflowY: 'auto' }}>
                  {alerts.length === 0 && (
                    <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
                      <CheckCircle2 size={20} color="#22c55e" style={{ margin: '0 auto 6px' }} />
                      No active anomalies. All systems normal.
                    </div>
                  )}

                  {alerts.map((a) => (
                    <div key={a.id} style={{ padding: '8px 10px', borderRadius: '8px', background: a.severity === 'critical' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', borderLeft: a.severity === 'critical' ? '3px solid #ef4444' : '3px solid #f59e0b' }}>
                      <p style={{ fontWeight: 600, color: '#f8fafc', margin: 0 }}>{a.title}</p>
                      <p style={{ fontSize: '0.7rem', color: '#94a3b8', margin: '2px 0 0 0' }}>Value: {a.observed_value} (Threshold: {a.threshold_value})</p>
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
                    color: '#f8fafc',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  View All Alerts <ChevronRight size={14} />
                </button>
              </div>
            )}
          </div>

          {/* User Profile Avatar Avatar */}
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
                padding: '3px 8px 3px 4px',
                borderRadius: '9999px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ 
                width: '26px', 
                height: '26px', 
                borderRadius: '50%', 
                background: 'linear-gradient(135deg, #38bdf8, #6366f1)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                fontWeight: 800, 
                color: '#ffffff', 
                fontSize: '0.75rem',
                boxShadow: '0 0 10px rgba(56, 189, 248, 0.35)'
              }}>
                Y
              </div>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>Yatharth</span>
            </div>

            {/* User Profile Menu Dropdown */}
            {userMenuOpen && (
              <div style={{
                position: 'absolute',
                right: 0,
                top: '44px',
                width: '280px',
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '16px',
                boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6)',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '14px'
              }}>
                {/* User Info Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
                  <div style={{ width: '38px', height: '38px', borderRadius: '50%', background: 'linear-gradient(135deg, #38bdf8, #6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, color: '#ffffff', fontSize: '1rem' }}>
                    Y
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.875rem', margin: 0 }}>Yatharth Singhai</p>
                    <p style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 500, margin: '2px 0 0 0' }}>Lead AI & Observability Engineer</p>
                  </div>
                </div>

                {/* API Key Box */}
                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Key size={12} color="#38bdf8" /> API Key
                    </span>
                    <button
                      onClick={handleCopyKey}
                      style={{ background: 'none', border: 'none', color: copiedKey ? '#22c55e' : '#38bdf8', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}
                    >
                      {copiedKey ? <Check size={12} /> : <Copy size={12} />}
                      {copiedKey ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <code style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace' }}>dev-local-key</code>
                </div>

                {/* Quick Links */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                  <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: '6px 8px', borderRadius: '6px', color: '#cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', textDecoration: 'none' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <BookOpen size={14} color="#818cf8" /> Swagger OpenAPI Docs
                    </span>
                    <ExternalLink size={12} color="#64748b" />
                  </a>

                  <a
                    href="http://localhost:8000/health"
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: '6px 8px', borderRadius: '6px', color: '#cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', textDecoration: 'none' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <HeartPulse size={14} color="#22c55e" /> System Health Status
                    </span>
                    <ExternalLink size={12} color="#64748b" />
                  </a>
                </div>

                {/* Environment Info */}
                <div style={{ paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.7rem', color: '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>Engine: DuckDB + SQLite</span>
                  <span style={{ color: '#22c55e', fontWeight: 600 }}>v1.0.0 Active</span>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    </header>
  );
};
