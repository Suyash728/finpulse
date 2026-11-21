"use client";

import { useRef, useState } from "react";
import { FileUp, Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { ingestFile, ingestSms, type IngestResult } from "@/lib/api";
import { emitDataChanged } from "@/lib/events";
import { pct } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const SAMPLES = [
  { label: "Oct SMS", file: "sms_oct.txt", kind: "sms" },
  { label: "Oct CSV", file: "statement_oct.csv", kind: "file" },
  { label: "Nov SMS", file: "sms_nov.txt", kind: "sms" },
  { label: "Nov CSV", file: "statement_nov.csv", kind: "file" },
  { label: "Nov PDF", file: "statement_nov.pdf", kind: "file" },
] as const;

function announce(r: IngestResult, source: string) {
  const parts = [`${r.rows.length} transactions`, `${pct(r.auto_rate)} auto-categorised`];
  if (r.reconciled?.ok) parts.push("reconciled ✓");
  toast.success(parts.join(" · "), { description: source });
}

/** "+ Add": paste SMS, upload CSV/PDF, or load a bundled sample (public/samples). */
export function IngestSheet({ triggerClassName }: { triggerClassName?: string }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(label: string, fn: () => Promise<IngestResult>) {
    setBusy(label);
    try {
      const r = await fn();
      announce(r, label);
      emitDataChanged();
      setOpen(false);
      setText("");
    } catch (e) {
      toast.error(`Couldn't import ${label}`, { description: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  const loadSample = (s: (typeof SAMPLES)[number]) =>
    run(s.label, async () => {
      const res = await fetch(`/samples/${s.file}`);
      if (!res.ok) throw new Error(`sample ${s.file} missing`);
      return s.kind === "sms" ? ingestSms(await res.text()) : ingestFile(await res.blob(), s.file);
    });

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button className={triggerClassName ?? "h-9"}>
          <Plus /> Add
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="flex w-full flex-col gap-4 overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Add transactions</SheetTitle>
          <SheetDescription>Paste bank SMS or upload a CSV/PDF statement.</SheetDescription>
        </SheetHeader>

        <Tabs defaultValue="sms">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="sms">Paste SMS</TabsTrigger>
            <TabsTrigger value="file">Upload file</TabsTrigger>
          </TabsList>
          <TabsContent value="sms" className="space-y-2">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste one or more bank / UPI SMS…"
              className="h-44 w-full resize-none rounded-md border bg-background p-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
            <Button
              className="h-11 w-full md:h-9"
              disabled={!text.trim() || !!busy}
              onClick={() => run("Pasted SMS", () => ingestSms(text))}
            >
              {busy === "Pasted SMS" && <Loader2 className="animate-spin" />} Import SMS
            </Button>
          </TabsContent>
          <TabsContent value="file" className="space-y-2">
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.pdf,.txt,text/csv,application/pdf,text/plain"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) run(f.name, () => ingestFile(f));
                e.target.value = "";
              }}
            />
            <Button
              variant="outline"
              className="h-24 w-full flex-col border-dashed"
              disabled={!!busy}
              onClick={() => fileRef.current?.click()}
            >
              <FileUp className="!size-5" />
              <span>Choose CSV or PDF</span>
            </Button>
          </TabsContent>
        </Tabs>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Load sample</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {SAMPLES.map((s) => (
              <Button
                key={s.file}
                variant="secondary"
                className="h-11 md:h-9"
                disabled={!!busy}
                onClick={() => loadSample(s)}
              >
                {busy === s.label && <Loader2 className="animate-spin" />}
                {s.label}
              </Button>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
