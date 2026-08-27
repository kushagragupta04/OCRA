'use client';

import React from 'react';
import { Action } from '@/lib/types';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  User,
  ArrowRight,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  XCircle,
  FileCheck,
  Calendar
} from 'lucide-react';
import Link from 'next/link';

interface Props {
  action: Action;
  onHighlightEvidence: (segmentId: string) => void;
  onApprove?: (actionId: string) => void;
  onReject?: (actionId: string) => void;
}

export const ActionCard: React.FC<Props> = ({
  action,
  onHighlightEvidence,
  onApprove,
  onReject
}) => {
  const getActionBadgeClass = (type: string) => {
    switch (type) {
      case 'CREATE':
        return 'badge-emerald';
      case 'SHIFT_DEADLINE':
        return 'badge-cyan';
      case 'CONFLICT':
        return 'badge-rose';
      case 'COMMENT':
        return 'badge-indigo';
      case 'ASSIGN':
        return 'badge-amber';
      default:
        return 'badge-indigo';
    }
  };

  const getStatusBadge = () => {
    switch (action.status) {
      case 'COMPLETED':
      case 'AUTO_EXECUTED':
        return <span className="badge badge-emerald">✓ Executed in Jira</span>;
      case 'REQUIRES_APPROVAL':
        return <span className="badge badge-amber">⚠️ Pending Approval</span>;
      case 'REJECTED':
        return <span className="badge badge-rose">✕ Rejected</span>;
      default:
        return <span className="badge badge-indigo">● {action.status}</span>;
    }
  };

  const isConflict = action.action_type === 'CONFLICT' || !!action.conflict_info;

  return (
    <div
      className="glass-panel"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        borderLeft: isConflict
          ? '4px solid #f43f5e'
          : action.status === 'COMPLETED'
          ? '4px solid #10b981'
          : '4px solid #f59e0b'
      }}
    >
      {/* Header: Action Type, Target Issue Key & Status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${getActionBadgeClass(action.action_type)}`}>
            {action.action_type}
          </span>
          {action.target_issue_key && (
            <span style={{
              fontSize: '0.8rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '6px',
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.3)'
            }}>
              {action.target_issue_key}
            </span>
          )}
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Project: <strong>{action.project_key}</strong>
          </span>
        </div>

        <div>{getStatusBadge()}</div>
      </div>

      {/* Summary */}
      <div>
        <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
          {action.summary}
        </h4>
        {action.description && (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            {action.description}
          </p>
        )}
      </div>

      {/* Meta Pills (Owner, Due Date, Confidence, Risk) */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px', fontSize: '0.8rem' }}>
        {action.owner_name && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#f8fafc' }}>
            <User size={14} color="#38bdf8" />
            <span>Owner: <strong>{action.owner_name}</strong></span>
          </div>
        )}

        {action.due_at && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#f8fafc' }}>
            <Calendar size={14} color="#f59e0b" />
            <span>Due: <strong>{action.due_at}</strong></span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--text-muted)' }}>
          <Sparkles size={14} color="#a855f7" />
          <span>Confidence: <strong>{Math.round(action.confidence * 100)}%</strong></span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{
            fontSize: '0.72rem',
            padding: '2px 6px',
            borderRadius: '4px',
            fontWeight: 700,
            background: action.risk === 'HIGH' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(16, 185, 129, 0.2)',
            color: action.risk === 'HIGH' ? '#f43f5e' : '#10b981'
          }}>
            {action.risk} RISK
          </span>
        </div>
      </div>

      {/* Conflict / Contradiction Inspector (Old Decision vs New Decision) */}
      {isConflict && action.conflict_info && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.08)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          borderRadius: '8px',
          padding: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: '#fb7185', fontWeight: 700, fontSize: '0.85rem' }}>
            <AlertTriangle size={16} />
            <span>Contradiction Detected With Active Work</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '10px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px', borderRadius: '6px', fontSize: '0.8rem' }}>
              <div style={{ color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
                Existing Backlog State ({action.conflict_info.affected_issue_key}):
              </div>
              <div style={{ color: '#f8fafc' }}>{action.conflict_info.old_decision}</div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px', borderRadius: '6px', fontSize: '0.8rem' }}>
              <div style={{ color: '#fb7185', fontWeight: 600, marginBottom: '4px' }}>
                New Meeting Decision:
              </div>
              <div style={{ color: '#ffffff' }}>{action.conflict_info.new_evidence}</div>
            </div>
          </div>

          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            <strong>Recommendation:</strong> {action.conflict_info.recommendation}
          </div>
        </div>
      )}

      {/* Rationale */}
      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.4)', padding: '8px 12px', borderRadius: '6px' }}>
        <strong>Reasoning:</strong> {action.reason}
      </div>

      {/* Evidence Citations (Click to Jump) */}
      {action.evidence && action.evidence.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
            Meeting Evidence:
          </span>
          {action.evidence.map((ev, idx) => (
            <button
              key={idx}
              onClick={() => onHighlightEvidence(ev.segment_id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '6px',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                color: '#818cf8',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              title="Click to jump and highlight this quote in the transcript"
            >
              <Clock size={12} />
              <span>{Math.floor(ev.start_ms / 1000)}s-{Math.floor(ev.end_ms / 1000)}s: &quot;{ev.evidence_text.slice(0, 32)}...&quot;</span>
              <ArrowRight size={12} />
            </button>
          ))}
        </div>
      )}

      {/* Actions / Approval Controls */}
      {action.status === 'REQUIRES_APPROVAL' && onApprove && onReject && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
          <button
            onClick={() => onApprove(action.id)}
            className="btn btn-success"
            style={{ padding: '6px 14px', fontSize: '0.82rem' }}
          >
            <CheckCircle2 size={15} />
            Approve &amp; Execute
          </button>
          <button
            onClick={() => onReject(action.id)}
            className="btn btn-danger"
            style={{ padding: '6px 14px', fontSize: '0.82rem' }}
          >
            <XCircle size={15} />
            Reject
          </button>
        </div>
      )}

      {action.status === 'COMPLETED' && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: '#10b981', marginTop: '4px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <FileCheck size={15} /> Mutation executed idempotently in Jira
          </span>
          <Link
            href="/sandbox"
            style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38bdf8', textDecoration: 'none', fontWeight: 600 }}
          >
            Inspect in Sandbox <ExternalLink size={13} />
          </Link>
        </div>
      )}
    </div>
  );
};
