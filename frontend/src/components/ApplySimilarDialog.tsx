"use client";

import type { Category, Transaction } from "@/lib/api";
import { fmtDay, inr } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export type SimilarPrompt = { ruleId: string; category: Category; merchant: string; rows: Transaction[]; ids: string[] };

/** "Apply 'Food Delivery' to 6 similar transactions?" with a preview list. */
export function ApplySimilarDialog({
  prompt,
  busy,
  onApply,
  onSkip,
}: {
  prompt: SimilarPrompt | null;
  busy?: boolean;
  onApply: () => void;
  onSkip: () => void;
}) {
  const n = prompt?.ids.length ?? 0;
  return (
    <Dialog open={!!prompt} onOpenChange={(o) => !o && onSkip()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            Apply &lsquo;{prompt?.category}&rsquo; to {n} similar transaction{n === 1 ? "" : "s"}?
          </DialogTitle>
          <DialogDescription>
            FinPulse learned a rule for <span className="font-medium text-foreground">{prompt?.merchant}</span>.
            Future uploads use it automatically.
          </DialogDescription>
        </DialogHeader>
        {prompt && prompt.rows.length > 0 && (
          <ul className="max-h-60 divide-y overflow-auto rounded-md border text-sm">
            {prompt.rows.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate">{t.raw_desc}</p>
                  <p className="text-xs text-muted-foreground">
                    {fmtDay(t.date)} · now {t.category}
                  </p>
                </div>
                <span className="tabular-nums">{inr(t.amount)}</span>
              </li>
            ))}
          </ul>
        )}
        {prompt && prompt.rows.length < n && (
          <p className="text-xs text-muted-foreground">+{n - prompt.rows.length} more not shown in this view</p>
        )}
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 md:h-9" onClick={onSkip} disabled={busy}>
            Skip
          </Button>
          <Button className="h-11 md:h-9" onClick={onApply} disabled={busy}>
            Apply to {n}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
