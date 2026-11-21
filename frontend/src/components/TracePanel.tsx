"use client";

/** One event per coach step: {node: tool_name, status, tier_used, ms, args, result_summary}. */
export type TraceEvent = {
  node: string;
  status: string;
  tier_used: string | null;
  ms: number;
  args?: Record<string, unknown>;
  result_summary?: string;
  error?: string;
};

const tierColor: Record<string, string> = {
  groq: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  gemini: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  local: "bg-green-500/15 text-green-600 dark:text-green-400",
};

const statusColor: Record<string, string> = {
  error: "text-negative",
  refused: "text-warning",
  ok: "text-positive",
  finished: "text-positive",
};

export default function TracePanel({ events }: { events: TraceEvent[] }) {
  return (
    <aside className="w-full shrink-0 rounded-xl border bg-card p-3 text-sm md:w-80">
      <h2 className="mb-2 font-semibold">Agent trace</h2>
      {events.length === 0 && <p className="text-muted-foreground">No run yet.</p>}
      <ol className="space-y-2 font-mono text-xs">
        {events.map((e, i) => (
          <li key={i} className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="truncate font-medium">{e.node}</span>
              <span className={statusColor[e.status] ?? "text-muted-foreground"}>{e.status}</span>
              {e.tier_used && (
                <span className={`rounded px-1 ${tierColor[e.tier_used] ?? "bg-muted"}`}>{e.tier_used}</span>
              )}
              {e.ms > 0 && <span className="ml-auto text-muted-foreground">{e.ms} ms</span>}
            </div>
            {e.args && Object.keys(e.args).length > 0 && (
              <p className="truncate text-muted-foreground">args {JSON.stringify(e.args)}</p>
            )}
            {e.result_summary && <p className="text-muted-foreground">→ {e.result_summary}</p>}
            {e.error && <p className="text-negative">{e.error}</p>}
          </li>
        ))}
      </ol>
    </aside>
  );
}
