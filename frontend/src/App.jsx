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

  // The free-tier backend sleeps when idle and can take a while to wake, and
  // the knowledge base finishes loading a moment after the server is up.
  // Retry until both answer instead of leaving an empty dashboard.
  // The timer depends only on the phase, not on `state`: live state arrives
  // every second and would otherwise restart the timer before it ever fired.
  const serverDown = !state;
  const kbLoading = !serverDown && !kb;
  const kbFailed = kbLoading && !!kbError && !kbError.includes('(503)');
  const [waitedSec, setWaitedSec] = useState(0);
  const phase = serverDown ? 'server' : kbLoading ? 'kb' : null;
  useEffect(() => {
    if (!phase) return;
    const started = Date.now();
    setWaitedSec(0);
    const timer = setInterval(() => {
      setWaitedSec(Math.round((Date.now() - started) / 1000));
      if (phase === 'server') refresh();
      refreshKb();
    }, 4000);
    return () => clearInterval(timer);
  }, [phase, refresh, refreshKb]);

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
      {serverDown && (
        <div className="wake-banner" role="status">
          <span className="wake-dot" aria-hidden="true" />
          Waking up the backend server - the free hosting tier sleeps when idle and can take a minute or two to start.
          {waitedSec > 0 && <span className="wake-time"> Waiting {waitedSec}s, retrying automatically.</span>}
        </div>
      )}
      {kbLoading && !kbFailed && (
        <div className="wake-banner soft" role="status">
          <span className="wake-dot" aria-hidden="true" />
          Server is up. Loading the knowledge base of past incidents - the dashboard already works,
          incident analysis starts as soon as it's ready.
        </div>
      )}
      {kbFailed && (
        <div className="wake-banner error" role="alert">
          Knowledge base unavailable: {kbError} - retrying automatically.
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
