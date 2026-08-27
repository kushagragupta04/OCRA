'use client';

import React, { useState } from 'react';
import { ExecutionPlan, Action } from '@/lib/types';
import { ActionCard } from './ActionCard';
import { CheckCircle, AlertTriangle, ShieldCheck, Flame, ListFilter } from 'lucide-react';

interface Props {
  plan: ExecutionPlan;
  onHighlightEvidence: (segmentId: string) => void;
  onApproveAction: (actionId: string) => void;
  onRejectAction: (actionId: string) => void;
}

export const ExecutionPlanView: React.FC<Props> = ({
  plan,
  onHighlightEvidence,
  onApproveAction,
  onRejectAction
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'safe' | 'pending' | 'conflicts'>('all');

  const allActions = [
    ...(plan.executed || []),
    ...(plan.auto_executable || []),
    ...(plan.requires_approval || []),
    ...(plan.conflicts || [])
  ];

  // Deduplicate actions by ID if present across categories
  const uniqueAll = Array.from(new Map(allActions.map((a) => [a.id, a])).values());

  const getFilteredActions = () => {
    switch (activeTab) {
      case 'safe':
        return [...(plan.executed || []), ...(plan.auto_executable || [])];
      case 'pending':
        return plan.requires_approval || [];
      case 'conflicts':
        return plan.conflicts || [];
      default:
        return uniqueAll;
    }
  };

  const filtered = getFilteredActions();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Category Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <button
          onClick={() => setActiveTab('all')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: activeTab === 'all' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
            color: activeTab === 'all' ? '#ffffff' : 'var(--text-secondary)'
          }}
        >
          <ListFilter size={15} />
          All Actions ({uniqueAll.length})
        </button>

        <button
          onClick={() => setActiveTab('safe')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: activeTab === 'safe' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
            color: activeTab === 'safe' ? '#34d399' : 'var(--text-secondary)'
          }}
        >
          <CheckCircle size={15} color="#10b981" />
          Safe / Executed ({plan.executed.length + plan.auto_executable.length})
        </button>

        <button
          onClick={() => setActiveTab('pending')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: activeTab === 'pending' ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
            color: activeTab === 'pending' ? '#fbbf24' : 'var(--text-secondary)'
          }}
        >
          <AlertTriangle size={15} color="#f59e0b" />
          Needs Approval ({plan.requires_approval.length})
        </button>

        <button
          onClick={() => setActiveTab('conflicts')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: activeTab === 'conflicts' ? 'rgba(244, 63, 94, 0.2)' : 'transparent',
            color: activeTab === 'conflicts' ? '#fb7185' : 'var(--text-secondary)'
          }}
        >
          <Flame size={15} color="#f43f5e" />
          Conflicts ({plan.conflicts.length})
        </button>
      </div>

      {/* Action Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {filtered.length === 0 ? (
          <div className="glass-panel" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>
            No actions in this category.
          </div>
        ) : (
          filtered.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onHighlightEvidence={onHighlightEvidence}
              onApprove={onApproveAction}
              onReject={onRejectAction}
            />
          ))
        )}
      </div>
    </div>
  );
};
