# OCRA - External Integration Plan & Guide

This document outlines everything you are expected to integrate into OCRA to move from the local development/sandbox environment to live production environments.

---

## 1. Integration Matrix Overview

| Integration | Priority | Purpose | Local Default (Zero Config) | Production Target |
| :--- | :--- | :--- | :--- | :--- |
| **Jira Cloud REST v3** | **High** | Real-time issue creation, transitions, comments | `JiraMockSandboxAdapter` (Pre-seeded board at `/sandbox`) | Atlassian OAuth 2.0 (3LO) Bearer Token |
| **LLM Provider** | **Medium** | Real-time extraction of decisions & evidence | Deterministic Rule-Based Reasoning Engine | Google Gemini 2.5 Flash / OpenAI GPT-4o |
| **Meeting Bot / Ingestion** | **Medium** | Audio recording & automated transcript streaming | Live Meeting Room Simulator & Manual Upload | Webhook Ingestion (Recall.ai / Zoom / Meet) |
| **Alternative Trackers** | *Optional* | Managing tickets outside of Jira | Extensible `JiraAdapter` Base Class | Linear / GitHub Projects / ClickUp |

---

## 2. Atlassian Jira Cloud Integration (OAuth 2.0 3LO)

To connect OCRA directly to your team's live Atlassian Cloud site:

### Step 1: Create an Atlassian Developer App
1. Go to the [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/).
2. Click **Create** $\rightarrow$ **OAuth 2.0 integration (3LO)**.
3. Give your app a name: `OCRA Engineering Agent`.

### Step 2: Configure Permissions (Scopes)
Under **Permissions**, enable the **Jira platform REST API** and add the following classic 3LO scopes:
- `read:jira-work`: Read issue details, projects, transitions, and fields.
- `write:jira-work`: Create issues, post ADF comments, shift due dates, and update workflows.
- `read:jira-user`: Search accessible team members for speaker resolution.
- `offline_access`: Receive refresh tokens for long-lived integration sessions.

### Step 3: Configure Callback URL
Under **Authorization**, set the redirect URI:
```text
http://localhost:8000/api/integrations/jira/callback
```
*(For production deployments, replace `localhost:8000` with your backend domain).*

### Step 4: Add Credentials to Environment
Copy your **Client ID** and **Client Secret** from the Atlassian Console and update `backend/.env`:
```bash
# backend/.env
USE_MOCK_JIRA=false
JIRA_CLIENT_ID="your-atlassian-client-id"
JIRA_CLIENT_SECRET="your-atlassian-client-secret"
JIRA_REDIRECT_URI="http://localhost:8000/api/integrations/jira/callback"
JIRA_CLOUD_ID="your-atlassian-cloud-id"
```

---

## 3. LLM Provider Integration (Gemini / OpenAI)

OCRA includes a high-fidelity deterministic extraction engine for offline work. To enable real-time generative reasoning with live LLMs:

### Option A: Google Gemini (Recommended)
1. Get a free API key at [Google AI Studio](https://aistudio.google.com/).
2. Add to `backend/.env`:
   ```bash
   GEMINI_API_KEY="AIzaSy..."
   DEFAULT_LLM_MODEL="gemini-2.5-flash"
   ```

### Option B: OpenAI
1. Get an API key from the [OpenAI Platform](https://platform.openai.com/api-keys).
2. Add to `backend/.env`:
   ```bash
   OPENAI_API_KEY="sk-..."
   ```

---

## 4. Voice Text Ingestion Flow (Meeting to Pipeline)

Voice audio is converted to text and ingested into the OCRA pipeline through two primary methods:

### Flow A: Live Meeting Ingestion (Live Streaming)
1. **Audio Capture**: A meeting recorder/bot (e.g., Zoom/Meet webhook, custom browser microphone recorder using Web Speech API) captures audio in real time.
2. **Real-time Transcription**: The audio is converted to text (either via Web Speech API in the browser or via Speech-to-Text services like Deepgram/Whisper by a meeting bot).
3. **Streaming Ingestion**: The transcription segments are sent chunk-by-chunk to the backend via:
   ```http
   POST /api/meetings/{meeting_id}/chunks
   Content-Type: application/json

   {
     "speaker_name": "Rahul",
     "start_ms": 12000,
     "end_ms": 17500,
     "text": "Rahul will implement OAuth backend by Friday."
   }
   ```
4. **Trigger Pipeline**: When the meeting is concluded, the frontend/bot triggers the pipeline via:
   ```http
   POST /api/meetings/{meeting_id}/process?project_key=PAY
   ```

### Flow B: Post-Meeting Fallback (File Upload)
1. **Audio/Video Recording**: The meeting is recorded normally.
2. **Transcription Export**: The meeting platform (Zoom, Meet, Teams) or a transcription service exports the transcript as a VTT, SRT, JSON, or text file.
3. **Full Ingestion**: The user uploads or pastes the transcript directly, and the system parses the timestamps and speakers in a single request:
   ```http
   POST /api/meetings?auto_process=true
   Content-Type: application/json

   {
     "title": "Weekly Sprint Planning",
     "raw_text": "[00:12] Rahul: Rahul will implement OAuth backend by Friday."
   }
   ```
   The ingestion service extracts speaker segments, saves them to the DB, and processes the pipeline.
  "provider": "zoom_bot",
  "project_key": "PAY"
}
```

### Endpoint 2: Stream Live Speech Chunks
As participants speak, the bot forwards timestamped chunks:
```http
POST /api/meetings/{meeting_id}/chunks
Content-Type: application/json

{
  "speaker_name": "Rahul",
  "start_ms": 12000,
  "end_ms": 17500,
  "text": "Rahul will implement OAuth backend by Friday."
}
```

### Endpoint 3: Conclude & Trigger Pipeline
When the meeting ends:
```http
POST /api/meetings/{meeting_id}/process?project_key=PAY
```

---

## 5. Adding New Work Management Adapters (Linear / GitHub)

The system is designed with an extensible adapter pattern located in `backend/app/adapters/`.

To integrate Linear or GitHub Projects:
1. Inherit from `JiraAdapter` in `backend/app/adapters/jira_base.py`.
2. Implement the standard async methods:
   - `search_issues(query, fields, limit)`
   - `create_issue(payload)`
   - `update_issue(issue_key, payload)`
   - `shift_deadline(issue_key, new_deadline, reason_adf)`
   - `add_comment(issue_key, comment_body)`
   - `transition_issue(issue_key, target_state)`
3. Register the new adapter in `backend/app/adapters/__init__.py`.
