"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { siteConfig } from "@/lib/site-config";

/** Выпадающее меню навигации для узких экранов. */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <Button
        variant="ghost"
        size="icon-lg"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="mobile-nav"
        aria-label={open ? "Закрыть меню" : "Открыть меню"}
      >
        {open ? <X /> : <Menu />}
      </Button>

      {open && (
        <nav
          id="mobile-nav"
          aria-label="Основная навигация"
          className="absolute inset-x-0 top-full border-b bg-background shadow-lg"
        >
          <ul className="mx-auto flex max-w-6xl flex-col px-4 py-2">
            {siteConfig.nav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-2 py-3 text-base font-medium text-foreground hover:bg-muted"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
}
