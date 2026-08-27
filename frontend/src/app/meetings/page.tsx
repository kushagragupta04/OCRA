'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Meeting } from '@/lib/types';
import { UploadTranscriptModal } from '@/components/meetings/UploadTranscriptModal';
import { Layers, Upload, Clock, CheckCircle2, AlertCircle, ArrowRight, Sparkles } from 'lucide-react';

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const fetchMeetings = async () => {
    try {
      setLoading(true);
      const data = await api.getMeetings();
      setMeetings(data);
    } catch (err) {
      console.error('Failed to load meetings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, []);

  const handleUploadSubmit = async (title: string, rawText: string) => {
    const res = await api.createMeeting({
      title,
      raw_text: rawText,
      project_key: 'PAY'
    }, true);
    await fetchMeetings();
  };

  return (
    <div className="content-wrapper">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
            Meeting Execution Archive
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            All recorded sessions and uploaded transcripts processed into Jira actions.
          </p>
        </div>

        <button
          onClick={() => setIsUploadOpen(true)}
          className="btn btn-primary"
        >
          <Upload size={16} />
          Upload Transcript
        </button>
      </div>

      {/* Grid of Meetings */}
      {loading ? (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '60px 0' }}>
          Loading meetings...
        </div>
      ) : meetings.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Layers size={48} color="var(--border-accent)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
            No Meetings Ingested Yet
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Start a Live Meeting session or upload a transcript to generate Jira executions.
          </p>
          <button onClick={() => setIsUploadOpen(true)} className="btn btn-primary">
            <Upload size={16} /> Upload First Transcript
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {meetings.map((m) => (
            <Link
              key={m.id}
              href={`/meetings/${m.id}`}
              style={{ textDecoration: 'none' }}
            >
              <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span className="badge badge-indigo">
                      {m.provider}
                    </span>
                    <span className={`badge ${m.status === 'COMPLETED' ? 'badge-emerald' : 'badge-amber'}`}>
                      {m.status}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '8px' }}>
                    {m.title}
                  </h3>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      <span>{new Date(m.started_at).toLocaleDateString()}</span>
                    </div>
                    <span>•</span>
                    <div>{m.segment_count} transcript segments</div>
                  </div>
                </div>

                <div style={{
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sparkles size={15} color="#38bdf8" />
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>
                      {m.action_count} Jira Actions
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8' }}>
                    Open Workbench <ArrowRight size={14} />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <UploadTranscriptModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSubmit={handleUploadSubmit}
      />
    </div>
  );
}
