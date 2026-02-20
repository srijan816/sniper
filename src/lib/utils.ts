import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num);
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    DISCOVERED: "bg-[#F1F3F5] text-[#6B7280] border-[#D1D5DB]",
    PENDING_APPROVAL: "bg-[#FFF3CD] text-[#856404] border-[#FACC15]",
    APPROVED: "bg-[#D4EDDA] text-[#155724] border-[#0A7C2E]",
    WHITELISTED: "bg-[#8E95A3] text-white border-[#6B7280]",
    REJECTED: "bg-[#F8D7DA] text-[#721C24] border-[#DC2626]",
    TAKEDOWN_SUBMITTED: "bg-[#CCE5FF] text-[#004085] border-[#2563EB]",
    TAKEDOWN_CONFIRMED: "bg-[#10D94B] text-[#1A1C24] border-[#0A7C2E]",
    REMOVED: "bg-[#10D94B] text-[#1A1C24] border-[#0A7C2E]",
    PENDING: "bg-[#FFF3CD] text-[#856404] border-[#FACC15]",
    SUBMITTED: "bg-[#CCE5FF] text-[#004085] border-[#2563EB]",
    CONFIRMED: "bg-[#10D94B] text-[#1A1C24] border-[#0A7C2E]",
    FAILED: "bg-[#F8D7DA] text-[#721C24] border-[#DC2626]",
  };

  return colors[status] || "bg-muted text-muted-foreground border-border";
}

export function getStatusLabel(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

export const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
