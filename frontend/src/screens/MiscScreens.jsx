import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../api.js';
import { severityTone } from '../agents.js';
import { INCIDENT_TYPES, typeLabel } from '../incidentTypes.js';
import { useBusy } from '../useBusy.js';
import { Sparkline } from '../components/Sparkline.jsx';
import { PlaybookModal } from '../components/PlaybookModal.jsx';

// ---------- Knowledge ----------
export function KnowledgeScreen({ kb, error, onRetry, state }) {
  const items = kb?.items ?? [];
  const counts = kb?.categories ?? {};
  const index = kb?.index;
  const [selId, setSelId] = useState(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter(i => {
      if (category !== 'all' && i.category !== category) return false;
      if (!q) return true;
      return [i.id, i.company, i.summary, i.description, i.root_cause]
        .some(v => String(v || '').toLowerCase().includes(q));
    });
  }, [items, query, category]);

  const sel = filtered.find(i => i.id === selId) || filtered[0] || null;

  // Which active incidents retrieved this postmortem (real data from RCA).
  const retrievedBy = useMemo(() => {
    if (!sel) return [];
    const out = [];
    for (const inc of state?.incidents ?? []) {
      (inc.analysis?.hypotheses ?? []).forEach((h, rank) => {
        if (h.historical_id === sel.id) out.push({ inc, rank, conf: h.confidence });
      });
    }
    return out;
  }, [sel, state]);

  if (!kb) {
    return (
      <div className="page">
        <h1>Knowledge base</h1>
        {error ? (
          <div className="empty">
            <div style={{ marginBottom: 10 }}>Couldn't load the knowledge base: {error}</div>
            <button className="btn sm" onClick={onRetry}>Retry</button>
          </div>
        ) : <div className="muted">Loading knowledge base…</div>}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr 300px', minHeight: 'calc(100vh - 60px)' }}>
      {/* List */}
      <div style={{ borderRight: '1px solid var(--line)', padding: 16, background: 'var(--bg)', overflow: 'auto', maxHeight: 'calc(100vh - 60px)' }}>
        <h2 className="serif" style={{ fontSize: 20, margin: 0 }}>Knowledge base</h2>
        <div className="muted mono-xs" style={{ marginBottom: 10 }}>
          {items.length} real postmortems · {filtered.length} shown
        </div>
        <input
          type="search"
          placeholder="Search company, cause, text…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ width: '100%', marginBottom: 10 }}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 12 }}>
          <button
            className={`chip chip-btn ${category === 'all' ? 'solid' : ''}`}
            aria-pressed={category === 'all'}
            onClick={() => setCategory('all')}
          >All <span className="count">{items.length}</span></button>
          {INCIDENT_TYPES.map(t => (
            <button
              key={t.id}
              className={`chip chip-btn ${category === t.id ? 'solid' : ''}`}
              aria-pressed={category === t.id}
              onClick={() => setCategory(t.id)}
            >{t.label} <span className="count">{counts[t.id] ?? 0}</span></button>
          ))}
        </div>
        <div className="col" style={{ gap: 6 }}>
          {filtered.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No matches.</div>}
          {filtered.map(i => (
            <button
              key={i.id}
              className={`card card-btn ${sel?.id === i.id ? 'selected' : ''}`}
              aria-pressed={sel?.id === i.id}
              onClick={() => setSelId(i.id)}
              style={{ padding: 10 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                <span className="mono-xs muted">{i.id} · {i.company}</span>
                <span className={`chip ${severityTone(i.severity)}`} style={{ padding: '0 6px', fontSize: 10 }}>{i.severity}</span>
              </div>
              <div style={{ fontSize: 13, marginTop: 2 }}>{i.summary}</div>
              <div className="mono-xs muted" style={{ marginTop: 3 }}>{typeLabel(i.category)}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Detail */}
      <div style={{ padding: 28, overflow: 'auto', maxHeight: 'calc(100vh - 60px)' }}>
        {!sel ? <div className="empty">Nothing matches the current filter.</div> : (
          <>
            <div className="mono-xs muted">{sel.id} · {sel.section}</div>
            <h1 className="serif" style={{ fontSize: 26, margin: '4px 0 10px', fontWeight: 600, letterSpacing: '-0.01em' }}>
              {sel.company}: {sel.summary}
            </h1>
            <div style={{ display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
              <span className={`chip ${severityTone(sel.severity)}`}>{sel.severity}</span>
              <span className="chip violet">{typeLabel(sel.category)}</span>
              {sel.duration && <span className="chip">~{sel.duration}</span>}
              <span className="chip">{sel.source === 'live' ? 'from this session' : 'public postmortem'}</span>
              {sel.source_url && (
                <a className="btn sm" href={sel.source_url} target="_blank" rel="noreferrer">Read original ↗</a>
              )}
            </div>
            <div className="grid-2">
              <div className="card" style={{ gridColumn: 'span 2' }}>
                <div className="card-title">What happened</div>
                <div style={{ fontSize: 13.5, lineHeight: 1.65, marginTop: 8, color: 'var(--ink-2)' }}>
                  {sel.description || '—'}
                </div>
              </div>
              <div className="card">
                <div className="card-title">Symptoms</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {(Array.isArray(sel.symptoms) ? sel.symptoms : []).map((s, k) => (
                    <span key={k} className="chip amber">{s}</span>
                  ))}
                  {!(sel.symptoms?.length) && <span className="muted">—</span>}
                </div>
              </div>
              <div className="card">
                <div className="card-title">Recommended action</div>
                <code className="mono" style={{ display: 'block', fontSize: 13, marginTop: 8 }}>
                  {sel.recommended_action || '—'}
                </code>
              </div>
              <div className="card" style={{ gridColumn: 'span 2' }}>
                <div className="card-title">Root cause</div>
                <div style={{ fontSize: 13.5, lineHeight: 1.65, marginTop: 8 }}>{sel.root_cause || '—'}</div>
              </div>
              <div className="card" style={{ gridColumn: 'span 2' }}>
                <div className="card-title">Resolution</div>
                <div style={{ fontSize: 13.5, lineHeight: 1.65, marginTop: 8 }}>
                  {sel.resolution || (
                    <span className="muted">Not described in the public summary — see the original postmortem.</span>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Side */}
      <div style={{ borderLeft: '1px solid var(--line)', padding: 16, background: 'var(--bg)' }}>
        <div className="card-title">Retrieved by live incidents</div>
        {retrievedBy.length === 0 ? (
          <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
            Not retrieved by any active incident. Inject a{' '}
            <strong>{sel ? typeLabel(sel.category) : ''}</strong> incident to see RCA pick from this category.
          </div>
        ) : retrievedBy.map(({ inc, rank, conf }) => (
          <div key={inc.id + rank} className="card" style={{ marginTop: 8, padding: 10 }}>
            <div className="mono-xs muted">{inc.id} · match #{rank + 1}</div>
            <div style={{ fontSize: 13 }}>{typeLabel(inc.type)} · {Math.round((conf || 0) * 100)}% similarity</div>
          </div>
        ))}

        <div className="card-title" style={{ marginTop: 22 }}>Index</div>
        <div style={{ fontSize: 13, lineHeight: 1.8, marginTop: 6, color: 'var(--ink-2)' }}>
          <div>documents · <span className="mono">{index?.documents ?? '—'}</span></div>
          <div>embedding · <span className="mono">{index?.embedding_model} ({index?.dims}d)</span></div>
          <div>distance · <span className="mono">{index?.distance}</span></div>
          <div>collection · <span className="mono" style={{ wordBreak: 'break-all' }}>{index?.collection}</span></div>
        </div>
        <div className="card-title" style={{ marginTop: 22 }}>Source</div>
        <div style={{ fontSize: 12.5, lineHeight: 1.6, marginTop: 6, color: 'var(--ink-3)' }}>
          Real outage write-ups collected at{' '}
          <a href="https://github.com/danluu/post-mortems" target="_blank" rel="noreferrer">{index?.source}</a>,
          normalized by <span className="mono">scripts/build_kb_from_postmortems.py</span>.
          RCA searches only the incident's own category first.
        </div>
      </div>
    </div>
  );
}

// ---------- History (real data from /api/history) ----------
export function HistoryScreen({ onKbChange }) {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [replay, setReplay] = useState(null); // { incident, kind, steps }
  const [kbStatus, setKbStatus] = useState({}); // { [id]: 'pending' | 'ok' | 'err' }

  const refresh = async () => {
    try { setData(await api.history()); setLoadError(null); }
    catch (e) { setLoadError(e.message || String(e)); }
  };
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const items = data?.items ?? [];
  const kpis = data?.kpis ?? {};

  const onReplay = (inc) => {
    const steps = buildResolutionSteps(inc);
    const kind = inc.state === 'ESCALATED' ? 'deny' : 'approve';
    setReplay({ incident: inc, kind, steps });
  };

  const onAddToKB = async (inc) => {
    setKbStatus(s => ({ ...s, [inc.id]: 'pending' }));
    const started = performance.now();
    try {
      await api.kbIngest(inc.id);
      const left = 350 - (performance.now() - started);
      if (left > 0) await new Promise(r => setTimeout(r, left));
      setKbStatus(s => ({ ...s, [inc.id]: 'ok' }));
      onKbChange?.();
    } catch (e) {
      setKbStatus(s => ({ ...s, [inc.id]: 'err' }));
    }
  };

  return (
    <div className="page">
      <h1>History · post-mortems</h1>
      <div className="subtitle">
        {items.length > 0
          ? `Resolved incidents from this session (${items.length} so far).`
          : 'No resolved incidents yet — approve or deny one in Live to populate this view.'}
      </div>
      {loadError && <div className="form-error" style={{ marginBottom: 14 }}>Couldn't load history: {loadError}</div>}

      <div className="grid-4" style={{ marginBottom: 18 }}>
        <Kpi k="Incidents (total)" v={kpis.incidents ?? 0} />
        <Kpi k="Resolved" v={kpis.resolved ?? 0} />
        <Kpi k="Auto-resolved" v={kpis.auto_resolved ?? 0} />
        <Kpi k="Avg ticks to resolve" v={kpis.avg_ticks ?? '—'} />
      </div>

      {items.length > 0 && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-title" style={{ marginBottom: 8 }}>Resolution timeline</div>
          <ResolutionDots items={items} />
        </div>
      )}

      <h2 className="serif" style={{ fontSize: 20, marginTop: 18, marginBottom: 12 }}>Post-mortems</h2>
      {items.length === 0 && (
        <div className="empty">No post-mortems yet.</div>
      )}
      <div className="col">
        {items.map(p => {
          const sev = p.analysis?.severity || 'P2';
          const summary = p.analysis?.summary || '—';
          const root = p.analysis?.hypotheses?.[0]?.root_cause || '—';
          const ticks = p.history?.length ? (p.history[p.history.length - 1][0] - p.start_tick) : null;
          const escalated = p.state === 'ESCALATED';
          const kbS = kbStatus[p.id];
          return (
            <div key={p.id} className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span className={`chip ${severityTone(sev)}`}>{sev}</span>
                <span className="mono-xs muted">{p.id}</span>
                <span style={{ fontSize: 14, fontWeight: 600 }}>{typeLabel(p.type)}</span>
                {escalated && <span className="chip red">escalated</span>}
                {p.jira_ticket_key && <span className="chip blue">{p.jira_ticket_key}</span>}
                <span className="mono-xs muted" style={{ marginLeft: 'auto' }}>
                  resolved at tick {p.history?.[p.history.length - 1]?.[0] ?? '?'} · {ticks != null ? `${ticks} ticks` : '—'}
                </span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--ink-2)', marginTop: 8 }}>↳ {root}</div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 4 }}>{summary}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                <button className="btn sm" onClick={() => onReplay(p)}>Replay timeline</button>
                <button className="btn sm ghost" onClick={() => downloadPostmortem(p)}>Export .md</button>
                <button
                  className={`btn sm ${kbS === 'ok' ? 'accent' : 'ghost'} ${kbS === 'pending' ? 'is-pending' : ''}`}
                  onClick={() => onAddToKB(p)}
                  disabled={kbS === 'pending' || kbS === 'ok'}
                >
                  {kbS === 'pending' ? 'Adding…' : kbS === 'ok' ? '✓ Added to KB' : kbS === 'err' ? 'Retry add to KB' : 'Add to KB'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {replay && (
        <PlaybookModal
          incident={replay.incident}
          kind={replay.kind}
          steps={replay.steps}
          onClose={() => setReplay(null)}
        />
      )}
    </div>
  );
}

function Kpi({ k, v }) {
  return (
    <div className="card kpi">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
    </div>
  );
}

function ResolutionDots({ items }) {
  if (!items.length) return null;
  const ticks = items.map(i => i.history?.[i.history.length - 1]?.[0] || i.start_tick);
  const minT = Math.min(...ticks);
  const maxT = Math.max(...ticks);
  const span = Math.max(maxT - minT, 1);
  return (
    <svg viewBox="0 0 800 80" style={{ width: '100%' }}>
      <line x1="0" y1="50" x2="800" y2="50" stroke="var(--line-2)" strokeWidth="1.4" />
      {items.map((inc) => {
        const t = inc.history?.[inc.history.length - 1]?.[0] || inc.start_tick;
        const x = ((t - minT) / span) * 760 + 20;
        const tone = severityTone(inc.analysis?.severity || 'P2');
        const fill = tone === 'red' ? 'var(--red)' : tone === 'amber' ? 'var(--amber)' : 'var(--green)';
        return (
          <g key={inc.id}>
            <circle cx={x} cy="50" r="4" fill={fill} stroke="var(--ink)" strokeWidth="0.6">
              <title>{`${inc.id} · ${typeLabel(inc.type)} · tick ${t}`}</title>
            </circle>
          </g>
        );
      })}
      <text x="20" y="72" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-3)">tick {minT}</text>
      <text x="780" y="72" textAnchor="end" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-3)">tick {maxT}</text>
    </svg>
  );
}

function buildResolutionSteps(inc) {
  const a = inc.analysis || {};
  const out = [];
  out.push(`Detected ${typeLabel(inc.type)} at tick ${inc.start_tick}`);
  if (a.severity) out.push(`Triage classified as ${a.severity}`);
  const symptoms = (a.triage_report?.symptoms || []).filter(s => !String(s).startsWith('[AI Insight]')).slice(0, 3);
  if (symptoms.length) out.push(`Symptoms: ${symptoms.join(', ')}`);
  const h = a.hypotheses?.[0];
  if (h) {
    const conf = Math.round((h.confidence || 0) * 100);
    const src = h.company ? ` (closest match: ${h.company}, ${h.historical_id})` : '';
    out.push(`RCA top hypothesis (${conf}% similarity): ${h.root_cause}${src}`);
  }
  if (a.top_recommendation) out.push(`Recommended action: ${a.top_recommendation}`);
  if (inc.jira_ticket_key) out.push(`Jira ticket ${inc.jira_ticket_key} created`);
  out.push(inc.state === 'ESCALATED' ? 'User denied → escalated to L3' : 'User approved → executed playbook');
  out.push(`Final state: ${inc.state}`);
  return out;
}

function downloadPostmortem(inc) {
  const a = inc.analysis || {};
  const h = a.hypotheses || [];
  const lines = [
    `# Postmortem: ${typeLabel(inc.type)} (${inc.id})`,
    '',
    `- **Severity:** ${a.severity || '—'}`,
    `- **Final state:** ${inc.state}`,
    `- **Started at tick:** ${inc.start_tick}`,
    inc.jira_ticket_key ? `- **Jira:** ${inc.jira_ticket_key}` : null,
    '',
    '## Summary',
    a.summary || '—',
    '',
    '## Root cause',
    a.root_cause || h[0]?.root_cause || '—',
    '',
    '## Similar past incidents (RAG)',
    ...(h.length ? h.map((x, i) =>
      `${i + 1}. ${x.company ? `**${x.company}** (${x.historical_id}) — ` : ''}${x.root_cause} ` +
      `_(similarity ${Math.round((x.confidence || 0) * 100)}%)_${x.source_url ? ` [source](${x.source_url})` : ''}`) : ['—']),
    '',
    '## Timeline',
    ...buildResolutionSteps(inc).map(s => `- ${s}`),
    '',
  ].filter(l => l !== null);
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `postmortem-${inc.id}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Sim ----------
const SEVERITY_HINTS = [
  [null, 'Auto'],
  ['P1', 'P1'],
  ['P2', 'P2'],
  ['P3', 'P3'],
];

export function SimScreen({ state, refresh, kbCounts = {} }) {
  const [scenario, setScenario] = useState(INCIDENT_TYPES[0].id);
  const [severity, setSeverity] = useState(null);
  const engine = useBusy();
  const inject = useBusy();
  const history = (state?.metrics_history ?? []).filter(Boolean);
  const running = !!state?.auto_run;
  const scenarioLabel = typeLabel(scenario);

  return (
    <div className="page">
      <h1>Simulation control</h1>
      <div className="subtitle">Drive the synthetic engine and inject incidents.</div>
      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Engine</div>
            <span className={`chip ${running ? 'green' : 'amber'}`}>
              <span className={`dot ${running ? 'green pulse' : 'amber'}`}></span>{running ? 'running' : 'paused'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button
              className={`btn ${running ? 'selected' : 'accent'} ${engine.busy === 'run' ? 'is-pending' : ''}`}
              disabled={!!engine.busy || running}
              aria-pressed={running}
              onClick={() => engine.run('run', async () => { await api.setAuto(true); await refresh(); })}
            >▶ {running ? 'Running' : 'Run'}</button>
            <button
              className={`btn ${!running ? 'selected' : ''} ${engine.busy === 'pause' ? 'is-pending' : ''}`}
              disabled={!!engine.busy || !running}
              aria-pressed={!running}
              onClick={() => engine.run('pause', async () => { await api.setAuto(false); await refresh(); })}
            >⏸ {running ? 'Pause' : 'Paused'}</button>
            <button
              className={`btn ghost ${engine.busy === 'step' ? 'is-pending' : ''}`}
              disabled={!!engine.busy || running}
              title={running ? 'Pause the engine to step manually' : 'Advance one tick'}
              onClick={() => engine.run('step', async () => { await api.tick(); await refresh(); })}
            >⏭ Step</button>
          </div>
          {engine.error && <div className="form-error">{engine.error}</div>}
          <div className="grid-2" style={{ marginTop: 18 }}>
            <Stat k="tick" v={state?.tick ?? 0} />
            <Stat k="mode" v={state?.mode ?? '—'} />
            <Stat k="active incidents" v={state?.incidents?.length ?? 0} />
            <Stat k="LLM" v={state?.llm_active ? 'active' : 'mock'} />
          </div>
        </div>

        <div className="card">
          <div className="card-title">Inject incident</div>
          <div className="muted mono-xs">types match the knowledge-base categories · count = real postmortems</div>
          <div style={{ marginTop: 14 }}>
            <div className="label" style={{ marginBottom: 6 }}>Scenario</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {INCIDENT_TYPES.map(t => (
                <button
                  key={t.id}
                  className={`chip chip-btn ${scenario === t.id ? 'solid' : ''}`}
                  aria-pressed={scenario === t.id}
                  onClick={() => setScenario(t.id)}
                >{t.label} <span className="count">{kbCounts[t.id] ?? '·'}</span></button>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <div className="label" style={{ marginBottom: 6 }}>Severity hint</div>
            <div className="toggle" role="group" aria-label="Severity hint">
              {SEVERITY_HINTS.map(([val, label]) => (
                <button
                  key={label}
                  className={severity === val ? 'on' : ''}
                  aria-pressed={severity === val}
                  onClick={() => setSeverity(val)}
                >{label}</button>
              ))}
            </div>
            <div className="mono-xs muted" style={{ marginTop: 6 }}>
              {severity ? `Triage will treat this as at least ${severity}.` : 'Triage decides severity from metrics and logs.'}
            </div>
          </div>
          <button
            className={`btn accent ${inject.busy ? 'is-pending' : ''}`}
            disabled={!!inject.busy}
            style={{ marginTop: 18, width: '100%', justifyContent: 'center' }}
            onClick={() => inject.run('inject', async () => { await api.inject(scenario, severity); await refresh(); })}
          >{inject.busy ? 'Injecting…' : `⚡ Inject ${scenarioLabel}`}</button>
          {inject.error && <div className="form-error">{inject.error}</div>}
          {!running && !inject.error && (
            <div className="mono-xs muted" style={{ marginTop: 8 }}>
              Engine is paused: press Run or Step so the agents pick the incident up.
            </div>
          )}
        </div>

        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-title">Live metrics — synthetic stream</div>
          <div className="grid-4" style={{ marginTop: 12 }}>
            <SignalCell label="CPU %" series={history.map(m => m?.cpu_percent ?? 0)} value={state?.metrics?.cpu_percent} />
            <SignalCell label="Memory %" series={history.map(m => m?.memory_percent ?? 0)} value={state?.metrics?.memory_percent} />
            <SignalCell label="Latency (s)" series={history.map(m => m?.latency_seconds ?? 0)} value={state?.metrics?.latency_seconds} suffix="" digits={2} />
            <SignalCell label="Disk %" series={history.map(m => m?.disk_percent ?? 0)} value={state?.metrics?.disk_percent} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ k, v }) {
  return (
    <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 8 }}>
      <div className="label">{k}</div>
      <div className="serif" style={{ fontSize: 22, fontWeight: 600 }}>{v}</div>
    </div>
  );
}

function SignalCell({ label, series, value, suffix = '%', digits = 1 }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div className="label">{label}</div>
        <div className="serif" style={{ fontSize: 16, fontWeight: 600 }}>
          {value != null ? `${Number(value).toFixed(digits)}${suffix}` : '—'}
        </div>
      </div>
      <Sparkline values={series} height={48} />
    </div>
  );
}
