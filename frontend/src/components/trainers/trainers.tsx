"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AiTeacherPanel } from "@/components/learn/ai-teacher-panel";
import { AnalysisTrainer } from "@/components/trainers/analysis-trainer";
import { HttpTrainer } from "@/components/trainers/http-trainer";
import { LinuxTrainer } from "@/components/trainers/linux-trainer";
import { SqlTrainer } from "@/components/trainers/sql-trainer";
import { buttonVariants } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { fetchCourse } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "http" | "sql" | "linux" | "analysis" | "ai";
const TABS: readonly Tab[] = ["http", "sql", "linux", "analysis", "ai"];

export function Trainers() {
  const { status, user, version } = useAuth();
  const owner = user ? `${user.id}:${version}` : "guest";
  const [tab, setTab] = useState<Tab>("http");
  const [aiLessonId, setAiLessonId] = useState<number | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    const controller = new AbortController();
    fetchCourse(controller.signal)
      .then((course) => {
        const lesson = course.modules.flatMap((module) => module.lessons)[0];
        setAiLessonId(lesson?.id ?? null);
      })
      .catch(() => setAiLessonId(null));
    return () => controller.abort();
  }, [status, owner]);

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  }

  if (status !== "authenticated") {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">{t.login}</p>
        <Link
          href="/login?next=%2Ftrainers"
          className={cn(buttonVariants({ size: "lg" }), "mt-4 px-4")}
        >
          Войти
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label={t.title}>
        {TABS.map((item, index) => (
          <button
            key={item}
            id={`trainer-tab-${item}`}
            type="button"
            role="tab"
            aria-selected={tab === item}
            aria-controls={`trainer-panel-${item}`}
            tabIndex={tab === item ? 0 : -1}
            onClick={() => setTab(item)}
            onKeyDown={(event) => {
              if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const nextIndex =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? TABS.length - 1
                    : (index + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
              const next = TABS[nextIndex];
              setTab(next);
              document.getElementById(`trainer-tab-${next}`)?.focus();
            }}
            className={cn(
              "rounded-lg px-3 py-2 text-sm font-medium",
              tab === item ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-surface",
            )}
          >
            {t.tabs[item]}
          </button>
        ))}
      </div>
      <div className="mt-6">
        <div
          role="tabpanel"
          id="trainer-panel-http"
          aria-labelledby="trainer-tab-http"
          tabIndex={0}
          hidden={tab !== "http"}
        >
          {tab === "http" ? <HttpTrainer key={`http-${owner}`} /> : null}
        </div>
        <div
          role="tabpanel"
          id="trainer-panel-sql"
          aria-labelledby="trainer-tab-sql"
          tabIndex={0}
          hidden={tab !== "sql"}
        >
          {tab === "sql" ? <SqlTrainer key={`sql-${owner}`} /> : null}
        </div>
        <div
          role="tabpanel"
          id="trainer-panel-linux"
          aria-labelledby="trainer-tab-linux"
          tabIndex={0}
          hidden={tab !== "linux"}
        >
          {tab === "linux" ? <LinuxTrainer key={`linux-${owner}`} /> : null}
        </div>
        <div
          role="tabpanel"
          id="trainer-panel-analysis"
          aria-labelledby="trainer-tab-analysis"
          tabIndex={0}
          hidden={tab !== "analysis"}
        >
          {tab === "analysis" ? <AnalysisTrainer key={`analysis-${owner}`} /> : null}
        </div>
        <div
          role="tabpanel"
          id="trainer-panel-ai"
          aria-labelledby="trainer-tab-ai"
          tabIndex={0}
          hidden={tab !== "ai"}
        >
          {tab === "ai" ? (
            aiLessonId ? (
              <AiTeacherPanel key={`ai-${aiLessonId}-${owner}`} lessonId={aiLessonId} />
            ) : (
              <p className="text-sm text-muted-foreground">{t.aiUnavailable}</p>
            )
          ) : null}
        </div>
      </div>
      <div className="mt-8 rounded-xl border bg-card p-4">
        <p className="text-sm font-medium">Проверить конфигурацию перед JMeter-прогоном</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Симулятор проверит потоки, ramp-up, think time и путь запроса.
        </p>
        <Link href="/jmeter-simulator" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-3")}>
          Открыть JMeter-симулятор
        </Link>
      </div>
    </div>
  );
}
