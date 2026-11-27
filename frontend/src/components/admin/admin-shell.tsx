"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { buttonVariants } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { cn } from "@/lib/utils";

/** Защита страниц админки на клиенте. Настоящая проверка — на сервере. */
export function AdminShell({ children }: { children: ReactNode }) {
  const { status, user, version } = useAuth();
  const pathname = usePathname();

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">{t.accessDenied}</p>
        <Link
          href="/login?next=%2Fadmin"
          className={cn(buttonVariants({ size: "lg" }), "mt-4 px-4")}
        >
          {t.login}
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight break-words sm:text-3xl">
        {pathname.startsWith("/admin/students")
          ? t.students
          : pathname.startsWith("/admin/interview")
            ? t.interview
            : pathname.startsWith("/admin/answers")
              ? "Проверка ответов"
              : pathname.startsWith("/admin/lessons")
                ? "Редактор урока"
                : t.dashboard}
      </h1>
      <nav aria-label={t.title} className="flex flex-wrap gap-2 border-b pb-4">
        <Link
          href="/admin"
          aria-current={pathname === "/admin" ? "page" : undefined}
          className={cn(
            "rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
            pathname === "/admin" && "bg-muted",
          )}
        >
          {t.dashboard}
        </Link>
        <Link
          href="/admin/students"
          aria-current={pathname === "/admin/students" ? "page" : undefined}
          className={cn(
            "rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
            pathname === "/admin/students" && "bg-muted",
          )}
        >
          {t.students}
        </Link>
        <Link
          href="/admin/interview"
          aria-current={pathname === "/admin/interview" ? "page" : undefined}
          className={cn(
            "rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
            pathname === "/admin/interview" && "bg-muted",
          )}
        >
          {t.interview}
        </Link>
        <Link
          href="/admin/answers"
          aria-current={pathname === "/admin/answers" ? "page" : undefined}
          className={cn(
            "rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
            pathname === "/admin/answers" && "bg-muted",
          )}
        >
          Ответы
        </Link>
      </nav>
      <div key={`${user.id}:${version}`} className="mt-6">
        {children}
      </div>
    </div>
  );
}
