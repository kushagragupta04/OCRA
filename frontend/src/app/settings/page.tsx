'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { JiraConfig } from '@/lib/types';
import {
  Settings,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  Lock,
  RefreshCw,
  Trello
} from 'lucide-react';

export default function SettingsPage() {
  const [config, setConfig] = useState<JiraConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await api.getJiraSettings('PAY');
      setConfig(data);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleUpdate = async (updatedFields: Partial<JiraConfig>) => {
    if (!config) return;
    try {
      setSaving(true);
      const updated = await api.updateJiraSettings({
        project_key: config.project_key,
        ...updatedFields
      });
      setConfig(updated);
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="content-wrapper" style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
        Loading integration settings...
      </div>
    );
  }

  return (
    <div className="content-wrapper" style={{ maxWidth: '880px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
          Integration &amp; Execution Policy Settings
        </h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Configure Jira connection, confidence gating, and autonomous execution safety controls.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Workspace Kill-Switch */}
        <div
          className="glass-panel"
          style={{
            borderLeft: config.kill_switch_active ? '4px solid #f43f5e' : '4px solid #10b981',
            background: config.kill_switch_active ? 'rgba(244, 63, 94, 0.08)' : 'var(--bg-card)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={20} color={config.kill_switch_active ? '#f43f5e' : '#10b981'} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff' }}>
                Master Autonomy Kill-Switch
              </h3>
            </div>

            <button
              onClick={() => handleUpdate({ kill_switch_active: !config.kill_switch_active })}
              className={config.kill_switch_active ? 'btn btn-danger' : 'btn btn-secondary'}
              style={{ padding: '6px 14px', fontSize: '0.82rem' }}
            >
              {config.kill_switch_active ? 'KILL SWITCH ACTIVE' : 'Kill Switch Disarmed'}
            </button>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            When activated, all autonomous Jira executions are immediately suspended. Every extracted action will strictly require human approval.
          </p>
        </div>

        {/* Policy Thresholds */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={18} color="#38bdf8" />
            Confidence &amp; Safety Policy
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Auto Execute Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.9rem' }}>
                  Allow Autonomous Execution for Safe Actions
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Automatically creates high-confidence issues with explicit owners and no duplicate conflicts.
                </div>
              </div>

              <input
                type="checkbox"
                checked={config.auto_execute_enabled}
                onChange={(e) => handleUpdate({ auto_execute_enabled: e.target.checked })}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
            </div>

            {/* Confidence Slider */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.9rem' }}>
                  Minimum Confidence Threshold
                </span>
                <span style={{ fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                  {Math.round(config.min_confidence_threshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="0.99"
                step="0.05"
                value={config.min_confidence_threshold}
                onChange={(e) => handleUpdate({ min_confidence_threshold: parseFloat(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                <span>50% (Permissive)</span>
                <span>80% (Recommended)</span>
                <span>99% (Strict)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Jira Cloud Integration Details */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Trello size={18} color="#818cf8" />
            Jira Cloud Connection (OAuth 2.0 3LO)
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.85rem' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Adapter Mode: </span>
              <strong style={{ color: '#10b981' }}>Jira Mock Sandbox (Active)</strong>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Target Project: </span>
              <strong style={{ color: '#38bdf8' }}>{config.project_key} ({config.project_name})</strong>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>OAuth Scopes: </span>
              <strong style={{ color: '#ffffff' }}>read:jira-work, write:jira-work, read:jira-user</strong>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Document Format: </span>
              <strong style={{ color: '#ffffff' }}>Atlassian Document Format (ADF v1)</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
