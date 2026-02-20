import Image from "next/image";
import Link from "next/link";
import { Logomark } from "@/components/marketing/logomark";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/15 bg-[#1A1C24]">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-10 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-2">
          <div className="hidden items-center md:flex">
            <Image
              src="/logo-light.png"
              alt="SniperIP"
              width={240}
              height={240}
              className="h-14 w-auto"
            />
          </div>
          <div className="flex items-center gap-3 text-white md:hidden">
            <Logomark className="h-8 w-8 text-white" />
            <span className="font-[family-name:var(--font-heading)] text-lg font-bold">
              SniperIP
            </span>
          </div>
          <p className="text-sm text-[#94A3B8]">
            Surgical enforcement infrastructure for modern D2C teams.
          </p>
          <p className="inline-flex items-center gap-2 text-xs text-[#94A3B8]">
            <span className="marketing-status-dot h-2 w-2 rounded-full bg-[#10D94B]" />
            System Status: All Systems Operational
          </p>
          <p className="text-xs text-[#94A3B8]">© SniperIP. All rights reserved.</p>
        </div>

        <nav className="flex flex-wrap items-center gap-4 text-sm text-[#94A3B8]">
          <Link href="/terms" className="hover:text-white">
            Terms of Service
          </Link>
          <Link href="/privacy" className="hover:text-white">
            Privacy Policy
          </Link>
          <Link href="/dmca-policy" className="hover:text-white">
            DMCA Policy
          </Link>
          <Link href="/contact" className="hover:text-white">
            Contact
          </Link>
          <Link href="/auth/login" className="hover:text-white">
            Login
          </Link>
        </nav>
      </div>
    </footer>
  );
}
