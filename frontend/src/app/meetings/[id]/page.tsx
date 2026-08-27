'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Meeting, ExecutionPlan, Action } from '@/lib/types';
import { TranscriptViewer } from '@/components/meetings/TranscriptViewer';
import { ExecutionPlanView } from '@/components/meetings/ExecutionPlanView';
import {
  ArrowLeft,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Clock,
  ShieldCheck,
  RefreshCw,
  Trello
} from 'lucide-react';
import Link from 'next/link';

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = params.id as string;

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [plan, setPlan] = useState<ExecutionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [highlightedSegmentId, setHighlightedSegmentId] = useState<string | null>(null);

  const loadMeetingData = async () => {
    try {
      setLoading(true);
      const [m, p] = await Promise.all([
        api.getMeeting(meetingId),
        api.getMeetingActions(meetingId)
      ]);
      setMeeting(m);
      setPlan(p);
    } catch (err) {
      console.error('Failed to load meeting details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (meetingId) {
      loadMeetingData();
    }
  }, [meetingId]);

  const handleApproveAction = async (actionId: string) => {
    try {
      await api.approveAction(actionId, { reviewer: 'Engineering Lead' });
      await loadMeetingData();
    } catch (err: any) {
      alert(`Approval execution failed: ${err.message}`);
    }
  };

  const handleRejectAction = async (actionId: string) => {
    try {
      await api.rejectAction(actionId, { reviewer: 'Engineering Lead' });
      await loadMeetingData();
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    }
  };

  if (loading || !meeting || !plan) {
    return (
      <div className="content-wrapper" style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)' }}>
        <RefreshCw className="animate-spin" size={24} style={{ margin: '0 auto 12px' }} />
        <div>Loading Meeting Workbench &amp; Reasoning Plan...</div>
      </div>
    );
  }

  return (
    <div className="content-wrapper" style={{ maxWidth: '1680px' }}>
      {/* Top Breadcrumb & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Link href="/meetings" className="btn btn-secondary" style={{ padding: '6px 12px' }}>
            <ArrowLeft size={16} /> Back
          </Link>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`badge ${meeting.status === 'COMPLETED' ? 'badge-emerald' : 'badge-amber'}`}>
                {meeting.status}
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                HASH: {meeting.transcript_hash?.slice(0, 8)}...
              </span>
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', marginTop: '2px' }}>
              {meeting.title}
            </h2>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Link href="/sandbox" className="btn btn-secondary" style={{ padding: '8px 14px' }}>
            <Trello size={16} color="#38bdf8" />
            Inspect Jira Board
          </Link>
          <button onClick={loadMeetingData} className="btn btn-secondary" style={{ padding: '8px 14px' }}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Total Actions
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', marginTop: '4px' }}>
            {plan.total_actions}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.75rem', color: '#10b981', textTransform: 'uppercase', fontWeight: 600 }}>
            Auto-Executed / Safe
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>
            {plan.executed.length + plan.auto_executable.length}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '0.75rem', color: '#f59e0b', textTransform: 'uppercase', fontWeight: 600 }}>
            Pending Human Review
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fbbf24', marginTop: '4px' }}>
            {plan.requires_approval.length}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px', borderLeft: '4px solid #f43f5e' }}>
          <div style={{ fontSize: '0.75rem', color: '#f43f5e', textTransform: 'uppercase', fontWeight: 600 }}>
            Scope Conflicts Flagged
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fb7185', marginTop: '4px' }}>
            {plan.conflicts.length}
          </div>
        </div>
      </div>

      {/* Split-Screen Interactive Workbench */}
      <div style={{ display: 'grid', gridTemplateColumns: '480px 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Left Pane: Synchronized Transcript with Pulsing Evidence Glow */}
        <div style={{ height: '750px', position: 'sticky', top: '90px' }}>
          <TranscriptViewer
            segments={meeting.segments || []}
            highlightedSegmentId={highlightedSegmentId}
            onSelectSegment={(seg) => setHighlightedSegmentId(seg.id)}
          />
        </div>

        {/* Right Pane: Traceable Execution Plan */}
        <div>
          <ExecutionPlanView
            plan={plan}
            onHighlightEvidence={(segId) => setHighlightedSegmentId(segId)}
            onApproveAction={handleApproveAction}
            onRejectAction={handleRejectAction}
          />
        </div>
      </div>
    </div>
  );
}
