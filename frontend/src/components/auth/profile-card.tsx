"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthCard, FormError } from "@/components/auth/auth-card";
import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { authContent } from "@/content/auth";
import { toolsContent } from "@/content/tools";
import { cn } from "@/lib/utils";

const { profile: text, roles, errors } = authContent;

/**
 * Профиль доступен только вошедшим: гостя переводим на страницу входа.
 * Это удобство интерфейса, а не защита — данные профиля сервер и так
 * не отдаст без действующей сессии.
 */
export function ProfileCard() {
  const router = useRouter();
  const { status, user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "anonymous") router.replace("/login?next=/profile");
  }, [status, router]);

  async function handleLogout() {
    setLoggingOut(true);
    setError(null);
    try {
      await logout();
    } catch {
      setError(errors.logoutFailed);
      setLoggingOut(false);
    }
  }

  if (status !== "authenticated" || !user) {
    return (
      <AuthCard title={text.title} description={text.description}>
        <p className="text-sm text-muted-foreground" role="status">
          {status === "loading" ? text.loading : text.redirecting}
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={text.title} description={text.description}>
      <dl className="space-y-4">
        <div>
          <dt className="text-sm text-muted-foreground">{text.email}</dt>
          <dd className="mt-1 font-medium break-all">{user.email}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{text.role}</dt>
          <dd className="mt-1">
            <Badge variant="secondary">{roles[user.role]}</Badge>
          </dd>
        </div>
      </dl>

      <div className="mt-6 space-y-3 border-t pt-6">
        <FormError message={error} />
        {user.role === "admin" ? (
          <Link
            href="/admin"
            className={cn(buttonVariants({ size: "lg" }), "h-10 w-full text-base")}
          >
            Открыть админ-панель
          </Link>
        ) : null}
        <Link
          href="/profile/tools"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 w-full text-base")}
        >
          {toolsContent.profileTitle}
        </Link>
        <Button
          variant="outline"
          size="lg"
          className="h-10 w-full text-base"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? text.loggingOut : text.logout}
        </Button>
      </div>
    </AuthCard>
  );
}
