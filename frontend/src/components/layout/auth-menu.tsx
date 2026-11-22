"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/auth-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { authContent } from "@/content/auth";
import { cn } from "@/lib/utils";

const { menu } = authContent;

/** Блок входа в шапке: «Войти» для гостя, почта и «Выйти» для вошедшего. */
export function AuthMenu() {
  const { status, user, logout } = useAuth();

  // Пока неизвестно, вошёл ли человек, не показываем ни один из вариантов.
  if (status === "loading") return null;

  if (!user) {
    return (
      <Link
        href="/login"
        className={cn(buttonVariants({ variant: "outline", size: "lg" }), "px-4")}
      >
        {menu.login}
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-1">
      {user.role === "admin" ? (
        <Link
          href="/admin"
          className={cn(
            buttonVariants({ variant: "outline", size: "lg" }),
            "hidden px-3 sm:inline-flex",
          )}
        >
          Админ-панель
        </Link>
      ) : null}
      <Link
        href="/profile"
        title={user.email}
        className="max-w-44 truncate rounded-md px-2 py-2 text-sm font-medium hover:bg-muted"
      >
        {user.email}
      </Link>
      {/* Ошибка выхода здесь не показывается: человек остаётся вошедшим и может повторить. */}
      <Button variant="ghost" size="lg" className="px-3" onClick={() => logout().catch(() => {})}>
        {menu.logout}
      </Button>
    </div>
  );
}
