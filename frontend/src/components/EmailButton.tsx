"use client";

import { useState } from "react";
import { Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { sendEmail } from "@/lib/api";
import { Button } from "@/components/ui/button";

/** Button-triggered email via Resend (no cron). */
export function EmailButton({ kind, month, label }: { kind: "nudges" | "report"; month?: string; label: string }) {
  const [busy, setBusy] = useState(false);
  async function go() {
    setBusy(true);
    try {
      const r = await sendEmail(kind, month);
      toast.success(`Sent to ${r.to}`);
    } catch (e) {
      toast.error("Email failed", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }
  return (
    <Button variant="outline" size="sm" className="h-11 md:h-8" onClick={go} disabled={busy}>
      {busy ? <Loader2 className="animate-spin" /> : <Mail />} {label}
    </Button>
  );
}
