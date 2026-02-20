import { cn } from "@/lib/utils";

const statusClasses: Record<string, string> = {
  DISCOVERED: "bg-[#F1F3F5] text-[#6B7280] border-l-[#9CA3AF]",
  PENDING_APPROVAL: "bg-[#FFF3CD] text-[#856404] border-l-[#D39E00]",
  PENDING: "bg-[#FFF3CD] text-[#856404] border-l-[#D39E00]",
  APPROVED: "bg-[#D4EDDA] text-[#155724] border-l-[#0A7C2E]",
  SUBMITTED: "bg-[#CCE5FF] text-[#004085] border-l-[#0056B3]",
  TAKEDOWN_SUBMITTED: "bg-[#CCE5FF] text-[#004085] border-l-[#0056B3]",
  CONFIRMED: "bg-[#10D94B] text-white border-l-[#0A7C2E]",
  TAKEDOWN_CONFIRMED: "bg-[#10D94B] text-white border-l-[#0A7C2E]",
  REMOVED: "bg-[#10D94B] text-white border-l-[#0A7C2E]",
  FAILED: "bg-[#F8D7DA] text-[#721C24] border-l-[#A71D2A]",
  WHITELISTED: "bg-[#8E95A3] text-white border-l-[#6B7280]",
  REJECTED: "bg-[#F8D7DA] text-[#721C24] border-l-[#A71D2A]",
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border-l-[3px] px-2 py-1 text-app-xs font-medium uppercase tracking-wide",
        statusClasses[status] ?? "bg-muted text-muted-foreground border-l-muted-foreground",
        className,
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
