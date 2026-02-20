import { cn } from "@/lib/utils";

export function SniperChevron({
  className,
  size = 14,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      aria-hidden="true"
      className={cn("shrink-0", className)}
    >
      <path d="M8 1L15 15H1L8 1Z" fill="currentColor" />
    </svg>
  );
}
