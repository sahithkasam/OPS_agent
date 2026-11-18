import { useCallback, useEffect, useRef, useState } from 'react';

const MIN_PENDING_MS = 350;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

/**
 * Tracks one in-flight async action for a group of buttons.
 *
 *   const { busy, error, run } = useBusy();
 *   <button disabled={!!busy} className={busy === 'approve' ? 'is-pending' : ''}
 *           onClick={() => run('approve', () => api.approve(id))}>
 *
 * While an action runs, every button in the group is disabled (no double
 * submits) and the clicked one shows the pending style. The pending state is
 * held for at least MIN_PENDING_MS so the feedback is visible even when the
 * API answers instantly.
 */
export function useBusy() {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const busyRef = useRef(null);
  const mounted = useRef(true);

  useEffect(() => () => { mounted.current = false; }, []);

  const run = useCallback(async (key, fn) => {
    if (busyRef.current) return undefined;
    busyRef.current = key;
    setBusy(key);
    setError(null);
    const started = performance.now();
    try {
      const result = await fn();
      const left = MIN_PENDING_MS - (performance.now() - started);
      if (left > 0) await sleep(left);
      return result;
    } catch (e) {
      if (mounted.current) setError(e?.message || String(e));
      return undefined;
    } finally {
      busyRef.current = null;
      if (mounted.current) setBusy(null);
    }
  }, []);

  return { busy, error, run, clearError: () => setError(null) };
}
