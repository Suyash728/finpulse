import { TodoCard } from "@/components/placeholder";

export default function PlanPage() {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <TodoCard title="Profile" slice={5}>Income, fixed costs, emergency fund, budgets.</TodoCard>
      <TodoCard title="Goals" slice={5}>Target amount + target date, progress bar.</TodoCard>
      <div className="lg:col-span-2">
        <TodoCard title="What-if simulator" slice={6}>
          e.g. &quot;cut Dining by 30%&quot;, &quot;rent +2,000&quot; → POST /simulate → baseline vs scenario goal dates.
        </TodoCard>
      </div>
    </div>
  );
}
