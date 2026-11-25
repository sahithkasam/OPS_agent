import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from './components/AppShell.jsx';
import { LiveScreen } from './screens/LiveScreen.jsx';
import { WorkflowScreen } from './screens/WorkflowScreen.jsx';
import { AgentsScreen } from './screens/AgentsScreen.jsx';
import { KnowledgeScreen, HistoryScreen, SimScreen } from './screens/MiscScreens.jsx';
import { api, subscribeEvents } from './api.js';

export default function App() {
  const [tab, setTab] = useState('live');
  const [state, setState] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [kb, setKb] = useState(null);       // { items, categories, index }
  const [kbError, setKbError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const s = await api.state();
      setState(s);
    } catch (e) {
      console.warn('state fetch failed', e);
    }
  }, []);

  const refreshKb = useCallback(async () => {
    try {
      setKb(await api.kb());
      setKbError(null);
    } catch (e) {
      setKbError(e.message || String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
    refreshKb();
    const stop = subscribeEvents((s) => setState(s));
    return stop;
  }, [refresh, refreshKb]);

  // The free-tier backend sleeps when idle and can take 1-2 minutes to wake.
  // Keep retrying until it answers instead of leaving an empty dashboard.
  const [waitedSec, setWaitedSec] = useState(0);
  const waking = !state || (!kb && !!kbError);
  useEffect(() => {
    if (!waking) return;
    const started = Date.now();
    const timer = setInterval(() => {
      setWaitedSec(Math.round((Date.now() - started) / 1000));
      if (!state) refresh();
      if (!kb) refreshKb();
    }, 5000);
    return () => clearInterval(timer);
  }, [waking, state, kb, refresh, refreshKb]);

  // Auto-select first incident if none picked, or if previous selection is gone.
  useEffect(() => {
    const ids = (state?.incidents || []).map(i => i.id);
    if (!ids.length) {
      if (selectedId) setSelectedId(null);
      return;
    }
    if (!selectedId || !ids.includes(selectedId)) {
      setSelectedId(ids[0]);
    }
  }, [state, selectedId]);

  const selected = state?.incidents?.find(i => i.id === selectedId) || null;
  const kbCounts = kb?.categories || {};

  return (
    <AppShell tab={tab} onTab={setTab} state={state}>
      {waking && (
        <div className="wake-banner" role="status">
          <span className="wake-dot" aria-hidden="true" />
          Waking up the backend server - the free hosting tier sleeps when idle and can take 1-2 minutes to start.
          {waitedSec > 0 && <span className="wake-time"> Waiting {waitedSec}s, retrying automatically.</span>}
        </div>
      )}
      {tab === 'live' && (
        <LiveScreen state={state} refresh={refresh} kbCounts={kbCounts}
          selectedId={selectedId} onSelect={setSelectedId} />
      )}
      {tab === 'workflow' && (
        <WorkflowScreen state={state} selected={selected}
          selectedId={selectedId} onSelect={setSelectedId} />
      )}
      {tab === 'agents' && (
        <AgentsScreen state={state} refresh={refresh} selected={selected}
          selectedId={selectedId} onSelect={setSelectedId} />
      )}
      {tab === 'knowledge' && (
        <KnowledgeScreen kb={kb} error={kbError} onRetry={refreshKb} state={state} />
      )}
      {tab === 'history' && <HistoryScreen onKbChange={refreshKb} />}
      {tab === 'sim' && <SimScreen state={state} refresh={refresh} kbCounts={kbCounts} />}
    </AppShell>
  );
}
