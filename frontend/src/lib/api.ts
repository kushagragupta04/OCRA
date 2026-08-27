import {
  Meeting,
  ExecutionPlan,
  Action,
  JiraIssue,
  JiraConfig,
  AuditEvent,
  Segment
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {})
    }
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Error [${res.status}]: ${errText || res.statusText}`);
  }

  return res.json();
}

export const api = {
  // Meetings
  getMeetings: () => fetchJSON<Meeting[]>('/api/meetings'),
  getMeeting: (id: string) => fetchJSON<Meeting>(`/api/meetings/${id}`),
  createMeeting: (payload: { title?: string; provider?: string; raw_text?: string; segments?: any[]; project_key?: string }, autoProcess = true) =>
    fetchJSON<Meeting>(`/api/meetings?auto_process=${autoProcess}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  appendLiveChunk: (meetingId: string, chunk: { speaker_name: string; start_ms: number; end_ms: number; text: string }) =>
    fetchJSON<{ status: string; segment_id: string }>(`/api/meetings/${meetingId}/chunks`, {
      method: 'POST',
      body: JSON.stringify(chunk)
    }),
  processMeeting: (meetingId: string, projectKey = 'PAY') =>
    fetchJSON<Meeting>(`/api/meetings/${meetingId}/process?project_key=${projectKey}`, {
      method: 'POST'
    }),

  // Actions & Execution Plan
  getMeetingActions: (meetingId: string) => fetchJSON<ExecutionPlan>(`/api/meetings/${meetingId}/actions`),
  getPendingApprovals: () => fetchJSON<Action[]>('/api/approvals/pending'),
  approveAction: (actionId: string, payload: { reviewer?: string; comment?: string }) =>
    fetchJSON<Action>(`/api/actions/${actionId}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  rejectAction: (actionId: string, payload: { reviewer?: string; comment?: string }) =>
    fetchJSON<Action>(`/api/actions/${actionId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  executeAction: (actionId: string) =>
    fetchJSON<Action>(`/api/actions/${actionId}/execute`, {
      method: 'POST'
    }),

  // Jira Sandbox & Settings
  getSandboxIssues: () => fetchJSON<{ issues: JiraIssue[] }>('/api/integrations/jira/sandbox/issues'),
  resetSandbox: () => fetchJSON<{ message: string }>('/api/integrations/jira/sandbox/reset', { method: 'POST' }),
  getJiraSettings: (projectKey = 'PAY') => fetchJSON<JiraConfig>(`/api/integrations/jira/settings?project_key=${projectKey}`),
  updateJiraSettings: (payload: Partial<JiraConfig>) =>
    fetchJSON<JiraConfig>('/api/integrations/jira/settings', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  // Executions & Audit
  getExecutions: () => fetchJSON<any[]>('/api/executions'),
  getAuditEvents: (meetingId?: string) =>
    fetchJSON<AuditEvent[]>(`/api/audit${meetingId ? `?meeting_id=${meetingId}` : ''}`),

  // Pre-seeded Demos
  seedE2EDemo: () => fetchJSON<Meeting>('/api/demo/seed-e2e', { method: 'POST' }),
  seedInjectionDemo: () => fetchJSON<Meeting>('/api/demo/seed-injection', { method: 'POST' }),
  resetAllDemo: () => fetchJSON<{ message: string }>('/api/demo/reset-all', { method: 'POST' })
};
