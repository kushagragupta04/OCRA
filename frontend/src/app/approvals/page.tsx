'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Action } from '@/lib/types';
import { ActionCard } from '@/components/meetings/ActionCard';
import { CheckCircle2, ShieldAlert, RefreshCw, Inbox } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ApprovalsPage() {
  const router = useRouter();
  const [pendingActions, setPendingActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const data = await api.getPendingApprovals();
      setPendingActions(data);
    } catch (err) {
      console.error('Failed to load pending approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleApprove = async (actionId: string) => {
    try {
      await api.approveAction(actionId, { reviewer: 'Engineering Lead' });
      await fetchApprovals();
    } catch (err: any) {
      alert(`Approval execution failed: ${err.message}`);
    }
  };

  const handleReject = async (actionId: string) => {
    try {
      await api.rejectAction(actionId, { reviewer: 'Engineering Lead' });
      await fetchApprovals();
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    }
  };

  return (
    <div className="content-wrapper" style={{ maxWidth: '1000px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
            Action Approval Hub
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Engineering decisions requiring explicit human verification before Jira execution.
          </p>
        </div>

        <button onClick={fetchApprovals} className="btn btn-secondary">
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          Loading pending approvals...
        </div>
      ) : pendingActions.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <CheckCircle2 size={48} color="#10b981" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
            Approval Inbox Zero
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            All high-confidence actions were executed or approved. No actions are currently blocked.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {pendingActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onHighlightEvidence={() => router.push(`/meetings/${action.meeting_id}`)}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      )}
    </div>
  );
}
