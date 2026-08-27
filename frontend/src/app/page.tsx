'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import {
  Radio,
  Mic,
  MicOff,
  Play,
  Square,
  Sparkles,
  Send,
  User,
  Clock,
  CheckCircle2,
  Bot,
  Zap,
  Layers,
  ArrowRight
} from 'lucide-react';

interface LiveSegment {
  speaker_name: string;
  start_ms: number;
  end_ms: number;
  text: string;
}

const SAMPLE_SCRIPT: LiveSegment[] = [
  {
    speaker_name: 'Rahul',
    start_ms: 0,
    end_ms: 4500,
    text: 'Rahul will implement OAuth backend by Friday.'
  },
  {
    speaker_name: 'Priya',
    start_ms: 5000,
    end_ms: 9000,
    text: 'Priya will add the login UI.'
  },
  {
    speaker_name: 'Alex',
    start_ms: 9500,
    end_ms: 15000,
    text: 'We are dropping the old password-reset approach in favor of Google OAuth.'
  }
];

export default function LiveMeetingPage() {
  const router = useRouter();
  const [meetingTitle, setMeetingTitle] = useState('Live Architecture & Backlog Sync');
  const [isMeetingActive, setIsMeetingActive] = useState(false);
  const [segments, setSegments] = useState<LiveSegment[]>([]);
  const [currentSpeaker, setCurrentSpeaker] = useState('Rahul');
  const [customUtterance, setCustomUtterance] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [isSimulatingScript, setIsSimulatingScript] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Timer tick during active meeting
  useEffect(() => {
    let interval: any;
    if (isMeetingActive) {
      interval = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(interval);
  }, [isMeetingActive]);

  // Auto scroll live transcript
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [segments]);

  // Start Meeting
  const handleStartMeeting = async () => {
    try {
      setIsMeetingActive(true);
      setSegments([]);
      // Create empty in-progress meeting on backend
      const res = await api.createMeeting(
        {
          title: meetingTitle,
          provider: 'live_stream',
          segments: [],
          project_key: 'PAY'
        },
        false // Do not auto process yet
      );
      setMeetingId(res.id);
    } catch (err: any) {
      alert(`Could not initialize live meeting: ${err.message}`);
      setIsMeetingActive(false);
    }
  };

  // Append a live segment
  const handleAddSegment = async (speaker: string, text: string) => {
    if (!text.trim()) return;

    const start_ms = elapsedSeconds * 1000;
    const end_ms = start_ms + Math.max(text.length * 80, 4000);
    const newSeg: LiveSegment = { speaker_name: speaker, start_ms, end_ms, text };

    setSegments((prev) => [...prev, newSeg]);

    if (meetingId) {
      try {
        await api.appendLiveChunk(meetingId, newSeg);
      } catch (err) {
        console.error('Failed to append live chunk:', err);
      }
    }
  };

  // Simulate Section 20 Dialogue
  const handleSimulateScript = async () => {
    if (!isMeetingActive) {
      await handleStartMeeting();
    }
    setIsSimulatingScript(true);

    for (let i = 0; i < SAMPLE_SCRIPT.length; i++) {
      const item = SAMPLE_SCRIPT[i];
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setSegments((prev) => [...prev, item]);
      if (meetingId) {
        try {
          await api.appendLiveChunk(meetingId, item);
        } catch (e) {
          console.error(e);
        }
      }
    }
    setIsSimulatingScript(false);
  };

  // Conclude Meeting and Trigger Reasoning Pipeline
  const handleEndMeeting = async () => {
    if (!meetingId) {
      // Fallback: ingest full segments array
      setIsProcessing(true);
      try {
        const res = await api.createMeeting(
          {
            title: meetingTitle,
            provider: 'live_stream',
            segments: segments.map((s, idx) => ({
              id: `seg_${String(idx + 1).padStart(3, '0')}`,
              speaker_name: s.speaker_name,
              start_ms: s.start_ms,
              end_ms: s.end_ms,
              text: s.text
            })),
            project_key: 'PAY'
          },
          true
        );
        router.push(`/meetings/${res.id}`);
      } catch (err: any) {
        alert(`Pipeline processing failed: ${err.message}`);
      } finally {
        setIsProcessing(false);
      }
      return;
    }

    setIsProcessing(true);
    try {
      await api.processMeeting(meetingId, 'PAY');
      router.push(`/meetings/${meetingId}`);
    } catch (err: any) {
      alert(`Pipeline error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="content-wrapper" style={{ maxWidth: '1200px' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.6) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="badge badge-emerald">Primary Workflow</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Target Project: <strong>PAY (Payments &amp; Checkout)</strong>
              </span>
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
              Live Engineering Meeting Room
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              OCRA records live conversational segments $\rightarrow$ on conclusion, extracts evidence-backed decisions $\rightarrow$ executes Jira changes.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {!isMeetingActive ? (
              <button
                onClick={handleStartMeeting}
                className="btn btn-primary"
                style={{ padding: '10px 20px', fontSize: '0.95rem' }}
              >
                <Play size={18} />
                Start Meeting
              </button>
            ) : (
              <button
                onClick={handleEndMeeting}
                disabled={isProcessing}
                className="btn btn-danger"
                style={{ padding: '10px 20px', fontSize: '0.95rem' }}
              >
                <Square size={16} />
                {isProcessing ? 'Processing Execution Plan...' : 'End Meeting & Execute Jira Changes'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Grid: Room Status + Live Transcript Stream */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
        {/* Left Controller Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Status HUD */}
          <div className="glass-panel">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                ROOM STATUS
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  display: 'inline-block',
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: isMeetingActive ? '#10b981' : '#64748b',
                  boxShadow: isMeetingActive ? '0 0 10px #10b981' : 'none'
                }} />
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isMeetingActive ? '#10b981' : 'var(--text-muted)' }}>
                  {isMeetingActive ? 'RECORDING LIVE' : 'STANDBY'}
                </span>
              </div>
            </div>

            <div style={{
              background: 'rgba(10, 15, 30, 0.6)',
              padding: '16px',
              borderRadius: '8px',
              textAlign: 'center',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Session Duration
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#38bdf8', marginTop: '4px' }}>
                {formatTimer(elapsedSeconds)}
              </div>
            </div>

            {/* Quick Demo Script Trigger */}
            <button
              onClick={handleSimulateScript}
              disabled={isSimulatingScript || isProcessing}
              className="btn btn-secondary"
              style={{ width: '100%', justifyContent: 'center', padding: '10px' }}
            >
              <Zap size={16} color="#fbbf24" />
              {isSimulatingScript ? 'Simulating Dialogue...' : 'Simulate Section 20 Dialogue'}
            </button>
          </div>

          {/* Speaker Controls */}
          <div className="glass-panel">
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '12px' }}>
              Active Speaker
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
              {['Rahul', 'Priya', 'Alex', 'Sarah'].map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => setCurrentSpeaker(name)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: currentSpeaker === name ? 'rgba(99, 102, 241, 0.25)' : 'rgba(30, 41, 59, 0.5)',
                    border: currentSpeaker === name ? '1px solid #6366f1' : '1px solid var(--border-subtle)',
                    color: currentSpeaker === name ? '#ffffff' : 'var(--text-secondary)'
                  }}
                >
                  {name}
                </button>
              ))}
            </div>

            {/* Custom speech input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAddSegment(currentSpeaker, customUtterance);
                setCustomUtterance('');
              }}
            >
              <input
                type="text"
                placeholder={`Type what ${currentSpeaker} said...`}
                value={customUtterance}
                onChange={(e) => setCustomUtterance(e.target.value)}
                disabled={!isMeetingActive}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid var(--border-subtle)',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  marginBottom: '8px'
                }}
              />
              <button
                type="submit"
                disabled={!isMeetingActive || !customUtterance.trim()}
                className="btn btn-secondary"
                style={{ width: '100%', justifyContent: 'center' }}
              >
                <Send size={14} /> Add Utterance
              </button>
            </form>
          </div>
        </div>

        {/* Right Pane: Live Speech Bubbles Stream */}
        <div className="glass-panel" style={{ height: '620px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={18} color="#10b981" />
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
                Live Meeting Audio Stream &amp; Transcript
              </h3>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {segments.length} segments captured
            </span>
          </div>

          {/* Transcript Scroll Area */}
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              paddingRight: '6px'
            }}
          >
            {segments.length === 0 ? (
              <div style={{
                margin: 'auto',
                textAlign: 'center',
                color: 'var(--text-muted)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px'
              }}>
                <Bot size={48} color="var(--border-accent)" />
                <p style={{ fontSize: '0.9rem' }}>
                  {isMeetingActive
                    ? 'Listening to live audio stream... Speak or click "Simulate Section 20 Dialogue".'
                    : 'Click "Start Meeting" to initiate recording.'}
                </p>
              </div>
            ) : (
              segments.map((seg, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '14px',
                    borderRadius: '10px',
                    background: 'rgba(15, 23, 42, 0.7)',
                    border: '1px solid var(--border-subtle)',
                    animation: 'fadeIn 0.3s ease-in-out'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        background: 'rgba(56, 189, 248, 0.2)',
                        border: '1px solid #38bdf8',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: '#38bdf8'
                      }}>
                        {seg.speaker_name[0]}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#ffffff' }}>
                        {seg.speaker_name}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {Math.floor(seg.start_ms / 1000)}s - {Math.floor(seg.end_ms / 1000)}s
                    </div>
                  </div>

                  <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                    {seg.text}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Bottom Action bar */}
          {isMeetingActive && segments.length > 0 && (
            <div style={{
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '14px',
              marginTop: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Ready to execute changes?
              </span>
              <button
                onClick={handleEndMeeting}
                disabled={isProcessing}
                className="btn btn-primary"
              >
                <Sparkles size={16} />
                {isProcessing ? 'Processing Pipeline...' : 'End Meeting & Generate Plan'}
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
