export interface Segment {
  id: string;
  meeting_id: string;
  speaker_id: string;
  speaker_name: string;
  start_ms: int;
  end_ms: int;
  text: string;
}

export type int = number;

export interface Meeting {
  id: string;
  title: string;
  provider: string;
  external_id?: string;
  started_at: string;
  ended_at?: string;
  transcript_hash?: string;
  status: 'IN_PROGRESS' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  segment_count: number;
  action_count: number;
  segments?: Segment[];
}

export interface EvidenceRef {
  id?: string;
  segment_id: string;
  start_ms: number;
  end_ms: number;
  evidence_text: string;
}

export interface ConflictDetails {
  affected_issue_key: string;
  affected_issue_summary: string;
  old_decision: string;
  new_evidence: string;
  recommendation: string;
  risk_level: string;
}

export interface ApprovalInfo {
  id: string;
  required: boolean;
  reviewer?: string;
  decision: 'PENDING' | 'APPROVED' | 'REJECTED';
  comment?: string;
  decided_at?: string;
}

export interface ExecutionInfo {
  id: string;
  operation: string;
  idempotency_key: string;
  status: 'PENDING' | 'EXECUTING' | 'SUCCESS' | 'FAILED';
  jira_issue_key?: string;
  jira_response_id?: string;
  error_code?: string;
  error_message?: string;
  retry_count: number;
  executed_at: string;
}

export interface Action {
  id: string;
  meeting_id: string;
  action_type: 'CREATE' | 'UPDATE' | 'ASSIGN' | 'COMMENT' | 'SHIFT_DEADLINE' | 'TRANSITION' | 'CONFLICT' | 'NO_ACTION';
  summary: string;
  description?: string;
  target_issue_key?: string;
  project_key: string;
  issue_type: string;
  owner_account_id?: string;
  owner_name?: string;
  due_at?: string;
  priority?: string;
  confidence: number;
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'PROPOSED' | 'AUTO_EXECUTED' | 'REQUIRES_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXECUTING' | 'COMPLETED' | 'FAILED';
  reason: string;
  conflict_payload?: string;
  transition_name?: string;
  created_at: string;
  evidence: EvidenceRef[];
  executions: ExecutionInfo[];
  approval?: ApprovalInfo;
  conflict_info?: ConflictDetails;
}

export interface ExecutionPlan {
  meeting_id: string;
  total_actions: number;
  auto_executable: Action[];
  requires_approval: Action[];
  conflicts: Action[];
  executed: Action[];
  policy_summary: {
    total: number;
    executed_count: number;
    pending_approval_count: number;
    conflicts_count: number;
  };
}

export interface JiraUser {
  account_id: string;
  display_name: string;
  email?: string;
  active: boolean;
}

export interface JiraComment {
  id: string;
  author: string;
  body: string;
  created: string;
}

export interface JiraIssue {
  id: string;
  key: string;
  summary: string;
  description?: string;
  status: string;
  issue_type: string;
  assignee?: JiraUser;
  priority: string;
  due_date?: string;
  created: string;
  updated: string;
  comments: JiraComment[];
}

export interface JiraConfig {
  id: string;
  project_key: string;
  project_name: string;
  auto_execute_enabled: boolean;
  min_confidence_threshold: number;
  kill_switch_active: boolean;
  allowed_transitions: string[];
}

export interface AuditEvent {
  id: string;
  actor: string;
  action_id?: string;
  meeting_id?: string;
  event_type: string;
  before_state?: string;
  after_state?: string;
  timestamp: string;
}
