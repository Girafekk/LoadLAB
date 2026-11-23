import Link from "next/link";

import { siteConfig } from "@/lib/site-config";

/** Знак LoadLab: кривая растущей нагрузки + текстовое название. */
export function Logo() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      aria-label={`${siteConfig.name} — на главную`}
    >
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <svg
          viewBox="0 0 24 24"
          className="size-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M3 18h3l3.5-9 4 6 2.5-4H21" />
        </svg>
      </span>
      <span className="text-lg font-semibold tracking-tight">
        Load<span className="text-brand">Lab</span>
      </span>
    </Link>
  );
}
