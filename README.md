# OCRA: Operational Conversational Reasoning Agent
### Meeting-to-Jira Engineering Execution Agent

OCRA is an engineering execution system that joins or ingests engineering meeting conversations, deterministically extracts evidence-backed decisions, maps people and existing work, detects duplicate tickets and scope contradictions, applies configurable policy gating, and safely executes mutations via Jira Cloud REST APIs.

---

## 🌟 Key Features & Workflow

### 1. Best Demo: Live Meeting Experience
- **Join/Simulate Live Engineering Sync**: Stream speech segments with real-time speaker identification.
- **Conclude Meeting Trigger**: Ending the meeting automatically kicks off the 15-step reasoning pipeline.
- **Traceable Execution Plan**: Every proposed ticket, comment, or deadline shift is linked directly to exact timestamps and transcript quotes.
- **Click-to-Jump Traceability**: Clicking any evidence citation badge scrolls to and highlights the corresponding speaker statement in the transcript with a glowing pulse.

### 2. Fallback Ingestion: Transcript Upload
- Upload or paste timestamped transcripts (JSON, WebVTT, SRT, or plain text `[00:15] Speaker: ...`).
- Instant deduplication via SHA-256 transcript hashing.

### 3. Deep Work Management Operations
- 🎫 **Create Issues**: High-confidence task creation with ADF formatted descriptions and evidence callouts.
- 📅 **Shift Deadlines**: Explicitly updates due dates with reasoning comments.
- 💬 **Contextual Comments**: Adds timestamped decision notes to existing Jira issues.
- 👤 **Assignee Handoffs**: Resolves meeting speakers to Jira account IDs.
- 🔀 **Status Transitions**: Moves tickets through workflow states (`To Do` $\rightarrow$ `In Progress` $\rightarrow$ `In Review` $\rightarrow$ `Done`).
- ⚠️ **Conflict & Contradiction Detection**: Flags pivots (e.g. dropping old password-reset approach vs active ticket `PAY-104`) and halts for human sign-off with Old vs New decision diffs.

### 4. Enterprise Safety & Reliability
- 🛡️ **Prompt Injection Defense**: Transcripts are treated strictly as untrusted quoted data, preventing malicious override commands.
- 🔒 **Deterministic Idempotency**: Unique keys prevent duplicate Jira mutations on network retries or web UI refreshes.
- 🚨 **Master Kill-Switch**: Instantly suspends all autonomous execution across the workspace.
- 📜 **Immutable Audit Trail**: Chronological event ledger recording before/after states for all actions.
- 🧪 **Interactive Jira Mock Sandbox**: Built-in visual Jira board simulator supporting full REST v3 data model for instant testing.

---

## 🛠️ Requirements & Setup

### Requirements From Your End:
| Requirement | Status | Description |
| :--- | :--- | :--- |
| **Python 3.10+** | Required | Backend FastAPI runtime |
| **Node.js 18+** | Required | Frontend Next.js runtime |
| **LLM API Key (Gemini or OpenAI)** | *Optional* | If provided, used for live extraction. If omitted, built-in deterministic heuristic extraction runs offline seamlessly. |
| **Atlassian Jira Cloud Account** | *Optional* | If provided, connects via OAuth 2.0 (3LO). If omitted, built-in Jira Mock Sandbox runs out-of-the-box. |

---

## 🚀 Quickstart Guide

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend unit & integration tests
pytest -v

# Start FastAPI server on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🧪 Testing the Section 20 & 25 Demo Scenario

1. Open **[http://localhost:3000](http://localhost:3000)**.
2. Click **"Run E2E Demo Meeting"** in the top header (or click **"Simulate Section 20 Dialogue"** in the Live Meeting Room).
3. The meeting dialogue will stream:
   - *Rahul: "Rahul will implement OAuth backend by Friday."*
   - *Priya: "Priya will add the login UI."*
   - *Alex: "We are dropping the old password-reset approach in favor of Google OAuth."*
4. Click **"End Meeting & Execute Jira Changes"**.
5. Observe the generated Execution Plan:
   - 🟢 `PAY-106` (Implement OAuth 2.0 Backend Architecture - Rahul, due Friday) $\rightarrow$ **Auto-Executed**
   - 🟢 `PAY-105` (Develop Login UI - Priya) $\rightarrow$ **Auto-Executed**
   - 🔴 `PAY-104` (Password Reset Flow contradiction) $\rightarrow$ **Halted for Human Review**
6. Click any **Evidence Citation Badge** on the right to watch the left transcript pane jump directly to the quote.
7. Click **"Approve & Execute"** on the conflict card $\rightarrow$ Open **Jira Sandbox Board** to verify the tickets and decision comments in real time!
