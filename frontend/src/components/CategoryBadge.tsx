"use client";

import { CATEGORIES, ESSENTIAL, type Category, type Transaction } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";

const REVIEW_BELOW = 0.7;

function SourceMarker({ txn }: { txn: Transaction }) {
  if (txn.cat_source === "user") return <span className="text-muted-foreground">You</span>;
  if (txn.cat_source === "rule") return <span className="font-medium text-primary">Learned</span>;
  const low = txn.confidence < REVIEW_BELOW;
  return (
    <span className={cn("tabular-nums", low ? "font-medium text-warning" : "text-muted-foreground")}>
      AI {Math.round(txn.confidence * 100)}%
    </span>
  );
}

/** Category + source ("You" / "Learned" / "AI 82%"). Tap to correct. */
export function CategoryBadge({
  txn,
  onChange,
  disabled,
}: {
  txn: Transaction;
  onChange: (c: Category) => void;
  disabled?: boolean;
}) {
  return (
    <Select value={txn.category} onValueChange={(v) => onChange(v as Category)} disabled={disabled}>
      <SelectTrigger
        aria-label={`Category: ${txn.category}. Change`}
        className={cn(
          "h-11 w-auto min-w-0 gap-1.5 rounded-full px-3 text-xs md:h-8 [&>svg]:h-3 [&>svg]:w-3",
          txn.needs_review && "border-warning/60",
        )}
      >
        <span className="truncate font-medium">{txn.category}</span>
        <span className="text-muted-foreground">·</span>
        <SourceMarker txn={txn} />
      </SelectTrigger>
      <SelectContent className="max-h-80">
        {CATEGORIES.map((c) => (
          <SelectItem key={c} value={c} className="text-sm">
            {c}
            {ESSENTIAL.has(c) && <span className="ml-2 text-xs text-muted-foreground">essential</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
