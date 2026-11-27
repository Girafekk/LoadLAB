import Link from "next/link";

import { BackendStatus } from "@/components/layout/backend-status";
import { Logo } from "@/components/layout/logo";
import { footerContent } from "@/content/layout";
import { siteConfig } from "@/lib/site-config";

export function SiteFooter() {
  return (
    <footer className="border-t bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm space-y-3">
          <Logo />
          <p className="text-sm leading-relaxed text-muted-foreground">
            {siteConfig.tagline}. {footerContent.stage}
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
            <li>
              <Link href="/glossary" className="text-muted-foreground hover:text-foreground">
                Словарь
              </Link>
            </li>
            <li>
              <Link href="/final-project" className="text-muted-foreground hover:text-foreground">
                Финальный проект
              </Link>
            </li>
            <li>
              <Link href="/jmeter-simulator" className="text-muted-foreground hover:text-foreground">
                JMeter-симулятор
              </Link>
            </li>
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
