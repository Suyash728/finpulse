import { TodoCard } from "@/components/placeholder";

export default function TransactionsPage() {
  return (
    <div className="space-y-3">
      <TodoCard title="Upload statement / paste SMS" slice={1}>PDF, CSV or SMS text → POST /ingest.</TodoCard>
      <TodoCard title="Transactions" slice={2}>
        Filter by month / category / needs review. Each row shows a cat_source badge (rule / ai / user) and confidence.
      </TodoCard>
      <TodoCard title="Correct category → learn rule → apply to similar" slice={3} />
    </div>
  );
}
