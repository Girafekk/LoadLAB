"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { AiTeacherPanel } from "@/components/learn/ai-teacher-panel";
import { LessonQuiz } from "@/components/learn/lesson-quiz";
import { LessonTools } from "@/components/learn/lesson-tools";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { learnContent as t } from "@/content/learn";
import { ApiError, fetchCourse, fetchLesson, setLessonCompleted } from "@/lib/api";
import type { CourseOverview, LessonBlock, LessonRead } from "@/lib/learn-types";
import { cn } from "@/lib/utils";

type Status = "loading" | "ready" | "guest" | "notFound" | "error";

type Neighbour = {
  id: number;
  title: string;
};

function textOf(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function listOf(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

/** Текст блока выводится как текст: HTML из базы не исполняется. */
function Definitions({ text }: { text: string }) {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines[0]?.startsWith("Основные понятия")) lines.shift();
  return (
    <section aria-label="Основные понятия" className="rounded-xl border bg-surface/60 p-5">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        Основные понятия
      </p>
      <dl className="mt-3 space-y-4">
        {lines.map((line, index) => {
          const parts = line.split(/\s+—\s+/, 2);
          if (parts.length === 2) {
            return (
              <div key={`${index}-${parts[0]}`}>
                <dt className="font-semibold text-foreground">{parts[0]}</dt>
                <dd className="mt-1 leading-relaxed text-muted-foreground">{parts[1]}</dd>
              </div>
            );
          }
          return (
            <dd key={`${index}-${line}`} className="leading-relaxed text-muted-foreground">
              {line}
            </dd>
          );
        })}
      </dl>
    </section>
  );
}

function BlockView({ block }: { block: LessonBlock }) {
  const { type, content } = block;

  switch (type) {
    case "heading":
      return <h2 className="text-xl font-semibold text-balance">{textOf(content.text)}</h2>;
    case "text": {
      const value = textOf(content.text);
      if (value.startsWith("Основные понятия")) return <Definitions text={value} />;
      return (
        <p className="text-base leading-relaxed whitespace-pre-line">{value}</p>
      );
    }
    case "callout":
      return (
        <aside className="rounded-lg border-l-4 border-brand bg-surface px-4 py-3 text-sm leading-relaxed whitespace-pre-line">
          {textOf(content.text)}
        </aside>
      );
    case "list": {
      const items = listOf(content.items);
      const ordered = content.ordered === true;
      return ordered ? (
        <ol className="list-decimal space-y-1.5 pl-6 text-base leading-relaxed">
          {items.map((item, index) => (
            <li key={`${block.position}-${index}`}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul className="list-disc space-y-1.5 pl-6 text-base leading-relaxed">
          {items.map((item, index) => (
            <li key={`${block.position}-${index}`}>{item}</li>
          ))}
        </ul>
      );
    }
    case "code":
      return (
        <figure>
          <figcaption className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {t.lessonCode(textOf(content.language))}
          </figcaption>
          <pre className="overflow-x-auto rounded-lg border bg-muted p-4 text-sm leading-relaxed">
            <code className="font-mono">{textOf(content.code)}</code>
          </pre>
        </figure>
      );
    case "table": {
      const headers = listOf(content.headers);
      const rows = Array.isArray(content.rows)
        ? content.rows.filter((row): row is unknown[] => Array.isArray(row))
        : [];
      return (
        <figure>
          <figcaption className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {t.lessonTable}
          </figcaption>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-muted">
                <tr>
                  {headers.map((header) => (
                    <th key={header} scope="col" className="px-4 py-2 font-semibold">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="border-t">
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} className="px-4 py-2 align-top">
                        {textOf(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </figure>
      );
    }
    case "image": {
      const src = textOf(content.src);
      const alt = textOf(content.alt) || t.lesson;
      const caption = textOf(content.caption);
      if (!src) return null;
      return (
        <figure>
          <Image
            src={src}
            alt={alt}
            width={640}
            height={144}
            unoptimized
            className="h-auto w-full rounded-lg border"
          />
          {caption ? (
            <figcaption className="mt-2 text-sm text-muted-foreground">{caption}</figcaption>
          ) : null}
        </figure>
      );
    }
    default:
      return <p className="text-sm text-muted-foreground">{t.unavailableBlock}</p>;
  }
}

function Message({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center sm:px-6">
      <h1 className="text-2xl font-semibold text-balance">{title}</h1>
      {description ? (
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
      <p className="mt-8 text-sm">
        <Link href="/learn" className="font-medium text-brand underline-offset-4 hover:underline">
          {t.back}
        </Link>
      </p>
    </div>
  );
}

export function LessonView({ lessonId }: { lessonId: number | null }) {
  const { user, version } = useAuth();
  // Ключ включает урок, ученика и версию сессии: Next сохраняет состояние
  // клиентских компонентов при навигации, поэтому без ключа новый урок или
  // новый ученик увидел бы результат и прогресс предыдущего.
  return (
    <LessonViewContent
      key={`lesson-${lessonId ?? "none"}-${user?.id ?? "guest"}-${version}`}
      lessonId={lessonId}
    />
  );
}

function LessonViewContent({ lessonId }: { lessonId: number | null }) {
  const { status: authStatus, clearSession, user, version } = useAuth();
  const [status, setStatus] = useState<Status>("loading");
  const [lesson, setLesson] = useState<LessonRead | null>(null);
  const [course, setCourse] = useState<CourseOverview | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [navError, setNavError] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  // Номера запросов каталога: применяем только ответ на последний запрос.
  const catalogRequestId = useRef(0);

  useEffect(() => {
    // Гостю урок не запрашиваем вовсе: приглашение войти показывается по
    // состоянию авторизации, без лишнего запроса и без мигания.
    if (authStatus !== "authenticated" || lessonId === null) return;

    const controller = new AbortController();
    const catalogId = ++catalogRequestId.current;

    // Урок и каталог загружаются независимо: сбой каталога не должен
    // скрывать уже загруженный урок, навигация просто останется пустой.
    fetchLesson(lessonId, controller.signal)
      .then((lessonData) => {
        setLesson(lessonData);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          // Сессия истекла: сообщаем об этом общему провайдеру, иначе страница
          // входа увидит «authenticated» и вернёт человека к уроку снова.
          clearSession(version);
          setStatus("guest");
        } else if (error instanceof ApiError && error.status === 404) {
          setStatus("notFound");
        } else {
          setStatus("error");
        }
      });

    fetchCourse(controller.signal)
      .then((courseData) => {
        if (catalogRequestId.current === catalogId) {
          setCourse(courseData);
          setNavError(false);
        }
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        if (catalogRequestId.current === catalogId) setNavError(true);
      });

    return () => controller.abort();
  }, [authStatus, lessonId, reloadToken, clearSession, version]);

  if (authStatus === "loading") {
    return (
      <p className="mx-auto max-w-2xl px-4 py-16 text-sm text-muted-foreground sm:px-6">
        {t.loadingLesson}
      </p>
    );
  }

  if (authStatus === "anonymous" || status === "guest") {
    return (
      <Message
        title={t.login}
        description={t.loginPrompt}
        action={
          <Link
            href={`/login?next=${encodeURIComponent(`/learn/lessons/${lessonId}`)}`}
            className={cn(buttonVariants({ size: "lg" }), "px-4")}
          >
            {t.loginAction}
          </Link>
        }
      />
    );
  }

  if (lessonId === null || status === "notFound") {
    return <Message title={t.lessonNotFound} />;
  }

  if (status === "loading") {
    return (
      <p className="mx-auto max-w-2xl px-4 py-16 text-sm text-muted-foreground sm:px-6">
        {t.loadingLesson}
      </p>
    );
  }

  if (status === "error" || lesson === null) {
    return (
      <Message
        title={t.lessonLoadError}
        action={
          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              setStatus("loading");
              setReloadToken((value) => value + 1);
            }}
          >
            {t.retry}
          </Button>
        }
      />
    );
  }

  const published = course
    ? course.modules.flatMap((module) =>
        module.lessons.map((item) => ({
          id: item.id,
          title: item.title,
          modulePosition: module.position,
        })),
      )
    : [];
  const index = published.findIndex((item) => item.id === lessonId);
  const current = index >= 0 ? published[index] : null;
  const previous: Neighbour | null = index > 0 ? published[index - 1] : null;
  const next: Neighbour | null = index >= 0 && index < published.length - 1 ? published[index + 1] : null;
  const progress = course?.progress ?? null;

  async function toggleCompleted() {
    if (lesson === null || saving) return;
    setSaving(true);
    setSaveError(null);

    try {
      await setLessonCompleted(lesson.id, !lesson.is_completed);
    } catch (error) {
      // Истёкшая сессия: предлагаем войти заново, а не «повторить сохранение».
      if (error instanceof ApiError && error.status === 401) {
        clearSession(version);
        setStatus("guest");
      } else if (error instanceof ApiError && error.status === 409) {
        // В другой вкладке вошли другим учеником: страница будет пересоздана
        // после обновления владельца сессии.
        setSaveError(t.sessionChanged);
      } else {
        setSaveError(t.saveError);
      }
      setSaving(false);
      return;
    }

    setLesson({ ...lesson, is_completed: !lesson.is_completed });
    setSaving(false);
    setRefreshError(false);

    // Отметка уже сохранена. Сбой или устаревший ответ каталога не выдаём
    // за ошибку сохранения: счётчик обновится, когда придёт актуальный ответ.
    const catalogId = ++catalogRequestId.current;
    fetchCourse()
      .then((courseData) => {
        if (catalogRequestId.current === catalogId) setCourse(courseData);
      })
      .catch(() => {
        if (catalogRequestId.current === catalogId) setRefreshError(true);
      });
  }

  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {current
          ? `${t.week(current.modulePosition)} · ${t.lesson}`
          : t.lesson}
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {lesson.title}
      </h1>
      {lesson.summary ? (
        <p className="mt-3 text-base leading-relaxed text-muted-foreground">{lesson.summary}</p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{t.duration(lesson.estimated_minutes)}</Badge>
        <Badge variant={lesson.is_completed ? "default" : "outline"}>
          {lesson.is_completed ? t.completed : t.incomplete}
        </Badge>
        {progress ? (
          <span className="text-xs text-muted-foreground">
            {t.progressCount(progress.completed_lessons, progress.total_lessons)}
          </span>
        ) : null}
      </div>

      {lesson.blocks.length === 0 ? (
        <p className="mt-8 text-sm text-muted-foreground">{t.lessonEmpty}</p>
      ) : (
        <div className="mt-8 space-y-6">
          {lesson.blocks.map((block) => (
            <BlockView key={block.position} block={block} />
          ))}
        </div>
      )}

      {/* Ключ по ученику: при смене пользователя квиз и материалы начинаются заново. */}
      <LessonQuiz key={`quiz-${lessonId}-${user?.id ?? "guest"}`} lessonId={lessonId} />
      <LessonTools key={`tools-${lessonId}-${user?.id ?? "guest"}`} lessonId={lessonId} />
      <AiTeacherPanel key={`ai-${lessonId}-${user?.id ?? "guest"}`} lessonId={lessonId} />

      <div className="mt-10 flex flex-wrap items-center gap-3">
        <Button size="lg" className="px-4" onClick={toggleCompleted} disabled={saving}>
          {lesson.is_completed ? t.unmark : t.mark}
        </Button>
        {saving ? <span className="text-sm text-muted-foreground">{t.saving}</span> : null}
      </div>
      {saveError ? (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {saveError}
        </p>
      ) : null}
      {refreshError ? (
        <p role="status" className="mt-3 text-sm text-muted-foreground">
          {t.refreshError}
        </p>
      ) : null}
      {navError ? (
        <p role="status" className="mt-3 text-sm text-muted-foreground">
          {t.navError}
        </p>
      ) : null}

      <nav
        aria-label={t.lessonNav}
        className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t pt-6"
      >
        {previous ? (
          <Link href={`/learn/lessons/${previous.id}`} className="text-sm font-medium text-brand hover:underline">
            {t.previousLesson}
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link href={`/learn/lessons/${next.id}`} className="text-sm font-medium text-brand hover:underline">
            {t.nextLesson}
          </Link>
        ) : (
          <span />
        )}
      </nav>

      <p className="mt-8 text-sm">
        <Link
          href="/learn"
          className="font-medium text-brand underline-offset-4 hover:underline"
        >
          {t.back}
        </Link>
      </p>
    </article>
  );
}
