"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { authContent } from "@/content/auth";
import { siteConfig } from "@/lib/site-config";

const { menu } = authContent;
const ITEM_CLASSES =
  "block w-full rounded-md px-2 py-3 text-left text-base font-medium text-foreground hover:bg-muted";

/** Выпадающее меню навигации для узких и средних экранов (до 1024 px). */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { status, user, logout } = useAuth();
  const close = () => setOpen(false);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    function onPointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="xl:hidden">
      <Button
        ref={buttonRef}
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
                <Link href={item.href} onClick={close} className={ITEM_CLASSES}>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>

          {status !== "loading" && (
            <ul className="mx-auto flex max-w-6xl flex-col border-t px-4 py-2">
              {user ? (
                <>
                  <li>
                    <Link href="/profile" onClick={close} className={ITEM_CLASSES}>
                      {menu.profile}
                      <span className="block truncate text-sm font-normal text-muted-foreground">
                        {user.email}
                      </span>
                    </Link>
                  </li>
                  <li>
                    <button
                      type="button"
                      className={ITEM_CLASSES}
                      onClick={() => {
                        close();
                        logout().catch(() => {});
                      }}
                    >
                      {menu.logout}
                    </button>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Link href="/login" onClick={close} className={ITEM_CLASSES}>
                      {menu.login}
                    </Link>
                  </li>
                  <li>
                    <Link href="/register" onClick={close} className={ITEM_CLASSES}>
                      {menu.register}
                    </Link>
                  </li>
                </>
              )}
            </ul>
          )}
        </nav>
      )}
    </div>
  );
}
