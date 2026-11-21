import Link from "next/link";
import { ChevronRight, Scale, TrendingUp } from "lucide-react";
import type { Nudge } from "@/lib/api";
import { cn } from "@/lib/utils";

// price_change / unused are already shown from /recurring in AlertList, so only these kinds render here.
const SHOWN: Nudge["kind"][] = ["drift", "essentials_over_income"];
const ICON = { drift: TrendingUp, essentials_over_income: Scale } as const;
const HREF = { drift: "/transactions", essentials_over_income: "/plan" } as const;

/** Nudge rows for AlertList: icon by kind, one line, tap -> relevant page. */
export function NudgeRows({ nudges }: { nudges: Nudge[] }) {
  return (
    <>
      {nudges.filter((n) => SHOWN.includes(n.kind)).map((n) => {
        const kind = n.kind as keyof typeof ICON;
        const Icon = ICON[kind];
        return (
          <li key={n.id}>
            <Link href={HREF[kind]} className="flex min-h-11 items-center gap-3 py-2 hover:bg-accent/50">
              <Icon className={cn("h-4 w-4 shrink-0", n.severity === "info" ? "text-muted-foreground" : n.severity === "alert" ? "text-negative" : "text-warning")} />
              <p className="min-w-0 flex-1 truncate text-sm">{n.message}</p>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </Link>
          </li>
        );
      })}
    </>
  );
}
