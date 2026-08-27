'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { AuditEvent } from '@/lib/types';
import { FileClock, RefreshCw, User, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAudit = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditEvents();
      setEvents(data);
    } catch (err) {
      console.error('Failed to load audit events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, []);

  const getEventBadge = (type: string) => {
    if (type.includes('SUCCESS') || type.includes('APPROVED')) return 'badge-emerald';
    if (type.includes('REJECTED') || type.includes('FAILED')) return 'badge-rose';
    if (type.includes('CONFLICT')) return 'badge-amber';
    return 'badge-indigo';
  };

  return (
    <div className="content-wrapper" style={{ maxWidth: '1100px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
            Immutable Audit Trail
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Cryptographic and deterministic event log of all transcript ingestions, reasoning steps, approvals, and mutations.
          </p>
        </div>

        <button onClick={fetchAudit} className="btn btn-secondary">
          <RefreshCw size={15} /> Refresh Audit Log
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          Loading audit trail...
        </div>
      ) : events.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <FileClock size={48} color="var(--border-accent)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff' }}>
            No Audit Events Recorded
          </h3>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {events.map((ev) => (
            <div key={ev.id} className="glass-panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`badge ${getEventBadge(ev.event_type)}`}>
                    {ev.event_type}
                  </span>
                  <span style={{ fontSize: '0.82rem', color: '#38bdf8', fontWeight: 600 }}>
                    Actor: {ev.actor}
                  </span>
                </div>

                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {new Date(ev.timestamp).toLocaleString()}
                </span>
              </div>

              {ev.after_state && (
                <pre style={{
                  background: 'rgba(15, 23, 42, 0.8)',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  overflowX: 'auto'
                }}>
                  {ev.after_state}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
