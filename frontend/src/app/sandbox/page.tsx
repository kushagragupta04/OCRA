'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { JiraIssue } from '@/lib/types';
import {
  Trello,
  RefreshCw,
  RotateCcw,
  User,
  Calendar,
  MessageSquare,
  Sparkles,
  ExternalLink,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

const COLUMNS = ['To Do', 'In Progress', 'In Review', 'Done', 'Blocked'];

export default function JiraSandboxPage() {
  const [issues, setIssues] = useState<JiraIssue[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<JiraIssue | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  const fetchIssues = async () => {
    try {
      setLoading(true);
      const res = await api.getSandboxIssues();
      setIssues(res.issues);
      if (selectedIssue) {
        const updated = res.issues.find((i) => i.key === selectedIssue.key);
        if (updated) setSelectedIssue(updated);
      }
    } catch (err) {
      console.error('Failed to load sandbox issues:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIssues();
  }, []);

  const handleReset = async () => {
    if (!confirm('Are you sure you want to reset the Jira Mock Sandbox to initial backlog state?')) return;
    try {
      setResetting(true);
      await api.resetSandbox();
      await fetchIssues();
      setSelectedIssue(null);
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="content-wrapper" style={{ maxWidth: '1600px' }}>
      {/* Top Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-indigo">Simulator</span>
            <span className="badge badge-emerald">Jira Cloud REST v3</span>
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', marginTop: '4px' }}>
            Jira Sandbox Live Kanban Board
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Real-time reflection of Jira issues, ADF comments, and workflow transitions mutated by OCRA.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleReset}
            disabled={resetting}
            className="btn btn-secondary"
            style={{ color: '#fb7185' }}
          >
            <RotateCcw size={15} />
            {resetting ? 'Resetting...' : 'Reset Sandbox'}
          </button>
          <button onClick={fetchIssues} className="btn btn-secondary">
            <RefreshCw size={15} /> Refresh Board
          </button>
        </div>
      </div>

      {/* Kanban Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px', minHeight: '650px', alignItems: 'start' }}>
        {COLUMNS.map((colName) => {
          const colIssues = issues.filter((i) => i.status.toLowerCase() === colName.toLowerCase());

          return (
            <div
              key={colName}
              style={{
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                padding: '14px',
                minHeight: '500px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}
            >
              {/* Column Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                  {colName}
                </span>
                <span style={{
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: 'var(--text-muted)',
                  fontWeight: 600
                }}>
                  {colIssues.length}
                </span>
              </div>

              {/* Issues in Column */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {colIssues.map((issue) => {
                  const isSelected = selectedIssue?.key === issue.key;

                  return (
                    <div
                      key={issue.key}
                      onClick={() => setSelectedIssue(issue)}
                      style={{
                        background: isSelected ? 'rgba(99, 102, 241, 0.25)' : 'rgba(30, 41, 59, 0.7)',
                        border: isSelected ? '1px solid #6366f1' : '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '12px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: '#38bdf8',
                          fontFamily: 'var(--font-mono)'
                        }}>
                          {issue.key}
                        </span>
                        <span style={{
                          fontSize: '0.7rem',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: issue.priority === 'High' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                          color: issue.priority === 'High' ? '#fb7185' : '#94a3b8',
                          fontWeight: 600
                        }}>
                          {issue.priority}
                        </span>
                      </div>

                      <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff', marginBottom: '10px', lineHeight: '1.4' }}>
                        {issue.summary}
                      </h4>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <User size={12} color="#38bdf8" />
                          <span>{issue.assignee?.display_name || 'Unassigned'}</span>
                        </div>

                        {issue.comments && issue.comments.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#818cf8' }}>
                            <MessageSquare size={12} />
                            <span>{issue.comments.length}</span>
                          </div>
                        )}
                      </div>

                      {issue.due_date && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: '#f59e0b', marginTop: '6px' }}>
                          <Calendar size={11} />
                          <span>Due: {issue.due_date}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Issue Detail Modal / Slide-over */}
      {selectedIssue && (
        <div className="modal-overlay" onClick={() => setSelectedIssue(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                  {selectedIssue.key}
                </span>
                <span className="badge badge-emerald">{selectedIssue.status}</span>
                <span className="badge badge-indigo">{selectedIssue.issue_type}</span>
              </div>
              <button
                onClick={() => setSelectedIssue(null)}
                className="btn btn-secondary"
                style={{ padding: '4px 10px' }}
              >
                Close
              </button>
            </div>

            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', marginBottom: '16px' }}>
              {selectedIssue.summary}
            </h3>

            {/* Meta details */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Assignee: </span>
                <strong style={{ color: '#ffffff' }}>{selectedIssue.assignee?.display_name || 'Unassigned'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Priority: </span>
                <strong style={{ color: '#ffffff' }}>{selectedIssue.priority}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Due Date: </span>
                <strong style={{ color: selectedIssue.due_date ? '#f59e0b' : '#ffffff' }}>{selectedIssue.due_date || 'None'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Last Updated: </span>
                <strong style={{ color: '#ffffff' }}>{new Date(selectedIssue.updated).toLocaleTimeString()}</strong>
              </div>
            </div>

            {/* Description */}
            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '8px' }}>
                Description (ADF)
              </h4>
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                {selectedIssue.description || 'No description provided.'}
              </div>
            </div>

            {/* Comments & Meeting Decision History */}
            <div>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MessageSquare size={16} color="#38bdf8" />
                Comments &amp; Traceable Decision Notes ({selectedIssue.comments.length})
              </h4>

              {selectedIssue.comments.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No comments recorded yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedIssue.comments.map((comm) => (
                    <div
                      key={comm.id}
                      style={{
                        background: 'rgba(30, 41, 59, 0.6)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.8rem' }}>
                        <strong style={{ color: '#38bdf8' }}>{comm.author}</strong>
                        <span style={{ color: 'var(--text-muted)' }}>{new Date(comm.created).toLocaleTimeString()}</span>
                      </div>
                      <p style={{ fontSize: '0.85rem', color: '#f8fafc', whiteSpace: 'pre-wrap' }}>
                        {comm.body}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
