"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  applyRule, correctTransaction, listTransactions, type Category, type Transaction,
} from "@/lib/api";
import { emitDataChanged, onDataChanged } from "@/lib/events";
import { fmtMonth, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import { AutoRateChip } from "@/components/AutoRateChip";
import { ApplySimilarDialog, type SimilarPrompt } from "@/components/ApplySimilarDialog";
import { IngestSheet } from "@/components/IngestSheet";
import { TxnList } from "@/components/TxnList";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type Filter = "all" | "review" | Category;

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "h-9 shrink-0 rounded-full border px-3 text-xs transition-colors",
        active ? "border-primary bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

export default function TransactionsPage() {
  const [items, setItems] = useState<Transaction[] | null>(null);
  const [month, setMonth] = useState<string>("all");
  const [filter, setFilter] = useState<Filter>("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<SimilarPrompt | null>(null);
  const [applying, setApplying] = useState(false);

  const load = useCallback(() => {
    listTransactions()
      .then((d) => setItems(d.items))
      .catch((e) => {
        setItems([]);
        toast.error("Couldn't load transactions", { description: (e as Error).message });
      });
  }, []);

  useEffect(() => {
    load();
    return onDataChanged(load);
  }, [load]);

  const all = useMemo(() => items ?? [], [items]);
  const months = useMemo(() => Array.from(new Set(all.map((t) => t.date.slice(0, 7)))).sort().reverse(), [all]);
  const inMonth = useMemo(() => (month === "all" ? all : all.filter((t) => t.date.startsWith(month))), [all, month]);
  const catCounts = useMemo(() => {
    const m = new Map<Category, number>();
    inMonth.forEach((t) => m.set(t.category, (m.get(t.category) ?? 0) + 1));
    return Array.from(m).sort((a, b) => b[1] - a[1]);
  }, [inMonth]);
  const reviewCount = inMonth.filter((t) => t.needs_review).length;
  const shown = inMonth.filter((t) =>
    filter === "all" ? true : filter === "review" ? t.needs_review : t.category === filter,
  );

  async function onCorrect(t: Transaction, category: Category) {
    if (category === t.category && t.cat_source === "user") return;
    setBusyId(t.id);
    try {
      const r = await correctTransaction(t.id, category);
      setItems((prev) =>
        (prev ?? []).map((x) =>
          x.id === t.id ? { ...x, category, cat_source: "user", confidence: 1, needs_review: false } : x,
        ),
      );
      const merchant = titleCase(t.merchant_norm);
      const ids = r.similar_ids.filter((id) => id !== t.id);
      if (ids.length > 0) {
        setPrompt({
          ruleId: r.rule.id,
          category,
          merchant,
          ids,
          rows: all.filter((x) => ids.includes(x.id)),
        });
      } else {
        toast.success(`Learned: ${merchant} → ${category}`);
      }
      emitDataChanged();
    } catch (e) {
      toast.error("Couldn't save the correction", { description: (e as Error).message });
    } finally {
      setBusyId(null);
    }
  }

  async function onApply() {
    if (!prompt) return;
    setApplying(true);
    const p = prompt;
    const before = new Map(all.filter((x) => p.ids.includes(x.id)).map((x) => [x.id, x.category]));
    try {
      const r = await applyRule(p.ruleId, p.ids);
      setPrompt(null);
      emitDataChanged();
      toast.success(`Applied ${p.category} to ${r.updated} transaction${r.updated === 1 ? "" : "s"}`, {
        duration: 5000,
        action: {
          label: "Undo",
          // Per playbook: re-correct each row back to its previous category.
          onClick: async () => {
            try {
              await Promise.all(Array.from(before).map(([id, cat]) => correctTransaction(id, cat)));
              emitDataChanged();
              toast("Undone");
            } catch (e) {
              toast.error("Undo failed", { description: (e as Error).message });
            }
          },
        },
      });
    } catch (e) {
      toast.error("Couldn't apply the rule", { description: (e as Error).message });
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={month} onValueChange={(v) => { setMonth(v); setFilter("all"); }}>
          <SelectTrigger className="h-9 w-36" aria-label="Month">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All months</SelectItem>
            {months.map((m) => (
              <SelectItem key={m} value={m}>{fmtMonth(m)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <AutoRateChip />
        <div className="ml-auto">
          <IngestSheet />
        </div>
      </div>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0">
        <Chip active={filter === "all"} onClick={() => setFilter("all")}>All · {inMonth.length}</Chip>
        <Chip active={filter === "review"} onClick={() => setFilter("review")}>
          Needs review · <span className={reviewCount ? "text-warning" : ""}>{reviewCount}</span>
        </Chip>
        {catCounts.map(([c, n]) => (
          <Chip key={c} active={filter === c} onClick={() => setFilter(c)}>{c} · {n}</Chip>
        ))}
      </div>

      {items === null ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : (
        <TxnList items={shown} onCorrect={onCorrect} busyId={busyId} />
      )}

      <ApplySimilarDialog prompt={prompt} busy={applying} onApply={onApply} onSkip={() => setPrompt(null)} />
    </div>
  );
}
