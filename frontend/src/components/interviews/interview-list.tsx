"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { interviewsContent as t } from "@/content/interviews";
import { fetchInterviewLibrary } from "@/lib/api";
import type { InterviewLibrarySource } from "@/lib/interview-types";
import { cn } from "@/lib/utils";

export function InterviewList() {
  const [sources, setSources] = useState<InterviewLibrarySource[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    fetchInterviewLibrary(controller.signal)
      .then((data) => {
        setSources(data);
        setStatus("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("error");
      });
    return () => controller.abort();
  }, []);

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  }
  if (status === "error") {
    return <p className="text-sm text-destructive">{t.error}</p>;
  }
  if (sources.length === 0) {
    return <p className="text-sm text-muted-foreground">{t.empty}</p>;
  }

  return (
    <ul className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-2">
      {sources.map((source) => (
        <li key={source.id} className="flex min-w-0 flex-col rounded-xl border bg-card p-5">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <h2 className="min-w-0 text-base font-semibold break-all">{source.filename}</h2>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <Badge variant="secondary" className="shrink-0">
                {t.questions(source.questions_count)}
              </Badge>
              <span className="text-[11px] text-muted-foreground">
                {t.categories[source.category] ?? source.category}
              </span>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {t.date}: {new Date(source.created_at).toLocaleDateString("ru-RU")}
          </p>
          <Link
            href={`/interviews/${source.id}`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-4 self-start")}
          >
            {t.open}
          </Link>
        </li>
      ))}
    </ul>
  );
}
