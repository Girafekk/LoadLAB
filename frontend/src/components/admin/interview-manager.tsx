"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { interviewContent as t } from "@/content/interview";
import {
  analyzeInterviewSource,
  fetchInterviewLessons,
  fetchInterviewQuestionPage,
  fetchInterviewReport,
  fetchInterviewSources,
  approveAllInterviewQuestions,
  deduplicateInterviewQuestions,
  generateInterviewAnswers,
  updateInterviewQuestion,
  uploadInterviewSource,
  ApiError,
} from "@/lib/api";
import type {
  InterviewQuestion,
  InterviewReport,
  InterviewSource,
  LessonOption,
} from "@/lib/interview-types";

type Filter = "all" | "proposed" | "approved" | "rejected";

export function InterviewManager() {
  const [sources, setSources] = useState<InterviewSource[]>([]);
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [lessons, setLessons] = useState<LessonOption[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [allowExternal, setAllowExternal] = useState(false);
  const [allowAnswersExternal, setAllowAnswersExternal] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchInterviewSources(controller.signal),
      fetchInterviewReport(controller.signal),
      fetchInterviewLessons(controller.signal),
    ])
      .then(([nextSources, nextReport, nextLessons]) => {
        setSources(nextSources);
        setReport(nextReport);
        setLessons(nextLessons);
      })
      .catch(() => setStatus("error"));
    return () => controller.abort();
  }, [reloadToken]);

  useEffect(() => {
    const controller = new AbortController();
    fetchInterviewQuestionPage(
      filter === "all" ? undefined : filter,
      page * 25,
      25,
      controller.signal,
    )
      .then((data) => {
        setQuestions(data.items);
        setTotal(data.total);
        setStatus("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("error");
      });
    return () => controller.abort();
  }, [filter, page, reloadToken]);

  const pageCount = Math.max(1, Math.ceil(total / 25));
  const shownQuestions = questions;

  async function upload(file: File | undefined) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("Файл больше 10 МБ. Уменьшите файл или загрузите по частям.");
      return;
    }
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const source = await uploadInterviewSource(file);
      if (source.status === "error") {
        setError(source.error ?? t.uploadError);
      } else {
        setMessage(t.uploaded);
      }
      setReloadToken((value) => value + 1);
      setAllowExternal(false);
      setAllowAnswersExternal(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t.uploadError);
    } finally {
      setUploading(false);
    }
  }

  async function analyze(source: InterviewSource) {
    setBusyId(source.id);
    setError(null);
    const consent = allowExternal;
    setAllowExternal(false);
    try {
      const result = await analyzeInterviewSource(source.id, consent);
      setMessage(t.analyzeResult(result.questions_created, result.duplicates));
      setReloadToken((value) => value + 1);
    } catch {
      setError(t.uploadError);
    } finally {
      setBusyId(null);
    }
  }

  async function patch(question: InterviewQuestion, data: Partial<InterviewQuestion>) {
    setBusyId(question.id);
    setError(null);
    try {
      const updated = await updateInterviewQuestion(question.id, data);
      setQuestions((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setReport(await fetchInterviewReport());
    } catch {
      setError(t.approveError);
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll() {
    setBusyId(-1);
    setError(null);
    try {
      const result = await approveAllInterviewQuestions();
      setMessage(t.approvedCount(result.approved));
      setReloadToken((value) => value + 1);
    } catch {
      setError(t.approveError);
    } finally {
      setBusyId(null);
    }
  }

  async function deduplicate() {
    setBusyId(-2);
    setError(null);
    try {
      const result = await deduplicateInterviewQuestions();
      setMessage(t.deduplicated(result.removed));
      setReloadToken((value) => value + 1);
    } catch {
      setError(t.approveError);
    } finally {
      setBusyId(null);
    }
  }

  async function generateAnswers() {
    setBusyId(-3);
    setError(null);
    const consent = allowAnswersExternal;
    setAllowAnswersExternal(false);
    try {
      const result = await generateInterviewAnswers(consent);
      setMessage(t.answersGenerated(result.generated));
      setReloadToken((value) => value + 1);
    } catch {
      setError(t.approveError);
    } finally {
      setBusyId(null);
    }
  }

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  }
  if (status === "error") {
    return (
      <div className="rounded-xl border bg-card p-5">
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button className="mt-3" variant="outline" onClick={() => setReloadToken((v) => v + 1)}>
          {t.retry}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border bg-card p-5">
        <p className="max-w-3xl text-sm text-muted-foreground">{t.intro}</p>
        <label className="mt-4 inline-flex cursor-pointer flex-wrap items-center gap-3 rounded-lg focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
          <span className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            {uploading ? t.uploading : t.upload}
          </span>
          <input
            type="file"
            accept=".txt,.pdf,.doc,.docx,.png,.jpg,.jpeg"
            className="sr-only"
            disabled={uploading}
            onChange={(event) => {
              void upload(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <span className="text-xs text-muted-foreground">
            TXT, PDF, DOC, DOCX, PNG, JPG · до 10 МБ
          </span>
        </label>
        <label className="mt-3 flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={allowExternal}
            onChange={(event) => setAllowExternal(event.target.checked)}
            className="mt-1"
          />
          <span>
            {t.allowExternal}
            <span className="block text-xs text-muted-foreground">{t.allowExternalHint}</span>
          </span>
        </label>
        <label className="mt-2 flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={allowAnswersExternal}
            onChange={(event) => setAllowAnswersExternal(event.target.checked)}
            className="mt-1"
          />
          <span>
            {t.allowAnswersExternal}
            <span className="block text-xs text-muted-foreground">{t.allowExternalHint}</span>
          </span>
        </label>
        {message ? (
          <p role="status" className="mt-3 text-sm text-brand">
            {message}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.sources}</h2>
        {sources.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">{t.noSources}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {sources.map((source) => (
              <li
                key={source.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm"
              >
                <span className="min-w-0 break-all">
                  {source.filename}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {source.questions_count} ·{" "}
                    {({ extracted: "извлечён", analyzed: "разобран", error: "ошибка" } as Record<string, string>)[
                      source.status
                    ] ?? source.status}
                  </span>
                  {source.error ? (
                    <span className="block text-xs text-destructive">{source.error}</span>
                  ) : null}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busyId === source.id || source.status === "error"}
                  onClick={() => void analyze(source)}
                >
                  {busyId === source.id ? t.analyzing : t.analyze}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {report ? (
        <section className="rounded-xl border bg-card p-5">
          <h2 className="text-lg font-semibold">{t.report}</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-surface p-3">
              <p className="text-xs text-muted-foreground">{t.total}</p>
              <p className="text-2xl font-semibold">{report.total_questions}</p>
            </div>
            <div className="rounded-lg bg-surface p-3">
              <p className="text-xs text-muted-foreground">{t.approved}</p>
              <p className="text-2xl font-semibold">{report.approved}</p>
            </div>
            <div className="rounded-lg bg-surface p-3">
              <p className="text-xs text-muted-foreground">{t.gaps}</p>
              <p className="text-2xl font-semibold">{report.gaps.length}</p>
            </div>
            <div className="rounded-lg bg-surface p-3">
              <p className="text-xs text-muted-foreground">{t.answersReady}</p>
              <p className="text-2xl font-semibold">
                {report.answers_ready}/{report.total_questions}
              </p>
              <p className="text-xs text-muted-foreground">
                {t.answersMissing}: {report.answers_missing}; {t.lesson}:{" "}
                {report.questions_without_lesson}
              </p>
            </div>
          </div>
          {report.by_topic.length > 0 ? (
            <div className="mt-4 overflow-x-auto" tabIndex={0}>
              <table className="w-full min-w-[420px] text-left text-sm">
                <thead className="text-xs text-muted-foreground">
                  <tr>
                    <th className="py-1">{t.topic}</th>
                    <th className="py-1">{t.questions}</th>
                    <th className="py-1">{t.lesson}</th>
                  </tr>
                </thead>
                <tbody>
                  {report.by_topic.map((row) => (
                    <tr key={row.topic} className="border-t">
                      <td className="py-1 break-words">{row.topic}</td>
                      <td className="py-1">{row.questions}</td>
                      <td className="py-1">{row.lessons}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <h3 className="mt-4 text-sm font-semibold">{t.suggestions}</h3>
          {report.suggestions.length === 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">{t.noGaps}</p>
          ) : (
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {report.suggestions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <section className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{t.questions}</h2>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={busyId === -1}
              onClick={() => void approveAll()}
            >
              {t.approveAll}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={busyId === -2}
              onClick={() => void deduplicate()}
            >
              {t.deduplicate}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={busyId === -3}
              onClick={() => void generateAnswers()}
            >
              {t.generateAnswers}
            </Button>
            {(["all", "proposed", "approved", "rejected"] as const).map((value) => (
              <Button
                key={value}
                size="sm"
                variant={filter === value ? "default" : "outline"}
                aria-pressed={filter === value}
                onClick={() => { setFilter(value); setPage(0); }}
              >
                {t[value]}
              </Button>
            ))}
          </div>
        </div>
        {total === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.noQuestions}</p>
        ) : (
          <ol className="mt-3 space-y-3">
            {shownQuestions.map((question) => (
              <li key={question.id} className="rounded-lg border p-3 text-sm">
                <p className="break-words">{question.text}</p>
                {question.reference_answer ? (
                  <details className="mt-2 rounded-lg bg-surface px-3 py-2 text-xs">
                    <summary className="cursor-pointer font-medium">Эталонный ответ</summary>
                    <p className="mt-2 whitespace-pre-line">{question.reference_answer}</p>
                    {question.answer_criteria ? (
                      <p className="mt-2 whitespace-pre-line text-muted-foreground">
                        {question.answer_criteria}
                      </p>
                    ) : null}
                  </details>
                ) : null}
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary" className="max-w-full whitespace-normal break-words">
                    {question.topic ?? "Без темы"}
                  </Badge>
                  <Badge variant="outline">{question.difficulty}</Badge>
                  <Badge variant="outline">{question.level}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {t.occurrences}: {question.occurrences}
                  </span>
                  {question.status === "approved" ? (
                    <Badge>{t.approved}</Badge>
                  ) : null}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <label className="text-xs text-muted-foreground">
                    {t.lesson}
                    <select
                      className="ml-2 h-8 w-full min-w-0 max-w-full rounded-lg border border-input bg-background px-2 text-sm sm:max-w-[260px]"
                      value={question.lesson_id ?? ""}
                      disabled={busyId === question.id}
                      onChange={(event) =>
                        void patch(question, {
                          lesson_id: event.target.value ? Number(event.target.value) : null,
                        })
                      }
                    >
                      <option value="">{t.noLesson}</option>
                      {lessons.map((lesson) => (
                        <option key={lesson.id} value={lesson.id}>
                          {lesson.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    size="sm"
                    variant={question.status === "approved" ? "outline" : "default"}
                    disabled={busyId === question.id}
                    onClick={() => void patch(question, { status: "approved" })}
                  >
                    {t.approve}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busyId === question.id}
                    onClick={() => void patch(question, { status: "rejected" })}
                  >
                    {t.reject}
                  </Button>
                </div>
              </li>
            ))}
          </ol>
        )}
        {total > 25 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              disabled={page === 0}
              onClick={() => setPage((value) => Math.max(0, value - 1))}
            >
              ← Назад
            </Button>
            <span className="text-sm text-muted-foreground">
              Страница {page + 1} из {pageCount} · {total} вопросов
            </span>
            <Button
              variant="outline"
              disabled={page + 1 >= pageCount}
              onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}
            >
              Вперёд →
            </Button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
