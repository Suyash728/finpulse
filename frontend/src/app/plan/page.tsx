import { GoalsEditor } from "@/components/GoalsEditor";
import { ProfileForm } from "@/components/ProfileForm";
import { WhatIfPanel } from "@/components/WhatIfPanel";

export default function PlanPage() {
  return (
    <div className="space-y-3">
      <WhatIfPanel />
      <div className="grid gap-3 lg:grid-cols-2">
        <GoalsEditor />
        <ProfileForm />
      </div>
    </div>
  );
}
