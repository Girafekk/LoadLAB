import Link from "next/link";
import { cookies } from "next/headers";
import { Suspense, type ReactNode } from "react";

import { AdminShell } from "@/components/admin/admin-shell";
import { buttonVariants } from "@/components/ui/button";
import { adminContent } from "@/content/admin";
import { cn } from "@/lib/utils";

const API_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8001";

type AdminUser = { id: number; email: string; role: string };

/** Проверка роли на сервере: клиентская защита лишь дополняет её. */
async function getAdminFromCookie(): Promise<{ state: "ok"; user: AdminUser } | { state: "denied" | "error" }> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((item) => `${item.name}=${item.value}`)
    .join("; ");
  if (!cookieHeader) return { state: "denied" };
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (response.status === 401 || response.status === 403) return { state: "denied" };
    if (!response.ok) return { state: "error" };
    const user = (await response.json()) as AdminUser;
    return user.role === "admin" ? { state: "ok", user } : { state: "denied" };
  } catch {
    return { state: "error" };
  }
}

async function AdminGate({ children }: { children: ReactNode }) {
  const result = await getAdminFromCookie();
  if (result.state !== "ok") {
    return (
      <div className="rounded-xl border bg-card p-6">
        <h1 className="text-2xl font-semibold tracking-tight break-words sm:text-3xl">
          {adminContent.title}
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          {result.state === "error" ? adminContent.serverUnavailable : adminContent.accessDenied}
        </p>
        <Link
          href="/login?next=%2Fadmin"
          className={cn(buttonVariants({ size: "lg" }), "mt-4 px-4")}
        >
          {adminContent.login}
        </Link>
      </div>
    );
  }
  return <AdminShell>{children}</AdminShell>;
}

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Suspense fallback={<p className="text-sm text-muted-foreground">{adminContent.loading}</p>}>
        <AdminGate>{children}</AdminGate>
      </Suspense>
    </div>
  );
}
