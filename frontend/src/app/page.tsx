"use client";

import { useRef, useState } from "react";
import TracePanel, { type TraceEvent } from "@/components/TracePanel";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8787";

type Sample = { id: string; title: string; input: string };

export default function Home() {
  const [input, setInput] = useState("");
  const [privacy, setPrivacy] = useState(false);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const es = useRef<EventSource | null>(null);

  async function loadSample() {
    const r = await fetch(`${API}/samples`).then((r) => r.json());
    const s: Sample = r.data[0];
    setInput(s.input);
  }

  function listen(id: string) {
    es.current?.close();
    const src = new EventSource(`${API}/runs/${id}/events`);
    src.onmessage = (m) => {
      const ev: TraceEvent & { result?: string } = JSON.parse(m.data);
      setEvents((prev) => [...prev, ev]);
      if (ev.node === "approval" && ev.status === "waiting") setWaiting(true);
      if (ev.result) setResult(ev.result);
    };
    src.addEventListener("end", () => src.close());
    es.current = src;
  }

  async function run() {
    setEvents([]);
    setResult(null);
    setWaiting(false);
    const r = await fetch(`${API}/runs`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ input, privacy_mode: privacy }),
    }).then((r) => r.json());
    setRunId(r.data.run_id);
    listen(r.data.run_id);
  }

  async function decide(approve: boolean) {
    setWaiting(false);
    await fetch(`${API}/runs/${runId}/resume`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ approve }),
    });
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-4 p-4 md:flex-row">
      <section className="flex-1 space-y-3">
        <h1 className="text-2xl font-bold">Hackathon starter</h1>
        <textarea
          className="h-32 w-full rounded border p-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the case..."
        />
        <div className="flex flex-wrap items-center gap-3">
          <button className="rounded border px-3 py-1" onClick={loadSample}>
            Load sample case
          </button>
          <button
            className="rounded bg-black px-3 py-1 text-white disabled:opacity-40"
            onClick={run}
            disabled={!input}
          >
            Run agent
          </button>
          <label className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={privacy} onChange={(e) => setPrivacy(e.target.checked)} />
            Privacy Mode (local GPU only)
          </label>
        </div>
        {waiting && (
          <div className="rounded border border-amber-400 bg-amber-50 p-3">
            <p className="mb-2 font-medium">The agent wants to act. Approve?</p>
            <button className="mr-2 rounded bg-green-600 px-3 py-1 text-white" onClick={() => decide(true)}>
              Approve
            </button>
            <button className="rounded bg-red-600 px-3 py-1 text-white" onClick={() => decide(false)}>
              Reject
            </button>
          </div>
        )}
        {result && <p className="rounded bg-gray-100 p-3">Result: {result}</p>}
      </section>
      <TracePanel events={events} />
    </main>
  );
}
