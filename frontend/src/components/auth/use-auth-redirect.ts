"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { safeNextPath } from "@/lib/auth-forms";

/**
 * Для страниц входа и регистрации: куда перейти после успеха.
 * Если человек уже вошёл, сразу отправляет его дальше.
 */
export function useAuthRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status } = useAuth();
  const rawNext = searchParams.get("next");
  const nextPath = safeNextPath(rawNext);

  useEffect(() => {
    if (status === "authenticated") router.replace(nextPath);
  }, [status, nextPath, router]);

  /** Ссылка на соседнюю страницу (вход ↔ регистрация) с сохранением `next`. */
  const withNext = (path: string) =>
    rawNext ? `${path}?next=${encodeURIComponent(nextPath)}` : path;

  return { withNext };
}
