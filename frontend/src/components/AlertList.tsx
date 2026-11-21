"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, PauseCircle, X } from "lucide-react";
import type { RecurringItem } from "@/lib/api";
import { inr, titleCase } from "@/lib/format";

const KEY = "finpulse:dismissed-alerts";

const readDismissed = (): string[] => {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; }
};

/** Recurring 'changed' / 'unused' items. Dismiss hides locally (per id+status). Slice 4 adds nudges below. */
export function AlertList({ recurring, children }: { recurring: RecurringItem[]; children?: React.ReactNode }) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  useEffect(() => setDismissed(readDismissed()), []);

  const keyOf = (r: RecurringItem) => `${r.id}:${r.status}:${r.amount}`;
  const items = recurring.filter((r) => r.status !== "active" && !dismissed.includes(keyOf(r)));

  const dismiss = (r: RecurringItem) => {
    const next = [...dismissed, keyOf(r)];
    setDismissed(next);
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode */ }
  };

  if (items.length === 0 && !children) {
    return <p className="text-sm text-muted-foreground">No alerts. Subscriptions look steady.</p>;
  }
  return (
    <ul className="divide-y">
      {items.map((r) => {
        const changed = r.status === "changed";
        const Icon = changed ? AlertTriangle : PauseCircle;
        return (
          <li key={r.id} className="flex items-center gap-3 py-2">
            <Icon className={changed ? "h-4 w-4 shrink-0 text-warning" : "h-4 w-4 shrink-0 text-muted-foreground"} />
            <div className="min-w-0 flex-1 text-sm">
              <p className="truncate">
                <span className="font-medium">{titleCase(r.merchant_norm)}</span>{" "}
                {changed && r.prev_amount != null ? (
                  <span className="tabular-nums">
                    {inr(r.prev_amount)} → <span className="font-medium">{inr(r.amount)}</span>
                  </span>
                ) : (
                  <span className="tabular-nums">{inr(r.amount)}/mo · looks unused</span>
                )}
              </p>
              {r.note && <p className="truncate text-xs text-muted-foreground">{r.note}</p>}
            </div>
            <button
              onClick={() => dismiss(r)}
              aria-label={`Dismiss ${r.merchant_norm} alert`}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-md text-muted-foreground hover:bg-accent md:h-8 md:w-8"
            >
              <X className="h-4 w-4" />
            </button>
          </li>
        );
      })}
      {children}
    </ul>
  );
}
