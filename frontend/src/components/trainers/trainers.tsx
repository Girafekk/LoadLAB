"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AnalysisTrainer } from "@/components/trainers/analysis-trainer";
import { HttpTrainer } from "@/components/trainers/http-trainer";
import { LinuxTrainer } from "@/components/trainers/linux-trainer";
import { SqlTrainer } from "@/components/trainers/sql-trainer";
import { buttonVariants } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { cn } from "@/lib/utils";

type Tab = "http" | "sql" | "linux" | "analysis";

export function Trainers() {
  const { status } = useAuth();
  const [tab, setTab] = useState<Tab>("http");

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
        {(["http", "sql", "linux", "analysis"] as const).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={tab === item}
            onClick={() => setTab(item)}
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
        {tab === "http" ? <HttpTrainer /> : null}
        {tab === "sql" ? <SqlTrainer /> : null}
        {tab === "linux" ? <LinuxTrainer /> : null}
        {tab === "analysis" ? <AnalysisTrainer /> : null}
      </div>
    </div>
  );
}
