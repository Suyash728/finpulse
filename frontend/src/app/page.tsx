import { StatTile, TodoCard } from "@/components/placeholder";
import { AutoRateChip } from "@/components/AutoRateChip";
import { IngestSheet } from "@/components/IngestSheet";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <AutoRateChip />
        <div className="ml-auto"><IngestSheet /></div>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Income (month)" />
        <StatTile label="Spent" />
        <StatTile label="Saved" />
        <StatTile label="Auto-categorized" />
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <TodoCard title="Spend vs budget by category" slice={7}>Recharts bar: budget vs actual; essentials marked.</TodoCard>
        </div>
        <div className="space-y-3">
          <TodoCard title="Nudges" slice={7}>GET /nudges, drift / price change / unused.</TodoCard>
          <TodoCard title="Recurring & subscriptions" slice={4}>GET /recurring with active / changed / unused badges.</TodoCard>
        </div>
      </div>
    </div>
  );
}
