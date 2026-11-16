import Link from "next/link";

import { BackendStatus } from "@/components/layout/backend-status";
import { Logo } from "@/components/layout/logo";
import { siteConfig } from "@/lib/site-config";

export function SiteFooter() {
  return (
    <footer className="border-t bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm space-y-3">
          <Logo />
          <p className="text-sm leading-relaxed text-muted-foreground">
            {siteConfig.tagline}. Проект находится в разработке: сейчас готов
            технический фундамент, учебные материалы появятся на следующих этапах.
          </p>
        </div>

        <nav aria-label="Навигация в подвале">
          <ul className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {siteConfig.nav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <div className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>© 2026 {siteConfig.name}</p>
          <BackendStatus />
        </div>
      </div>
    </footer>
  );
}
