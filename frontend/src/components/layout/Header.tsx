'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Zap, ShieldCheck, RefreshCw, Layers } from 'lucide-react';

export const Header: React.FC = () => {
  const router = useRouter();
  const [loadingDemo, setLoadingDemo] = useState(false);

  const handleRunE2EDemo = async () => {
    try {
      setLoadingDemo(true);
      const meeting = await api.seedE2EDemo();
      router.push(`/meetings/${meeting.id}`);
    } catch (err: any) {
      alert(`Demo trigger failed: ${err.message}`);
    } finally {
      setLoadingDemo(false);
    }
  };

  const handleRunInjectionDemo = async () => {
    try {
      setLoadingDemo(true);
      const meeting = await api.seedInjectionDemo();
      router.push(`/meetings/${meeting.id}`);
    } catch (err: any) {
      alert(`Injection test failed: ${err.message}`);
    } finally {
      setLoadingDemo(false);
    }
  };

  return (
    <header className="top-header">
      {/* Title & Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '0.8rem',
            padding: '4px 10px',
            borderRadius: '6px',
            background: 'rgba(56, 189, 248, 0.1)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            fontWeight: 700
          }}>
            PROJECT: PAY
          </span>
          <span style={{
            fontSize: '0.8rem',
            padding: '4px 10px',
            borderRadius: '6px',
            background: 'rgba(16, 185, 129, 0.1)',
            color: '#10b981',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            fontWeight: 600
          }}>
            ● Auto-Execute ON
          </span>
        </div>
      </div>

      {/* Demo Action Shortcuts */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button
          onClick={handleRunE2EDemo}
          disabled={loadingDemo}
          className="btn btn-primary"
          style={{ padding: '7px 14px', fontSize: '0.82rem' }}
          title="Seed and process the Rahul/Priya/Password-Reset scenario from Section 20 & 25"
        >
          <Zap size={15} />
          {loadingDemo ? 'Running...' : 'Run E2E Demo Meeting'}
        </button>

        <button
          onClick={handleRunInjectionDemo}
          disabled={loadingDemo}
          className="btn btn-secondary"
          style={{ padding: '7px 14px', fontSize: '0.82rem' }}
          title="Test resistance against malicious instructions in meeting transcripts"
        >
          <ShieldCheck size={15} color="#38bdf8" />
          Test Injection Defense
        </button>
      </div>
    </header>
  );
};
