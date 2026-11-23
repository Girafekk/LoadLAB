import Link from "next/link";

import { AuthMenu } from "@/components/layout/auth-menu";
import { Logo } from "@/components/layout/logo";
import { MobileNav } from "@/components/layout/mobile-nav";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { siteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur">
      <div className="relative mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />

        <nav aria-label="Основная навигация" className="hidden min-[1500px]:block">
          <ul className="flex items-center gap-1">
            {siteConfig.nav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="rounded-md px-2.5 py-2 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-1">
          <ThemeToggle />
          <div className="hidden sm:block">
            <AuthMenu />
          </div>
          <Link
            href={siteConfig.learnHref}
            className={cn(buttonVariants({ size: "lg" }), "hidden px-4 lg:inline-flex xl:hidden")}
          >
            Начать обучение
          </Link>
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
