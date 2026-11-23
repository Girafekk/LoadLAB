"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { learnContent as t } from "@/content/learn";
import { fetchCourse } from "@/lib/api";
import type { CourseOverview, LessonBrief } from "@/lib/learn-types";
import { cn } from "@/lib/utils";

type AvailableLesson = LessonBrief & {
  moduleTitle: string;
  modulePosition: number;
};

type Status = "loading" | "ready" | "error";

/**
 * Прогресс ученика и список опубликованных уроков.
 * Гость видит программу и приглашение войти, вошедший — свои отметки.
 */
export function CourseProgress() {
  const { status: authStatus, user, version } = useAuth();
  const [course, setCourse] = useState<CourseOverview | null>(null);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [reloadToken, setReloadToken] = useState(0);
  // Номер последнего запроса: ответ на устаревший запрос не должен
  // перезаписать более свежие данные (например, после выхода).
  const requestId = useRef(0);
  const ownerKey = `${authStatus}:${user?.id ?? 0}:${version}`;

  useEffect(() => {
    if (authStatus === "loading") return;
    const id = ++requestId.current;
    const controller = new AbortController();
    fetchCourse(controller.signal, authStatus === "authenticated")
      .then((data) => {
        if (requestId.current !== id) return;
        setCourse(data);
        setLoadedFor(ownerKey);
        setStatus("ready");
      })
      .catch(() => {
        if (requestId.current === id && !controller.signal.aborted) setStatus("error");
      });
    return () => controller.abort();
  }, [authStatus, ownerKey, reloadToken]);

  function retry() {
    setStatus("loading");
    setReloadToken((value) => value + 1);
  }

  if (authStatus === "loading") {
    return (
      <p className="mt-8 rounded-xl border bg-card px-5 py-6 text-sm text-muted-foreground">
        {t.loadingProgram}
      </p>
    );
  }

  // Ошибку показываем раньше ожидания: иначе при первом же сбое ученик
  // навсегда видит «Загружаем программу…» и не получает кнопку «Повторить».
  if (status === "error") {
    return (
      <div className="mt-8 rounded-xl border bg-card px-5 py-6">
        <p className="text-sm text-muted-foreground">{t.programLoadError}</p>
        <Button variant="outline" size="lg" className="mt-4" onClick={retry}>
          {t.retry}
        </Button>
      </div>
    );
  }

  if (status === "loading" || loadedFor !== ownerKey || course === null) {
    return (
      <p className="mt-8 rounded-xl border bg-card px-5 py-6 text-sm text-muted-foreground">
        {t.loadingProgram}
      </p>
    );
  }

  // Пока данные относятся к прошлому состоянию входа, личный прогресс
  // не показываем: после выхода старые проценты видны не должны.

  const progress = course.progress;
  const lessons: AvailableLesson[] = course.modules.flatMap((module) =>
    module.lessons.map((lesson) => ({
      ...lesson,
      moduleTitle: module.title,
      modulePosition: module.position,
    })),
  );

  return (
    <section
      aria-labelledby="course-progress-heading"
      className="mt-8 rounded-xl border bg-card p-5 sm:p-6"
    >
      <h2 id="course-progress-heading" className="text-lg font-semibold">
        {t.progress}
      </h2>

      {progress ? (
        <>
          <div className="mt-2 flex items-baseline justify-between gap-2">
            <p className="text-sm text-muted-foreground">
              {t.progressCount(progress.completed_lessons, progress.total_lessons)}
            </p>
            <span className="text-sm font-semibold tabular-nums">
              {t.progressPercent(progress.percent)}
            </span>
          </div>
          <div
            role="progressbar"
            aria-label={t.progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress.percent}
            className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted"
          >
            <div className="h-full rounded-full bg-brand" style={{ width: `${progress.percent}%` }} />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {progress.total_lessons === 0 ? (
              <p className="text-sm text-muted-foreground">{t.progressEmpty}</p>
            ) : progress.next_lesson_id !== null ? (
              <Link
                href={`/learn/lessons/${progress.next_lesson_id}`}
                className={cn(buttonVariants({ size: "lg" }), "px-4")}
              >
                {t.continue}
              </Link>
            ) : (
              <p className="text-sm text-muted-foreground">{t.progressDone}</p>
            )}
            {progress.last_completed_lesson_id !== null ? (
              <Link
                href={`/learn/lessons/${progress.last_completed_lesson_id}`}
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "max-w-full whitespace-normal px-4 text-balance",
                )}
              >
                {t.review}
              </Link>
            ) : null}
          </div>
        </>
      ) : (
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {t.loginPrompt}{" "}
          <Link
            href="/login?next=%2Flearn"
            className="font-medium text-brand underline-offset-4 hover:underline"
          >
            {t.loginAction}
          </Link>
        </p>
      )}

      <h3 className="mt-8 text-base font-semibold">{t.availableHeading}</h3>
      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{t.availableIntro}</p>

      {lessons.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{t.progressEmpty}</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {lessons.map((lesson) => (
            <li key={lesson.id}>
              <Link
                href={`/learn/lessons/${lesson.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-input bg-background px-4 py-3 transition-colors hover:bg-muted"
              >
                <span className="min-w-0">
                  <span className="block text-xs text-muted-foreground">
                    {t.week(lesson.modulePosition)} · {lesson.moduleTitle}
                  </span>
                  <span className="mt-0.5 block text-sm font-medium">{lesson.title}</span>
                </span>
                <span className="flex items-center gap-2">
                  <Badge variant="secondary">{t.duration(lesson.estimated_minutes)}</Badge>
                  {progress ? (
                    <Badge variant={lesson.is_completed ? "default" : "outline"}>
                      {lesson.is_completed ? t.completed : t.incomplete}
                    </Badge>
                  ) : (
                    <Badge variant="outline">{t.available}</Badge>
                  )}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
