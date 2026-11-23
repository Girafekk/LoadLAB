"use client";

import { useEffect, useState } from "react";

import { fetchHealth } from "@/lib/api";

import { backendStatusContent as TEXT } from "@/content/layout";

// «online» — работают и backend, и база; «databaseUnavailable» — backend отвечает,
// но база недоступна: войти и сохранить данные не получится, и зелёный цвет соврёт.
type Status = "checking" | "online" | "databaseUnavailable" | "offline";

const DOT_CLASSES: Record<Status, string> = {
  checking: "bg-muted-foreground/50",
  online: "bg-success",
  databaseUnavailable: "bg-warning",
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
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function check(attempt = 0) {
      try {
        const health = await fetchHealth(controller.signal);
        setVersion(health.version);
        if (health.status !== "ok") setStatus("offline");
        else setStatus(health.database === "ok" ? "online" : "databaseUnavailable");
      } catch {
        if (controller.signal.aborted) return;
        if (attempt === 0) {
          timer = setTimeout(() => void check(1), 1000);
          return;
        }
        setStatus("offline");
      }
    }

    void check();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <p className="flex items-center gap-2" role="status">
      <span className={`size-2 rounded-full ${DOT_CLASSES[status]}`} aria-hidden="true" />
      <span>
        {TEXT[status]}
        {status === "online" && version ? ` · API v${version}` : ""}
      </span>
    </p>
  );
}
