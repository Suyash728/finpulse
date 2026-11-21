import { CheckCircle2, Flag, PauseCircle } from "lucide-react";
import type { RecurringItem } from "@/lib/api";
import { fmtDate, inr, titleCase } from "@/lib/format";

const STATUS = {
  active: { Icon: CheckCircle2, cls: "text-positive", label: "Active" },
  changed: { Icon: Flag, cls: "text-warning", label: "Price changed" },
  unused: { Icon: PauseCircle, cls: "text-muted-foreground", label: "Looks unused" },
} as const;

/** Recurring charges with next-due date and status (from /recurring). */
export function RecurringList({ items }: { items: RecurringItem[] }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">Load two months of data to detect recurring charges.</p>;
  const flagged = items.filter((i) => i.status !== "active").length;
  return (
    <div>
      <ul className="divide-y">
        {items.slice(0, 10).map((r) => {
          const s = STATUS[r.status];
          return (
            <li key={r.id} className="flex items-center gap-3 py-2">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-muted text-xs font-semibold uppercase">
                {r.merchant_norm.slice(0, 2)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{titleCase(r.merchant_norm)}</p>
                <p className="truncate text-xs text-muted-foreground">{r.next_due ? `Next: ${fmtDate(r.next_due)}` : r.category}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium tabular-nums">{inr(r.amount)}</p>
                <p className="text-[11px] text-muted-foreground">Monthly</p>
              </div>
              <s.Icon className={`h-4 w-4 shrink-0 ${s.cls}`} aria-label={s.label} />
            </li>
          );
        })}
      </ul>
      <div className="mt-2 flex justify-between border-t pt-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><CheckCircle2 className="h-3.5 w-3.5 text-positive" />{items.length - flagged} steady</span>
        <span className="flex items-center gap-1"><Flag className="h-3.5 w-3.5 text-warning" />{flagged} to review</span>
      </div>
    </div>
  );
}
