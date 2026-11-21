import { TodoCard } from "@/components/placeholder";

export default function ReportPage() {
  return (
    <div className="space-y-3">
      <TodoCard title="Monthly review" slice={8}>GET /report/{"{month}"}: income, spend, savings rate, category vs budget, goal progress.</TodoCard>
      <TodoCard title="Email this report / nudges" slice={9}>POST /email/send (Resend, button-triggered).</TodoCard>
    </div>
  );
}
