"use client";

import type { ReactNode } from "react";

import { useAuth } from "@/components/auth/auth-provider";

/**
 * Пересоздаёт экран при смене ученика или версии сессии.
 * Старые формы не доживают до нового владельца cookie и не могут
 * отправить черновик прошлого аккаунта.
 */
export function SessionBoundary({ children }: { children: ReactNode }) {
  const { status, user, version } = useAuth();
  if (status === "loading") return <>{children}</>;
  return <div key={`${user?.id ?? "guest"}:${version}`}>{children}</div>;
}
