"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { buttonVariants } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { cn } from "@/lib/utils";

/** Защита страниц админки на клиенте. Настоящая проверка — на сервере. */
export function AdminShell({ children }: { children: ReactNode }) {
  const { status, user } = useAuth();

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
      <nav aria-label={t.title} className="flex flex-wrap gap-2 border-b pb-4">
        <Link
          href="/admin"
          className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
        >
          {t.dashboard}
        </Link>
        <Link
          href="/admin/students"
          className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
        >
          {t.students}
        </Link>
        <Link
          href="/admin/interview"
          className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
        >
          {t.interview}
        </Link>
      </nav>
      <div className="mt-6">{children}</div>
    </div>
  );
}
