/** Tiny app-wide signal: fire after any mutation so lists and the auto-rate chip refetch. */
const EVT = "finpulse:data-changed";

export const emitDataChanged = () => window.dispatchEvent(new Event(EVT));

export function onDataChanged(cb: () => void): () => void {
  window.addEventListener(EVT, cb);
  return () => window.removeEventListener(EVT, cb);
}
