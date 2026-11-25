"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { interviewsContent as t } from "@/content/interviews";
import { fetchInterviewLibraryItem } from "@/lib/api";
import type { InterviewLibraryDetail } from "@/lib/interview-types";
import { cn } from "@/lib/utils";

export function InterviewDetail({ sourceId }: { sourceId: number | null }) {
  const [detail, setDetail] = useState<InterviewLibraryDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "notfound" | "error">(
    sourceId === null ? "notfound" : "loading",
  );

  useEffect(() => {
    if (sourceId === null) return;
    const controller = new AbortController();
    fetchInterviewLibraryItem(sourceId, controller.signal)
      .then((data) => {
        setDetail(data);
        setStatus("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("notfound");
      });
    return () => controller.abort();
  }, [sourceId]);

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loadingOne}</p>;
  }
  if (status !== "ready" || !detail) {
    return (
      <div>
        <p className="text-sm text-muted-foreground">
          {status === "notfound" ? t.notFound : t.error}
        </p>
        <Link href="/interviews" className={cn(buttonVariants({ variant: "outline" }), "mt-4")}>
          {t.back}
        </Link>
      </div>
    );
  }

  return (
    <article>
      <Link href="/interviews" className="text-sm font-medium text-brand underline-offset-4 hover:underline">
        {t.back}
      </Link>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight break-words [overflow-wrap:anywhere] sm:text-3xl">
            {detail.filename}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t.categories[detail.category] ?? detail.category} · {t.questions(detail.questions_count)}
          </p>
        </div>
        <Badge variant="secondary">{t.questions(detail.questions_count)}</Badge>
      </div>

      <ol className="mt-6 space-y-3">
        {detail.questions.map((question, index) => (
          <li key={question.id} className="rounded-xl border bg-card p-4">
            <details className="group">
              <summary className="cursor-pointer list-none rounded-lg px-1 py-1 hover:bg-muted/60">
                <span className="flex items-start gap-3">
                  <span className="text-sm font-medium text-muted-foreground">{index + 1}.</span>
                  <span className="min-w-0 flex-1 font-medium break-words">{question.text}</span>
                </span>
                <span className="mt-2 flex flex-wrap gap-2 pl-6">
                  {question.topic ? (<Badge variant="outline" className="max-w-full whitespace-normal break-words">{question.topic}</Badge>) : null}
                  <Badge variant="outline">{question.difficulty_label}</Badge>
                  <Badge variant="outline">{question.level_label}</Badge><span className="ml-auto text-xs font-medium text-brand group-open:hidden">Показать ответ ↓</span><span className="ml-auto hidden text-xs font-medium text-brand group-open:inline">Скрыть ответ ↑</span>
                </span>
              </summary>
              <div className="mt-4 space-y-3 border-t pt-4 pl-6 text-sm leading-relaxed">
                <div>
                  <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t.answer}
                  </p>
                  <p className="whitespace-pre-line break-words">
                    {question.reference_answer ?? t.noAnswer}
                  </p>
                </div>
                {question.answer_criteria ? (
                  <div>
                    <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      {t.criteria}
                    </p>
                    <p className="whitespace-pre-line break-words text-muted-foreground">
                      {question.answer_criteria}
                    </p>
                  </div>
                ) : null}
              </div>
            </details>
          </li>
        ))}
      </ol>
    </article>
  );
}
