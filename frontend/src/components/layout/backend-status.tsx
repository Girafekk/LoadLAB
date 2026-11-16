"use client";

import { useEffect, useState } from "react";

import { fetchHealth } from "@/lib/api";

type Status = "checking" | "online" | "offline";

const LABELS: Record<Status, string> = {
  checking: "Проверяем сервер…",
  online: "Сервер работает",
  offline: "Сервер недоступен",
};

const DOT_CLASSES: Record<Status, string> = {
  checking: "bg-muted-foreground/50",
  online: "bg-success",
  offline: "bg-destructive",
};

/**
 * Индикатор связи с backend: один раз при загрузке страницы
 * запрашивает GET /api/v1/health и показывает результат.
 */
export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((health) => {
        setVersion(health.version);
        setStatus(health.status === "ok" ? "online" : "offline");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <p className="flex items-center gap-2" role="status">
      <span className={`size-2 rounded-full ${DOT_CLASSES[status]}`} aria-hidden="true" />
      <span>
        {LABELS[status]}
        {status === "online" && version ? ` · API v${version}` : ""}
      </span>
    </p>
  );
}
