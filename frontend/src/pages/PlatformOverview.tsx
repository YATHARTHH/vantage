import React, { useState } from 'react';
import { 
  DollarSign, 
  Activity, 
  BarChart3, 
  AlertTriangle, 
  ChevronDown, 
  Terminal, 
  Globe, 
  Database, 
  Cpu, 
  Zap, 
  User, 
  Bell, 
  ShieldAlert, 
  Sparkles
} from 'lucide-react';

export const PlatformOverview: React.FC = () => {
  const [timeRange, setTimeRange] = useState('Past 1 Hour');
  const [selectedSpan, setSelectedSpan] = useState<string | null>('llm_inference');
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([]);

  const handleDismiss = (id: string) => {
    setDismissedAlerts((prev) => [...prev, id]);
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Banner / Controls Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#06b6d4', boxShadow: '0 0 12px #06b6d4' }} />
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#ffffff' }}>
            Platform Overview
          </h2>
          <span className="badge badge-blue" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
            Live Engine
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Time Range Selector */}
          <div style={{ position: 'relative' }}>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{
                background: 'var(--bg-glass)',
                color: '#ffffff',
                border: '1px solid var(--border-glass)',
                padding: '8px 36px 8px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: 'pointer',
                outline: 'none',
                appearance: 'none',
                backdropFilter: 'blur(16px)'
              }}
            >
              <option value="Past 1 Hour">Past 1 Hour</option>
              <option value="Past 24 Hours">Past 24 Hours</option>
              <option value="Past 7 Days">Past 7 Days</option>
            </select>
            <ChevronDown size={16} color="#9ca3af" style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
          </div>

          <a 
            href="http://localhost:3000" 
            target="_blank" 
            rel="noreferrer" 
            className="glass-button"
            style={{ background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(99, 102, 241, 0.2))', borderColor: 'rgba(6, 182, 212, 0.4)' }}
          >
            <Sparkles size={16} color="#22d3ee" />
            Grafana Live Dashboard
          </a>
        </div>
      </div>

      {/* Hero Metric Cards Grid (4 Columns matching Banner) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        
        {/* Card 1: LLM Cost Analytics */}
        <div className="glass-panel" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(18, 24, 36, 0.85), rgba(15, 23, 42, 0.95))', border: '1px solid rgba(6, 182, 212, 0.25)', boxShadow: '0 0 30px rgba(6, 182, 212, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#9ca3af' }}>LLM Cost Analytics</span>
            <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee' }}>
              <DollarSign size={20} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '16px' }}>
            <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.03em' }}>$1,245.70</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f43f5e' }}>(+8%)</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.75rem' }}>
            <div>
              <p style={{ color: '#6b7280' }}>Total Cost</p>
              <p style={{ color: '#f3f4f6', fontWeight: 600 }}>$1,245.70</p>
            </div>
            <div>
              <p style={{ color: '#6b7280' }}>Token Usage</p>
              <p style={{ color: '#22d3ee', fontWeight: 600 }}>84.2M</p>
            </div>
            <div>
              <p style={{ color: '#6b7280' }}>Avg Cost/Req</p>
              <p style={{ color: '#f3f4f6', fontWeight: 600 }}>$0.015</p>
            </div>
          </div>
        </div>

        {/* Card 2: Service Health */}
        <div className="glass-panel" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(18, 24, 36, 0.85), rgba(15, 23, 42, 0.95))', border: '1px solid rgba(16, 185, 129, 0.25)', boxShadow: '0 0 30px rgba(16, 185, 129, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#9ca3af' }}>Service Health</span>
            <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
              <Activity size={20} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '16px' }}>
            <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.03em' }}>14/15</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#34d399' }}>Healthy</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.75rem' }}>
            <span style={{ color: '#6b7280' }}>Overall Uptime</span>
            <span style={{ color: '#34d399', fontWeight: 700, fontSize: '0.875rem' }}>99.98%</span>
          </div>
        </div>

        {/* Card 3: Throughput & Latency */}
        <div className="glass-panel" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(18, 24, 36, 0.85), rgba(15, 23, 42, 0.95))', border: '1px solid rgba(99, 102, 241, 0.25)', boxShadow: '0 0 30px rgba(99, 102, 241, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#9ca3af' }}>Throughput</span>
            <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
              <BarChart3 size={20} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <div>
              <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>Req/Sec</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff' }}>450</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>Avg Latency</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 800, color: '#818cf8' }}>110ms</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.75rem' }}>
            <span style={{ color: '#6b7280' }}>P99 Latency</span>
            <span style={{ color: '#f3f4f6', fontWeight: 600 }}>240ms</span>
          </div>
        </div>

        {/* Card 4: Anomalies */}
        <div className="glass-panel" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(18, 24, 36, 0.85), rgba(15, 23, 42, 0.95))', border: '1px solid rgba(244, 63, 94, 0.25)', boxShadow: '0 0 30px rgba(244, 63, 94, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#9ca3af' }}>Anomalies</span>
            <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185' }}>
              <ShieldAlert size={20} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '16px' }}>
            <span style={{ fontSize: '2rem', fontWeight: 800, color: '#f87171' }}>3</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f87171' }}>Active</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.75rem' }}>
            <span className="badge badge-rose" style={{ padding: '2px 8px', fontSize: '0.7rem' }}>
              <AlertTriangle size={12} /> 2 Critical
            </span>
            <span className="badge badge-amber" style={{ padding: '2px 8px', fontSize: '0.7rem' }}>
              <AlertTriangle size={12} /> 1 Warning
            </span>
          </div>
        </div>

      </div>

      {/* Main 3-Column Glass Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px' }}>
        
        {/* Column 1: LLM Cost Breakdown Chart (3 Cols) */}
        <div className="glass-panel" style={{ gridColumn: 'span 3', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>LLM Cost Breakdown</h3>
            <span style={{ color: '#6b7280', fontSize: '0.75rem', cursor: 'pointer' }}>•••</span>
          </div>

          {/* Glowing Area Chart SVG */}
          <div style={{ height: '180px', width: '100%', position: 'relative', marginTop: '10px' }}>
            <svg viewBox="0 0 300 150" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
              <defs>
                <linearGradient id="costGrad1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="costGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818cf8" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#818cf8" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              <line x1="0" y1="30" x2="300" y2="30" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
              <line x1="0" y1="75" x2="300" y2="75" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
              <line x1="0" y1="120" x2="300" y2="120" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />

              <path
                d="M 0 110 Q 75 40 150 70 T 300 20 L 300 140 L 0 140 Z"
                fill="url(#costGrad1)"
              />
              <path
                d="M 0 110 Q 75 40 150 70 T 300 20"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="3"
              />

              <path
                d="M 0 130 Q 75 80 150 95 T 300 50 L 300 140 L 0 140 Z"
                fill="url(#costGrad2)"
              />
              <path
                d="M 0 130 Q 75 80 150 95 T 300 50"
                fill="none"
                stroke="#818cf8"
                strokeWidth="2.5"
              />
            </svg>
          </div>

          {/* Model Breakdown Legend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.8125rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4' }} />
                <span style={{ color: '#d1d5db', fontWeight: 500 }}>GPT-4o</span>
              </div>
              <span style={{ color: '#ffffff', fontWeight: 700 }}>$3.3K</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#818cf8' }} />
                <span style={{ color: '#d1d5db', fontWeight: 500 }}>Claude 3.5 Sonnet</span>
              </div>
              <span style={{ color: '#ffffff', fontWeight: 700 }}>$4.2K</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} />
                <span style={{ color: '#d1d5db', fontWeight: 500 }}>Llama 3 70B</span>
              </div>
              <span style={{ color: '#ffffff', fontWeight: 700 }}>$0.1K</span>
            </div>
          </div>
        </div>

        {/* Column 2: OpenTelemetry Traces (Trace Tree View) (6 Cols) */}
        <div className="glass-panel" style={{ gridColumn: 'span 6', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={18} color="#06b6d4" />
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
                OpenTelemetry Traces (Trace Tree View)
              </h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#06b6d4', background: 'rgba(6, 182, 212, 0.1)', padding: '4px 8px', borderRadius: '6px', fontWeight: 600 }}>
              Live Trace Tree
            </span>
          </div>

          {/* Interactive Nested Trace Tree View */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.875rem' }}>
            
            {/* Level 0: Root Span */}
            <div 
              onClick={() => setSelectedSpan('root')}
              style={{ 
                padding: '12px 16px', 
                borderRadius: '12px', 
                background: selectedSpan === 'root' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.03)', 
                border: selectedSpan === 'root' ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid rgba(255, 255, 255, 0.06)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <User size={16} color="#818cf8" />
                </div>
                <div>
                  <p style={{ fontWeight: 700, color: '#ffffff' }}>Root Span</p>
                  <p style={{ fontSize: '0.75rem', color: '#9ca3af' }}>user_request</p>
                </div>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: 600 }}>1,180ms</span>
            </div>

            {/* Level 1: llm_gen (Indented) */}
            <div style={{ paddingLeft: '24px', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '10px', top: '0', bottom: '50%', width: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />
              <div style={{ position: 'absolute', left: '10px', top: '50%', width: '12px', height: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />

              <div 
                onClick={() => setSelectedSpan('llm_gen')}
                style={{ 
                  padding: '10px 14px', 
                  borderRadius: '10px', 
                  background: selectedSpan === 'llm_gen' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(255, 255, 255, 0.03)', 
                  border: selectedSpan === 'llm_gen' ? '1px solid rgba(6, 182, 212, 0.5)' : '1px solid rgba(255, 255, 255, 0.06)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Globe size={16} color="#22d3ee" />
                  <div>
                    <p style={{ fontWeight: 600, color: '#ffffff' }}>llm_gen</p>
                    <p style={{ fontSize: '0.75rem', color: '#9ca3af' }}>llm_gen</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#22d3ee', fontWeight: 600 }}>650ms</span>
                  <span className="badge badge-emerald" style={{ padding: '2px 6px', fontSize: '0.65rem' }}>OK</span>
                </div>
              </div>
            </div>

            {/* Level 2: vector_db_search (Nested) */}
            <div style={{ paddingLeft: '48px', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '34px', top: '0', bottom: '50%', width: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />
              <div style={{ position: 'absolute', left: '34px', top: '50%', width: '12px', height: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />

              <div 
                onClick={() => setSelectedSpan('vector_db')}
                style={{ 
                  padding: '10px 14px', 
                  borderRadius: '10px', 
                  background: selectedSpan === 'vector_db' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(255, 255, 255, 0.03)', 
                  border: selectedSpan === 'vector_db' ? '1px solid rgba(52, 211, 153, 0.5)' : '1px solid rgba(255, 255, 255, 0.06)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Database size={16} color="#34d399" />
                  <div>
                    <p style={{ fontWeight: 600, color: '#ffffff' }}>vector_db_search</p>
                    <p style={{ fontSize: '0.75rem', color: '#9ca3af' }}>vector_db_search</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>110ms</span>
                  <span className="badge badge-emerald" style={{ padding: '2px 6px', fontSize: '0.65rem' }}>OK</span>
                </div>
              </div>
            </div>

            {/* Level 2: llm_inference (Nested with Anomaly Spike!) */}
            <div style={{ paddingLeft: '48px', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '34px', top: '0', bottom: '50%', width: '2px', background: 'rgba(244, 63, 94, 0.4)' }} />
              <div style={{ position: 'absolute', left: '34px', top: '50%', width: '12px', height: '2px', background: 'rgba(244, 63, 94, 0.4)' }} />

              <div 
                onClick={() => setSelectedSpan('llm_inference')}
                style={{ 
                  padding: '10px 14px', 
                  borderRadius: '10px', 
                  background: selectedSpan === 'llm_inference' ? 'rgba(244, 63, 94, 0.25)' : 'rgba(244, 63, 94, 0.1)', 
                  border: '1px solid rgba(244, 63, 94, 0.5)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  boxShadow: '0 0 15px rgba(244, 63, 94, 0.15)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Cpu size={16} color="#f87171" />
                  <div>
                    <p style={{ fontWeight: 600, color: '#ffffff' }}>llm_inference</p>
                    <p style={{ fontSize: '0.75rem', color: '#f87171' }}>• Error: Latency Spike</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#f87171', fontWeight: 700 }}>420ms</span>
                  <span className="badge badge-rose" style={{ padding: '2px 6px', fontSize: '0.65rem' }}>
                    <AlertTriangle size={10} /> SPIKE
                  </span>
                </div>
              </div>
            </div>

            {/* Level 3: token_gen (Deeply Indented) */}
            <div style={{ paddingLeft: '72px', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '58px', top: '0', bottom: '50%', width: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />
              <div style={{ position: 'absolute', left: '58px', top: '50%', width: '12px', height: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />

              <div 
                style={{ 
                  padding: '8px 12px', 
                  borderRadius: '8px', 
                  background: 'rgba(255, 255, 255, 0.02)', 
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.8rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Zap size={14} color="#818cf8" />
                  <span style={{ color: '#d1d5db' }}>token_gen</span>
                </div>
                <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>150ms</span>
              </div>
            </div>

            {/* Level 3: api_call (Deeply Indented) */}
            <div style={{ paddingLeft: '72px', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '58px', top: '0', bottom: '50%', width: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />
              <div style={{ position: 'absolute', left: '58px', top: '50%', width: '12px', height: '2px', background: 'rgba(255, 255, 255, 0.15)' }} />

              <div 
                style={{ 
                  padding: '8px 12px', 
                  borderRadius: '8px', 
                  background: 'rgba(255, 255, 255, 0.02)', 
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.8rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Globe size={14} color="#38bdf8" />
                  <span style={{ color: '#d1d5db' }}>api_call</span>
                </div>
                <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>80ms</span>
              </div>
            </div>

          </div>
        </div>

        {/* Column 3: Alerts & Notifications Feed (3 Cols) */}
        <div className="glass-panel" style={{ gridColumn: 'span 3', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Alerts & Notifications</h3>
            <span style={{ color: '#6b7280', fontSize: '0.75rem', cursor: 'pointer' }}>•••</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            
            {/* Alert Item 1: Critical */}
            {!dismissedAlerts.includes('alert-1') && (
              <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(244, 63, 94, 0.12)', border: '1px solid rgba(244, 63, 94, 0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={16} color="#f87171" />
                    <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.875rem' }}>Critical Anomaly</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>12:48 PM</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#d1d5db' }}>
                  LLM Latency Spike (API Gateway: 4s)
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button 
                    onClick={() => alert('Investigating trace anomaly...')}
                    style={{ padding: '4px 10px', borderRadius: '6px', background: 'rgba(244, 63, 94, 0.3)', color: '#ffffff', border: 'none', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                  >
                    Investigate
                  </button>
                  <button 
                    onClick={() => handleDismiss('alert-1')}
                    style={{ padding: '4px 10px', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.05)', color: '#9ca3af', border: 'none', fontSize: '0.75rem', cursor: 'pointer' }}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}

            {/* Alert Item 2: Warning */}
            {!dismissedAlerts.includes('alert-2') && (
              <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={16} color="#fbbf24" />
                    <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.875rem' }}>Warning</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>12:35 PM</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#d1d5db' }}>
                  High Memory Usage (Inference Node-4)
                </p>
              </div>
            )}

            {/* Alert Item 3: Notification */}
            {!dismissedAlerts.includes('alert-3') && (
              <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Bell size={16} color="#60a5fa" />
                    <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.875rem' }}>Notification</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>12:15 PM</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#d1d5db' }}>
                  New Deployment Successful (v2.1)
                </p>
              </div>
            )}

          </div>
        </div>

      </div>

    </div>
  );
};
