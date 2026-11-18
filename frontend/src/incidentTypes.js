// Incident types the simulator can inject. Each one is also a category in the
// knowledge base (real public postmortems), so RCA retrieves same-kind outages.
// Keep in sync with src/simulation/incident.py::IncidentType.
export const INCIDENT_TYPES = [
  { id: 'bad_deploy',      label: 'Bad deploy / config' },
  { id: 'service_down',    label: 'Service outage' },
  { id: 'database_lock',   label: 'Database' },
  { id: 'network_latency', label: 'Network / latency' },
  { id: 'high_cpu',        label: 'CPU overload' },
  { id: 'process_crash',   label: 'Process crash' },
  { id: 'disk_usage_high', label: 'Disk full' },
  { id: 'dns_failure',     label: 'DNS failure' },
  { id: 'memory_leak',     label: 'Memory leak' },
  { id: 'ssl_expiry',      label: 'Certificate expiry' },
];

const LABELS = Object.fromEntries(INCIDENT_TYPES.map(t => [t.id, t.label]));

export function typeLabel(id) {
  return LABELS[id] || String(id || '').replaceAll('_', ' ');
}
