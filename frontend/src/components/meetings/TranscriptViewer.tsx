'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Segment } from '@/lib/types';
import { Search, User, Clock, MessageSquareQuote } from 'lucide-react';

interface Props {
  segments: Segment[];
  highlightedSegmentId?: string | null;
  onSelectSegment?: (segment: Segment) => void;
}

export const TranscriptViewer: React.FC<Props> = ({
  segments,
  highlightedSegmentId,
  onSelectSegment
}) => {
  const [search, setSearch] = useState('');
  const segmentRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  // Auto-scroll to highlighted segment when changed
  useEffect(() => {
    if (highlightedSegmentId && segmentRefs.current[highlightedSegmentId]) {
      segmentRefs.current[highlightedSegmentId]?.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }, [highlightedSegmentId]);

  const filtered = segments.filter(
    (s) =>
      s.text.toLowerCase().includes(search.toLowerCase()) ||
      s.speaker_name.toLowerCase().includes(search.toLowerCase())
  );

  const formatTime = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getSpeakerColor = (name: string) => {
    const colors = ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fbbf24'];
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
    return colors[hash % colors.length];
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header & Search */}
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquareQuote size={20} color="#38bdf8" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
            Meeting Transcript ({segments.length} segments)
          </h3>
        </div>

        <div style={{ position: 'relative', width: '220px' }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            placeholder="Search transcript..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 10px 6px 30px',
              fontSize: '0.8rem',
              borderRadius: '6px',
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid var(--border-subtle)',
              color: '#ffffff',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Segments List */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '4px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: '0.85rem' }}>
            No transcript segments found.
          </div>
        ) : (
          filtered.map((seg) => {
            const isHighlighted = seg.id === highlightedSegmentId;
            const speakerColor = getSpeakerColor(seg.speaker_name);

            return (
              <div
                key={seg.id}
                ref={(el) => {
                  segmentRefs.current[seg.id] = el;
                }}
                onClick={() => onSelectSegment && onSelectSegment(seg)}
                className={isHighlighted ? 'evidence-highlighted' : ''}
                style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: isHighlighted ? 'rgba(245, 158, 11, 0.15)' : 'rgba(15, 23, 42, 0.6)',
                  border: isHighlighted ? '1px solid #f59e0b' : '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {/* Speaker Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: `${speakerColor}22`,
                      border: `1px solid ${speakerColor}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: speakerColor
                    }}>
                      {seg.speaker_name[0] || 'U'}
                    </div>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
                      {seg.speaker_name}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    <Clock size={12} />
                    <span>{formatTime(seg.start_ms)} - {formatTime(seg.end_ms)}</span>
                  </div>
                </div>

                {/* Spoken Text */}
                <p style={{ fontSize: '0.875rem', lineHeight: '1.5', color: isHighlighted ? '#ffffff' : 'var(--text-secondary)' }}>
                  {seg.text}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
