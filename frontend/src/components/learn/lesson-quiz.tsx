"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { quizContent as t } from "@/content/quiz";
import {
  ApiError,
  fetchLessonQuiz,
  submitQuizAttempt,
} from "@/lib/api";
import type {
  QuizAnswerInput,
  QuizAttemptResult,
  QuizQuestion,
  QuizWithHistory,
} from "@/lib/learn-types";
import { cn } from "@/lib/utils";

type Status = "loading" | "ready" | "missing" | "error";

type Answers = Record<number, number[]>;

function selectedAnswers(questions: QuizQuestion[], answers: Answers): QuizAnswerInput[] {
  return questions.map((question) => ({
    question_id: question.id,
    option_ids: answers[question.id] ?? [],
  }));
}

function isAnswered(question: QuizQuestion, answers: Answers): boolean {
  return (answers[question.id] ?? []).length > 0;
}

/**
 * Квиз в конце урока. Правильные ответы хранит только сервер: до отправки
 * браузер их не знает, после — показывает разбор с объяснениями.
 */
export function LessonQuiz({ lessonId }: { lessonId: number }) {
  const { status: authStatus, clearSession, version } = useAuth();
  const [status, setStatus] = useState<Status>("loading");
  const [data, setData] = useState<QuizWithHistory | null>(null);
  const [answers, setAnswers] = useState<Answers>({});
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const resultRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  // Номер запроса истории: ответ на старый запрос не должен перезаписать
  // данные после новой попытки.
  const historyRequestId = useRef(0);

  // После отправки переводим фокус на результат: иначе он остаётся на кнопке,
  // которая исчезла из разметки.
  useEffect(() => {
    if (result) resultRef.current?.focus();
  }, [result]);

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    const controller = new AbortController();
    const historyId = ++historyRequestId.current;
    fetchLessonQuiz(lessonId, controller.signal)
      .then((quiz) => {
        if (historyRequestId.current !== historyId) return;
        setData(quiz);
        setStatus("ready");
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        if (caught instanceof ApiError && caught.status === 401) {
          clearSession(version);
        } else if (caught instanceof ApiError && caught.status === 404) {
          setStatus("missing");
        } else {
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, [authStatus, lessonId, reloadToken, clearSession, version]);

  if (authStatus !== "authenticated") return null;

  if (status === "loading") {
    return <p className="mt-10 text-sm text-muted-foreground">{t.title}…</p>;
  }
  if (status === "missing") {
    return (
      <section className="mt-10 rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{t.missing}</p>
      </section>
    );
  }
  if (status === "error" || data === null) {
    return (
      <section className="mt-10 rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{t.loadError}</p>
        <Button
          variant="outline"
          size="lg"
          className="mt-4"
          onClick={() => {
            setStatus("loading");
            setReloadToken((value) => value + 1);
          }}
        >
          {t.retryLoad}
        </Button>
      </section>
    );
  }

  const { quiz, attempts_total, best_percent } = data;
  const answered = quiz.questions.filter((question) => isAnswered(question, answers)).length;
  const left = quiz.questions.length - answered;

  function toggleOption(question: QuizQuestion, optionId: number) {
    setAnswers((previous) => {
      const chosen = previous[question.id] ?? [];
      if (question.multiple) {
        return {
          ...previous,
          [question.id]: chosen.includes(optionId)
            ? chosen.filter((value) => value !== optionId)
            : [...chosen, optionId],
        };
      }
      return { ...previous, [question.id]: [optionId] };
    });
  }

  async function handleSubmit() {
    if (submitting || left > 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const attempt = await submitQuizAttempt(
        lessonId,
        selectedAnswers(quiz.questions, answers),
      );
      setResult(attempt);
      // История и лучший результат обновляются отдельно, чтобы сбой этого
      // запроса не скрывал уже полученный разбор.
      const historyId = ++historyRequestId.current;
      fetchLessonQuiz(lessonId)
        .then((history) => {
          if (historyRequestId.current === historyId) setData(history);
        })
        .catch(() => undefined);
    } catch (caught: unknown) {
      // Истёкшая сессия: сбрасываем вход, чтобы страница входа не вернула
      // ученика обратно к недоступной отправке. Только для той версии сессии,
      // с которой началась отправка: запоздалый 401 не трогает новый вход.
      if (caught instanceof ApiError && caught.status === 401) {
        clearSession(version);
        return;
      }
      if (caught instanceof ApiError && caught.status === 404) {
        setStatus("missing");
        return;
      }
      if (caught instanceof ApiError && caught.status === 409) {
        setError(t.sessionChanged);
        return;
      }
      setError(t.submitError);
    } finally {
      setSubmitting(false);
    }
  }

  function restart() {
    setAnswers({});
    setResult(null);
    setError(null);
    // После исчезновения кнопки «Пройти ещё раз» возвращаем фокус к заголовку
    // квиза, а не теряем его.
    requestAnimationFrame(() => headingRef.current?.focus());
  }

  const resultByQuestion = new Map(
    (result?.questions ?? []).map((item) => [item.question_id, item]),
  );

  return (
    <section aria-labelledby="quiz-heading" className="mt-12">
      <div className="rounded-xl border bg-card p-5 sm:p-6">
        <h2 id="quiz-heading" ref={headingRef} tabIndex={-1} className="text-xl font-semibold outline-none">
          {quiz.title || t.title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {quiz.description ?? t.intro}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          {t.questionCount(quiz.questions.length)}
        </p>
        <p className="mt-3 text-xs text-muted-foreground">
          {attempts_total > 0 ? (
            <>
              {t.attempts(attempts_total)}
              {best_percent !== null ? ` · ${t.best(best_percent)}` : null}
            </>
          ) : (
            t.noAttempts
          )}
        </p>
        {data.attempts.length > 0 ? (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-muted-foreground">
              {t.historyTitle}
            </summary>
            <ul className="mt-2 space-y-1 text-muted-foreground">
              {data.attempts.map((attempt) => (
                <li key={attempt.id}>
                  {t.attemptLine(
                    new Date(attempt.created_at).toLocaleString("ru-RU"),
                    attempt.percent,
                    attempt.score,
                    attempt.max_score,
                  )}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>

      {result ? (
        <div
          ref={resultRef}
          tabIndex={-1}
          role="status"
          aria-live="polite"
          className="mt-4 rounded-xl border bg-card p-5 outline-none sm:p-6"
        >
          <p className="text-lg font-semibold">
            {t.resultTitle(result.score, result.max_score, result.percent)}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {result.percent >= 80 ? t.resultGood : t.resultWeak}
          </p>
          <Button variant="outline" size="lg" className="mt-4" onClick={restart}>
            {t.retry}
          </Button>
        </div>
      ) : null}

      <ol className="mt-4 space-y-4">
        {quiz.questions.map((question, index) => {
          const review = resultByQuestion.get(question.id);
          const chosen = answers[question.id] ?? [];
          return (
            <li key={question.id} className="rounded-xl border bg-card p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {index + 1}. {t.kind[question.kind] ?? question.kind}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {question.multiple ? t.multipleHint : t.singleHint}
                </span>
                {review ? (
                  <Badge variant={review.is_correct ? "default" : "destructive"}>
                    {review.is_correct ? t.correct : t.incorrect}
                  </Badge>
                ) : null}
              </div>

              <fieldset className="mt-3" disabled={result !== null || submitting}>
                <legend className="text-base leading-relaxed font-medium">
                  {question.text}
                </legend>
                <div className="mt-3 space-y-2">
                  {question.options.map((option) => {
                    // После отправки «Ваш выбор» берём из сохранённой попытки,
                    // а не из редактируемого состояния: иначе разбор разойдётся
                    // с тем, что оценил сервер.
                    const selected = review
                      ? review.selected_option_ids.includes(option.id)
                      : chosen.includes(option.id);
                    const correct = review?.correct_option_ids.includes(option.id) ?? false;
                    const wrongSelected = Boolean(review) && selected && !correct;
                    return (
                      <label
                        key={option.id}
                        className={cn(
                          "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 text-sm leading-relaxed transition-colors",
                          correct
                            ? "border-brand bg-surface"
                            : wrongSelected
                              ? "border-destructive bg-destructive/10"
                              : "hover:bg-muted",
                          result !== null ? "cursor-default" : "",
                        )}
                      >
                        <input
                          type={question.multiple ? "checkbox" : "radio"}
                          name={`question-${question.id}`}
                          value={option.id}
                          checked={selected}
                          onChange={() => toggleOption(question, option.id)}
                          className="mt-1 size-4 shrink-0 accent-[var(--brand)]"
                        />
                        <span className="min-w-0">
                          {option.text}
                          {correct ? (
                            <span className="ml-2 text-xs font-medium text-brand">
                              {t.correctAnswer}
                            </span>
                          ) : wrongSelected ? (
                            <span className="ml-2 text-xs font-medium text-destructive">
                              {t.yourAnswer}
                            </span>
                          ) : null}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>

              {review ? (
                <div className="mt-3 rounded-lg bg-surface px-3 py-2 text-sm leading-relaxed">
                  <span className="font-medium">{t.explanation}: </span>
                  {review.explanation}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>

      {result === null ? (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button size="lg" className="px-4" onClick={handleSubmit} disabled={submitting || left > 0}>
            {submitting ? t.submitting : t.submit}
          </Button>
          {left > 0 ? (
            <span className="text-sm text-muted-foreground">{t.answerAll(left)}</span>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}
