"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { interviewContent as t } from "@/content/interview";
import {
  analyzeInterviewSource,
  fetchInterviewLessons,
  fetchInterviewQuestions,
  fetchInterviewReport,
  fetchInterviewSources,
  approveAllInterviewQuestions,
  deduplicateInterviewQuestions,
  generateInterviewAnswers,
  updateInterviewQuestion,
  uploadInterviewSource,
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
      fetchInterviewQuestions(undefined, controller.signal),
      fetchInterviewReport(controller.signal),
      fetchInterviewLessons(controller.signal),
    ])
      .then(([nextSources, nextQuestions, nextReport, nextLessons]) => {
        setSources(nextSources);
        setQuestions(nextQuestions);
        setReport(nextReport);
        setLessons(nextLessons);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
    return () => controller.abort();
  }, [reloadToken]);

  const visibleQuestions = useMemo(
    () => (filter === "all" ? questions : questions.filter((item) => item.status === filter)),
    [filter, questions],
  );

  async function upload(file: File | undefined) {
    if (!file) return;
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
    } catch {
      setError(t.uploadError);
    } finally {
      setUploading(false);
    }
  }

  async function analyze(source: InterviewSource) {
    setBusyId(source.id);
    setError(null);
    try {
      const result = await analyzeInterviewSource(source.id, allowExternal);
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
    try {
      const result = await generateInterviewAnswers(allowAnswersExternal);
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
        <label className="mt-4 inline-flex cursor-pointer flex-wrap items-center gap-3">
          <span className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground">
            {uploading ? t.uploading : t.upload}
          </span>
          <input
            type="file"
            accept=".txt,.pdf,.docx,.png,.jpg,.jpeg"
            className="sr-only"
            disabled={uploading}
            onChange={(event) => {
              void upload(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <span className="text-xs text-muted-foreground">TXT, PDF, DOCX, PNG, JPG · до 10 МБ</span>
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
                    {source.questions_count} · {source.status}
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
            <div className="mt-4 overflow-x-auto">
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
                onClick={() => setFilter(value)}
              >
                {t[value]}
              </Button>
            ))}
          </div>
        </div>
        {visibleQuestions.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.noQuestions}</p>
        ) : (
          <ol className="mt-3 space-y-3">
            {visibleQuestions.map((question) => (
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
                  <Badge variant="secondary">{question.topic ?? "Без темы"}</Badge>
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
                      className="ml-2 h-8 max-w-[260px] rounded-lg border bg-background px-2 text-sm"
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
      </section>
    </div>
  );
}
