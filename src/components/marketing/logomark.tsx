import { cn } from "@/lib/utils";

export function Logomark({
  className,
  withRing = true,
}: {
  className?: string;
  withRing?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={cn("h-8 w-8", className)}
    >
      {withRing ? (
        <circle
          cx="32"
          cy="32"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
        />
      ) : null}
      <path d="M32 14V22" stroke="currentColor" strokeWidth="4" />
      <path d="M32 42V50" stroke="currentColor" strokeWidth="4" />
      <path d="M14 32H22" stroke="currentColor" strokeWidth="4" />
      <path d="M42 32H50" stroke="currentColor" strokeWidth="4" />
      <path d="M32 21 L42 40 L22 40 Z" fill="#10D94B" />
    </svg>
  );
}
