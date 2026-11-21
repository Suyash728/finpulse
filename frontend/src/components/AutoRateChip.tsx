"use client";

import { useCallback, useEffect, useState } from "react";
import { getAutoRate, type AutoRatePoint } from "@/lib/api";
import { onDataChanged } from "@/lib/events";
import { pct } from "@/lib/format";

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const w = 56, h = 18;
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - Math.max(0, Math.min(1, v)) * h}`)
    .join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="overflow-visible">
      <polyline points={pts} fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

/** Latest auto-categorisation rate + trend. Refetches after every ingest/correction (demo proof). */
export function AutoRateChip() {
  const [series, setSeries] = useState<AutoRatePoint[] | null>(null);

  const load = useCallback(() => {
    getAutoRate().then((d) => setSeries(d.series)).catch(() => setSeries([]));
  }, []);

  useEffect(() => {
    load();
    return onDataChanged(load);
  }, [load]);

  const latest = series?.at(-1);
  const prev = series && series.length > 1 ? series[series.length - 2] : undefined;
  const up = latest && prev ? latest.auto_rate - prev.auto_rate : 0;

  return (
    <div
      className="flex h-9 items-center gap-2 rounded-md border bg-card px-2.5 text-xs"
      title={latest ? `Latest upload: ${latest.filename}` : "No uploads yet"}
    >
      <span className="text-muted-foreground">Auto</span>
      <span className="text-sm font-semibold tabular-nums">{latest ? pct(latest.auto_rate) : "—"}</span>
      {up !== 0 && (
        <span className={`tabular-nums ${up > 0 ? "text-positive" : "text-negative"}`}>
          {up > 0 ? "▲" : "▼"}
          {Math.abs(Math.round(up * 100))}
        </span>
      )}
      <Sparkline values={(series ?? []).map((p) => p.auto_rate)} />
    </div>
  );
}
