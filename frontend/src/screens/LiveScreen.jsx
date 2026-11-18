import React, { useState } from 'react';
import { api } from '../api.js';
import { severityTone } from '../agents.js';
import { INCIDENT_TYPES, typeLabel } from '../incidentTypes.js';
import { useBusy } from '../useBusy.js';
import { MiniPipeline } from '../components/MiniPipeline.jsx';
import { Sparkline } from '../components/Sparkline.jsx';
import { PlaybookModal, extractPlaybookSteps } from '../components/PlaybookModal.jsx';

// Signal window. The engine ticks every 2 s while running, so 30/90/180
// ticks ≈ 1/3/6 minutes (the backend keeps the last 180 ticks).
const WINDOWS = [
  { ticks: 30, label: '1m' },
  { ticks: 90, label: '3m' },
  { ticks: 180, label: '6m' },
];
const SEV_RANK = { P1: 0, P2: 1, P3: 2 };

export function LiveScreen({ state, refresh, kbCounts = {}, selectedId, onSelect }) {
  const incidents = [...(state?.incidents ?? [])].sort((a, b) =>
    (SEV_RANK[a.analysis?.severity] ?? 1) - (SEV_RANK[b.analysis?.severity] ?? 1)
    || a.start_tick - b.start_tick);
  const selected = incidents.find(i => i.id === selectedId) || incidents[0];
  const [playbook, setPlaybook] = useState(null); // { incident, kind, steps }
  const [windowTicks, setWindowTicks] = useState(WINDOWS[0].ticks);
  const inject = useBusy();
  const decide = useBusy();

  const runAction = (kind, incident) => decide.run(kind, async () => {
    const beforeLogs = state?.logs || [];
    const after = kind === 'approve'
      ? await api.approve(incident.id)
      : await api.deny(incident.id);
    const steps = extractPlaybookSteps(beforeLogs, after?.logs, kind);
    setPlaybook({ incident, kind, steps });
    await refresh();
  });

  const history = (state?.metrics_history ?? []).filter(Boolean).slice(-windowTicks);
  const cpuSeries = history.map(m => m?.cpu_percent ?? 0);
  const memSeries = history.map(m => m?.memory_percent ?? 0);
  const latSeries = history.map(m => m?.latency_seconds ?? 0);

  return (
    <>
    <div className="page" style={{ display: 'grid', gridTemplateColumns: '300px 1fr 320px', gap: 18, maxWidth: 1600 }}>
      {/* Queue */}
      <div className="col">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Open · {incidents.length}</div>
            <div className="card-sub mono-xs">sorted by severity</div>
          </div>
          {incidents.length === 0 && (
            <div className="muted" style={{ fontSize: 13, padding: '12px 0' }}>No active incidents.</div>
          )}
          <div className="col" style={{ gap: 8 }}>
            {incidents.map(inc => {
              const sev = inc.analysis?.severity || inc.severity_hint || 'P2';
              const active = inc.id === selected?.id;
              return (
                <button
                  key={inc.id}
                  onClick={() => onSelect(inc.id)}
                  className={`card card-btn ${active ? 'selected' : ''}`}
                  aria-pressed={active}
                  style={{ padding: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono-xs muted">{inc.id}</span>
                    <span className={`chip ${severityTone(sev)}`}>{sev}</span>
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, marginTop: 4 }}>
                    {typeLabel(inc.type)}
                  </div>
                  <div className="mono-xs muted" style={{ marginTop: 2 }}>
                    started tick {inc.start_tick} · {inc.state.toLowerCase()}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Inject incident</div>
          <div className="card-sub" style={{ marginBottom: 10 }}>
            Each type is a category of real postmortems (count shown)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {INCIDENT_TYPES.map(t => (
              <button
                key={t.id}
                className={`btn sm ${inject.busy === t.id ? 'is-pending' : ''}`}
                disabled={!!inject.busy}
                title={`${kbCounts[t.id] ?? 0} real postmortems in this category`}
                onClick={() => inject.run(t.id, async () => { await api.inject(t.id); await refresh(); })}
              >
                {t.label}
                <span className="count">{kbCounts[t.id] ?? '·'}</span>
              </button>
            ))}
          </div>
          {inject.error && <div className="form-error">{inject.error}</div>}
        </div>
      </div>

      {/* Focus */}
      <div className="col">
        {selected ? (
          <FocusPanel incident={selected} runAction={runAction} busy={decide.busy} error={decide.error} />
        ) : (
          <div className="empty">Select or inject an incident to view details.</div>
        )}

        <div className="card">
          <div className="card-head">
            <div className="card-title">Live signals</div>
            <div className="toggle" role="group" aria-label="Signal window">
              {WINDOWS.map(w => (
                <button
                  key={w.ticks}
                  className={windowTicks === w.ticks ? 'on' : ''}
                  aria-pressed={windowTicks === w.ticks}
                  title={`Last ${w.ticks} ticks (≈${w.label} while running)`}
                  onClick={() => setWindowTicks(w.ticks)}
                >{w.label}</button>
              ))}
            </div>
          </div>
          <div className="grid-3">
            <SignalCell label="CPU %" series={cpuSeries} value={state?.metrics?.cpu_percent} />
            <SignalCell label="Memory %" series={memSeries} value={state?.metrics?.memory_percent} />
            <SignalCell label="Latency (s)" series={latSeries} value={state?.metrics?.latency_seconds} suffix="" digits={2} />
          </div>
        </div>
      </div>

      {/* Activity */}
      <div className="col">
        <div className="card">
          <div className="card-title" style={{ marginBottom: 8 }}>Agent chatter</div>
          <ConversationList conversation={selected?.analysis?.agent_conversation} />
        </div>

        <div className="card">
          <div className="card-title" style={{ marginBottom: 8 }}>System log</div>
          <div style={{ maxHeight: 220, overflow: 'auto' }}>
            {(state?.logs ?? []).slice(-25).map((l, i) => (
              <div key={i} className="logline"><span>{l}</span></div>
            ))}
          </div>
        </div>
      </div>
    </div>
    {playbook && (
      <PlaybookModal
        incident={playbook.incident}
        kind={playbook.kind}
        steps={playbook.steps}
        onClose={() => setPlaybook(null)}
      />
    )}
    </>
  );
}

function FocusPanel({ incident, runAction, busy, error }) {
  const a = incident.analysis;
  const sev = a?.severity || incident.severity_hint || 'P2';
  const stages = a?.workflow_stages || {};
  const totalMs = a?.pipeline_duration_ms || 0;
  const top = a?.top_recommendation;
  const needsApproval = a?.needs_approval;
  const match = a?.hypotheses?.[0];
  const blocked = a?.remediation_plan?.safety_status === 'BLOCKED';

  return (
    <div className="card elevated">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4, flexWrap: 'wrap' }}>
        <span className="mono-xs muted">{incident.id}</span>
        <span className={`chip ${severityTone(sev)}`}>{sev}</span>
        {!a && <span className="chip"><span className="dot amber pulse"></span>agents working</span>}
        {a && needsApproval && <span className="chip amber">awaiting approval</span>}
        {a && !needsApproval && <span className="chip">{blocked ? 'blocked by policy' : 'no approval required'}</span>}
        {incident.jira_ticket_key && <span className="chip blue">{incident.jira_ticket_key}</span>}
      </div>
      <h2 className="serif" style={{ margin: '4px 0 14px', fontSize: 24, fontWeight: 600, letterSpacing: '-0.01em' }}>
        {typeLabel(incident.type)}
      </h2>

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="label">Agent pipeline</div>
          <span className="mono-xs muted">{totalMs ? `${totalMs.toFixed(0)}ms total` : 'pending'}</span>
        </div>
        <MiniPipeline stages={stages} />
      </div>

      <div className="grid-2">
        <div style={{ minWidth: 0 }}>
          <div className="label" style={{ marginBottom: 6 }}>Summary</div>
          <div style={{ fontSize: 13.5, lineHeight: 1.55 }}>{a?.summary || 'Awaiting diagnostics…'}</div>
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="label" style={{ marginBottom: 6 }}>Closest past incident</div>
          {match ? (
            <>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>{match.root_cause}</div>
              {match.company && (
                <div className="mono-xs muted" style={{ marginTop: 4 }}>
                  {match.historical_id} · {match.company}
                  {match.source_url && <> · <a href={match.source_url} target="_blank" rel="noreferrer">postmortem ↗</a></>}
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                <div className="bar accent" style={{ flex: 1 }}>
                  <span style={{ width: `${Math.round((match.confidence || 0) * 100)}%` }}></span>
                </div>
                <span className="mono-xs" title="cosine similarity">{Math.round((match.confidence || 0) * 100)}% sim</span>
              </div>
            </>
          ) : <div className="muted">No match yet.</div>}
        </div>
      </div>

      {top && (
        <div style={{ marginTop: 16, padding: 12, background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)' }}>
          <div className="label" style={{ marginBottom: 4 }}>Recommended action</div>
          <code className="mono" style={{ fontSize: 13 }}>{top}</code>
        </div>
      )}

      {a && (
        <div style={{ marginTop: 14 }}>
          {!needsApproval && (
            <div className="mono-xs muted" style={{ marginBottom: 8 }}>
              Policy did not require approval — resolve or escalate it manually.
            </div>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`btn accent ${busy === 'approve' ? 'is-pending' : ''}`}
              disabled={!!busy}
              onClick={() => runAction('approve', incident)}
            >{busy === 'approve' ? 'Executing…' : needsApproval ? 'Approve' : 'Execute & resolve'}</button>
            <button
              className={`btn danger ${busy === 'deny' ? 'is-pending' : ''}`}
              disabled={!!busy}
              onClick={() => runAction('deny', incident)}
            >{busy === 'deny' ? 'Escalating…' : needsApproval ? 'Deny' : 'Escalate'}</button>
          </div>
          {error && <div className="form-error">{error}</div>}
        </div>
      )}
    </div>
  );
}

function SignalCell({ label, series, value, suffix = '%', digits = 1 }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div className="label">{label}</div>
        <div className="serif" style={{ fontSize: 18, fontWeight: 600 }}>
          {value != null ? `${Number(value).toFixed(digits)}${suffix}` : '—'}
        </div>
      </div>
      <Sparkline values={series} height={48} />
    </div>
  );
}

function ConversationList({ conversation }) {
  if (!conversation?.length) {
    return <div className="muted" style={{ fontSize: 13 }}>No messages yet.</div>;
  }
  const icons = {
    orchestrator: '🎯', triage: '🔍', diagnostics: '🔬',
    rca: '🧠', remediation: '🛠️', comms: '📡',
  };
  return (
    <div style={{ maxHeight: 360, overflow: 'auto' }}>
      {conversation.map((m, i) => (
        <div key={i} style={{ paddingLeft: 10, borderLeft: '2px solid var(--line)', marginBottom: 10 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600 }}>
            {icons[m.sender] || '•'} {m.sender} → {m.recipient}
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{m.payload_summary || m.type}</div>
          <div className="mono-xs muted">{m.duration_ms?.toFixed(0)}ms</div>
        </div>
      ))}
    </div>
  );
}
