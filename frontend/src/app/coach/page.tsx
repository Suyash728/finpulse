"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Loader2, SendHorizontal, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import {
  getCoach, simulate, sse, startCoach, type Adjustment, type ChatTurn, type SimulateResult,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import TracePanel, { type TraceEvent } from "@/components/TracePanel";
import { Markdown } from "@/components/Markdown";
import { ProjectionChart } from "@/components/ProjectionChart";
import { Button } from "@/components/ui/button";

type Msg = {
  role: "user" | "assistant";
  content: string;
  events?: TraceEvent[];
  refused?: boolean;
  pending?: boolean;
  chart?: SimulateResult | null;
};

const SUGGESTIONS = [
  "What if rent goes up ₹3k?",
  "Can I reach my emergency fund by June if I cut Zomato 30%?",
  "Which subscriptions should I review?",
  "Should I buy Reliance shares?",
];

/** Re-run the coach's own simulate call (deterministic, Python) to draw its chart. */
async function chartFor(events: TraceEvent[]): Promise<SimulateResult | null> {
  const sim = [...events].reverse().find((e) => e.node === "simulate" && e.status === "ok");
  const adj = sim?.args?.adjustments as Adjustment[] | undefined;
  if (!adj) return null;
  try { return await simulate(adj); } catch { return null; }
}

function TraceDetails({ events }: { events: TraceEvent[] }) {
  const tools = events.filter((e) => e.node !== "answer" && !e.node.endsWith("_guard")).length;
  return (
    <details className="group mt-2 md:hidden">
      <summary className="flex h-9 cursor-pointer list-none items-center gap-1 text-xs text-muted-foreground">
        <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
        Trace · {tools} tool call{tools === 1 ? "" : "s"}
      </summary>
      <TracePanel events={events} />
    </details>
  );
}

export default function CoachPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const closeRef = useRef<(() => void) | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => closeRef.current?.(), []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs]);

  const patchLast = (fn: (m: Msg) => Msg) =>
    setMsgs((prev) => prev.map((m, i) => (i === prev.length - 1 ? fn(m) : m)));

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const history: ChatTurn[] = msgs.filter((m) => !m.pending).map(({ role, content }) => ({ role, content }));
    setMsgs((prev) => [...prev, { role: "user", content: message }, { role: "assistant", content: "", events: [], pending: true }]);
    setInput("");
    setBusy(true);
    try {
      const { run_id } = await startCoach(message, history);
      closeRef.current = sse<TraceEvent>(
        `/coach/${run_id}/events`,
        (ev) => patchLast((m) => ({ ...m, events: [...(m.events ?? []), ev] })),
        async () => {
          try {
            const res = await getCoach(run_id);
            const chart = await chartFor(res.events);
            patchLast((m) => ({ ...m, content: res.answer ?? "No answer.", refused: res.refused, events: res.events, pending: false, chart }));
          } catch (e) {
            patchLast((m) => ({ ...m, content: "Couldn't fetch the answer.", pending: false }));
            toast.error("Coach failed", { description: (e as Error).message });
          } finally {
            setBusy(false);
          }
        },
      );
    } catch (e) {
      patchLast((m) => ({ ...m, content: "Couldn't reach the coach.", pending: false }));
      toast.error("Coach failed", { description: (e as Error).message });
      setBusy(false);
    }
  }

  const lastEvents = [...msgs].reverse().find((m) => m.role === "assistant")?.events ?? [];

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-start">
      <section className="flex min-h-[60dvh] flex-1 flex-col gap-3">
        {msgs.length === 0 && (
          <div className="space-y-3 rounded-xl border bg-card p-4">
            <p className="text-sm">
              Ask about your money. The coach uses your data and the simulator. It never picks stocks and
              never tells you to cut essentials.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="min-h-11 rounded-full border bg-background px-3 py-2 text-left text-xs hover:bg-accent md:min-h-9">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <ol className="space-y-3">
          {msgs.map((m, i) => (
            <li key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div className={cn(
                "max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm",
                m.role === "user" ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm border bg-card",
                m.refused && "border-warning/60",
              )}>
                {m.role === "user" ? m.content : m.pending ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {m.events?.at(-1) ? `Running ${m.events.at(-1)!.node}…` : "Thinking…"}
                  </span>
                ) : (
                  <>
                    {m.refused && (
                      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-warning">
                        <ShieldAlert className="h-3.5 w-3.5" /> Guardrail: no security picks
                      </p>
                    )}
                    <Markdown text={m.content} />
                    {m.chart && <div className="mt-3 border-t pt-3"><ProjectionChart result={m.chart} /></div>}
                  </>
                )}
                {m.role === "assistant" && (m.events?.length ?? 0) > 0 && <TraceDetails events={m.events!} />}
              </div>
            </li>
          ))}
        </ol>
        <div ref={endRef} className="scroll-mb-40 md:scroll-mb-24" />

        <form onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="sticky bottom-20 z-10 mt-auto flex gap-2 rounded-xl border bg-background/95 p-2 backdrop-blur md:bottom-4">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the coach…"
            aria-label="Message the coach"
            className="h-11 min-w-0 flex-1 bg-transparent px-2 text-sm outline-none md:h-9" />
          <Button type="submit" size="icon" className="h-11 w-11 md:h-9 md:w-9" disabled={busy || !input.trim()} aria-label="Send">
            {busy ? <Loader2 className="animate-spin" /> : <SendHorizontal />}
          </Button>
        </form>
      </section>

      <div className="hidden md:sticky md:top-20 md:block">
        <TracePanel events={lastEvents} />
      </div>
    </div>
  );
}
