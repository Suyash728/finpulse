"use client";

import type { Category, Transaction } from "@/lib/api";
import { fmtDay, inr, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import { CategoryBadge } from "@/components/CategoryBadge";

function Amount({ t }: { t: Transaction }) {
  const credit = t.direction === "cr";
  return (
    <span className={cn("whitespace-nowrap font-semibold tabular-nums", credit ? "text-positive" : "text-negative")}>
      {credit ? "+" : "−"}
      {inr(t.amount)}
    </span>
  );
}

/** Grouped by date. Cards on mobile, a dense table on desktop. */
export function TxnList({
  items,
  onCorrect,
  busyId,
}: {
  items: Transaction[];
  onCorrect: (t: Transaction, c: Category) => void;
  busyId?: string | null;
}) {
  const groups = new Map<string, Transaction[]>();
  [...items]
    .sort((a, b) => b.date.localeCompare(a.date))
    .forEach((t) => groups.set(t.date, [...(groups.get(t.date) ?? []), t]));

  if (items.length === 0) {
    return (
      <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        No transactions here. Use <span className="font-medium text-foreground">+ Add</span> to paste SMS or upload a statement.
      </p>
    );
  }

  return (
    <>
      {/* mobile: cards */}
      <div className="space-y-4 md:hidden">
        {Array.from(groups).map(([day, rows]) => (
          <section key={day}>
            <h3 className="mb-1.5 text-xs font-medium text-muted-foreground">{fmtDay(day)}</h3>
            <ul className="divide-y rounded-xl border bg-card">
              {rows.map((t) => (
                <li key={t.id} className="space-y-2 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{titleCase(t.merchant_norm)}</p>
                      <p className="truncate text-xs text-muted-foreground">{t.raw_desc}</p>
                    </div>
                    <Amount t={t} />
                  </div>
                  <CategoryBadge txn={t} onChange={(c) => onCorrect(t, c)} disabled={busyId === t.id} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* desktop: table */}
      <div className="hidden overflow-hidden rounded-xl border bg-card md:block">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Merchant</th>
              <th className="px-3 py-2 font-medium">Category</th>
              <th className="px-3 py-2 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {Array.from(groups).flatMap(([day, rows]) =>
              rows.map((t, i) => (
                <tr key={t.id} className="hover:bg-muted/30">
                  <td className="whitespace-nowrap px-3 py-1.5 align-middle text-xs text-muted-foreground">
                    {i === 0 ? fmtDay(day) : ""}
                  </td>
                  <td className="max-w-0 px-3 py-1.5">
                    <p className="truncate font-semibold">{titleCase(t.merchant_norm)}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.raw_desc}</p>
                  </td>
                  <td className="px-3 py-1.5">
                    <CategoryBadge txn={t} onChange={(c) => onCorrect(t, c)} disabled={busyId === t.id} />
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <Amount t={t} />
                  </td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
