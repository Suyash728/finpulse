import TracePanel from "@/components/TracePanel";
import { TodoCard } from "@/components/placeholder";

export default function CoachPage() {
  return (
    <div className="flex flex-col gap-3 md:flex-row">
      <div className="flex-1">
        <TodoCard title="Coach chat" slice={10}>
          POST /coach → stream GET /coach/{"{run_id}"}/events. Refuses security picks; never suggests cutting essentials.
        </TodoCard>
      </div>
      <TracePanel events={[]} />
    </div>
  );
}
