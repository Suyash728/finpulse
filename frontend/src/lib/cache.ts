"use client";

/**
 * Tiny stale-while-revalidate cache shared by all pages.
 * Switching tabs shows the last data instantly; a background refetch keeps it fresh.
 * Any write (emitDataChanged) marks everything stale and refetches what's on screen.
 */
import { useEffect, useState } from "react";
import { onDataChanged } from "@/lib/events";

type Entry = { data?: unknown; error?: string; ts: number; inflight?: Promise<unknown> };
const store = new Map<string, Entry>();
const subs = new Map<string, Set<() => void>>();
const FRESH_MS = 15_000;

function notify(key: string) {
  subs.get(key)?.forEach((fn) => fn());
}

export function fetchCached<T>(key: string, fetcher: () => Promise<T>, force = false): Promise<T> {
  const e = store.get(key) ?? { ts: 0 };
  if (e.inflight) return e.inflight as Promise<T>;
  if (!force && e.data !== undefined && Date.now() - e.ts < FRESH_MS) return Promise.resolve(e.data as T);
  const p = fetcher()
    .then((data) => { store.set(key, { data, ts: Date.now() }); notify(key); return data; })
    .catch((err: Error) => { store.set(key, { ...store.get(key), ts: 0, error: err.message, inflight: undefined }); notify(key); throw err; });
  store.set(key, { ...e, inflight: p });
  return p;
}

/** Warm the cache (e.g. on app load) without rendering anything. */
export const prefetch = <T,>(key: string, fetcher: () => Promise<T>) => { fetchCached(key, fetcher).catch(() => {}); };

let wired = false;
function wireInvalidation() {
  if (wired || typeof window === "undefined") return;
  wired = true;
  onDataChanged(() => {
    store.forEach((e) => { e.ts = 0; });
    subs.forEach((fns) => fns.forEach((fn) => fn()));
  });
}

export function useCached<T>(key: string | null, fetcher: () => Promise<T>) {
  const [, force] = useState(0);
  useEffect(() => {
    if (!key) return;
    wireInvalidation();
    const rerender = () => force((n) => n + 1);
    const revalidate = () => {
      rerender();
      fetchCached(key, fetcher).catch(() => {});
    };
    const set = subs.get(key) ?? new Set();
    set.add(revalidate);
    subs.set(key, set);
    fetchCached(key, fetcher).catch(() => {});
    return () => { set.delete(revalidate); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const e = key ? store.get(key) : undefined;
  return { data: e?.data as T | undefined, error: e?.error, loading: !!key && e?.data === undefined && !e?.error };
}
