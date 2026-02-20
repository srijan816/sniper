import { cn } from "@/lib/utils";

export function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden="true"
      className={cn("h-3.5 w-3.5", className)}
    >
      <path d="M8 1L15 15H1L8 1Z" fill="currentColor" />
    </svg>
  );
}
