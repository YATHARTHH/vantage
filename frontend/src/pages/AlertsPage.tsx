import React, { useEffect, useState } from 'react';
import { VantageAPI, AlertRecord } from '../api/client';
import { AlertTriangle, CheckCircle, Bell, ShieldAlert } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await VantageAPI.getAlerts(false);
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleResolve = async (id: string) => {
    try {
      await VantageAPI.resolveAlert(id);
      loadAlerts();
    } catch (err) {
      alert('Failed to resolve alert.');
    }
  };

  const activeIncidents = alerts.filter((a) => !a.resolved_at);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Anomaly Intelligence & Alerts</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
          Multi-detector anomaly engine covering cost spikes, latency degradation, error rates, and volume outages with incident suppression.
        </p>
      </div>

      {activeIncidents.length > 0 && (
        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '12px', padding: '16px 20px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <ShieldAlert size={28} color="#f87171" />
          <div>
            <h4 style={{ color: '#f87171', fontWeight: 700, fontSize: '1rem' }}>{activeIncidents.length} Active Incident(s) Triggered</h4>
            <p style={{ color: '#fca5a5', fontSize: '0.875rem' }}>Active incidents are suppressed from duplicate alerting until resolved by an operator.</p>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>Loading alert records...</div>
      ) : alerts.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <CheckCircle size={40} color="#34d399" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>All Systems Nominal</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px' }}>No anomaly alerts or active incidents reported.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {alerts.map((alert) => {
            const isResolved = !!alert.resolved_at;
            return (
              <div key={alert.id} className="glass-panel" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ padding: '12px', borderRadius: '10px', background: isResolved ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)' }}>
                    {isResolved ? <CheckCircle size={24} color="#34d399" /> : <AlertTriangle size={24} color="#f87171" />}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                      <span className={`badge ${isResolved ? 'badge-emerald' : 'badge-rose'}`}>{alert.severity.toUpperCase()}</span>
                      <span style={{ fontSize: '0.8rem', color: '#60a5fa' }}>Project: {alert.project_id}</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Strategy: {alert.detector_type}</span>
                    </div>
                    <h4 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{alert.title}</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Observed Value: <strong style={{ color: '#fff' }}>{alert.observed_value}</strong> | Threshold: <strong style={{ color: '#fff' }}>{alert.threshold_value}</strong>
                    </p>
                  </div>
                </div>

                <div>
                  {isResolved ? (
                    <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 600 }}>Resolved</span>
                  ) : (
                    <button className="glass-button" style={{ background: 'rgba(244, 63, 94, 0.2)', border: '1px solid rgba(244, 63, 94, 0.4)' }} onClick={() => handleResolve(alert.id || alert.alert_id || '')}>
                      Acknowledge & Resolve
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
