"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { adminErrorMessage } from "@/lib/admin-error";
import {
  deleteAdminQuiz,
  fetchAdminLesson,
  fetchAdminQuiz,
  replaceAdminBlocks,
  replaceAdminQuiz,
  updateAdminLesson,
} from "@/lib/api";
import type {
  BlockInput,
  LessonAdmin,
  QuizQuestionAdmin as Question,
} from "@/lib/admin-types";

const inputClass =
  "h-9 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";
const textareaClass =
  "w-full rounded-lg border bg-background px-3 py-2 text-sm leading-relaxed outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const BLOCK_TYPES = ["heading", "text", "code", "callout", "image", "table", "list"];
const QUESTION_KINDS = ["theory", "situation", "analysis", "error", "decision"];

type EditableBlock = { type: string; contentText: string };

function defaultContent(type: string): Record<string, unknown> {
  switch (type) {
    case "heading":
    case "text":
    case "callout":
      return { text: "" };
    case "list":
      return { items: [] };
    case "code":
      return { language: "python", code: "" };
    case "table":
      return { headers: [], rows: [] };
    case "image":
      return { src: "/lessons/example.svg", alt: "", caption: "" };
    default:
      return {};
  }
}

function emptyQuestion(): Question {
  return {
    kind: "theory",
    text: "",
    explanation: "",
    options: [
      { text: "", is_correct: true },
      { text: "", is_correct: false },
    ],
  };
}

export function LessonEditor({ lessonId }: { lessonId: number }) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [lesson, setLesson] = useState<LessonAdmin | null>(null);

  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [minutes, setMinutes] = useState(90);
  const [published, setPublished] = useState(false);
  const [blocks, setBlocks] = useState<EditableBlock[]>([]);

  const [quizExists, setQuizExists] = useState(false);
  const [quizTitle, setQuizTitle] = useState("");
  const [quizDescription, setQuizDescription] = useState("");
  const [quizPublished, setQuizPublished] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [attemptsCount, setAttemptsCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchAdminLesson(lessonId, controller.signal),
      fetchAdminQuiz(lessonId, controller.signal),
    ])
      .then(([lessonData, quizData]) => {
        setLesson(lessonData);
        setTitle(lessonData.title);
        setSummary(lessonData.summary ?? "");
        setMinutes(lessonData.estimated_minutes);
        setPublished(lessonData.is_published);
        setBlocks(
          lessonData.blocks.map((block) => ({
            type: block.type,
            contentText: JSON.stringify(block.content, null, 2),
          })),
        );
        setQuizExists(Boolean(quizData));
        if (quizData) {
          setQuizTitle(quizData.title);
          setQuizDescription(quizData.description ?? "");
          setQuizPublished(quizData.is_published);
          setQuestions(quizData.questions);
          setAttemptsCount(quizData.attempts_count);
        }
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
    return () => controller.abort();
  }, [lessonId]);

  async function saveMeta() {
    if (!lesson) return;
    setError(null);
    setMessage(null);
    try {
      const updated = await updateAdminLesson(lesson.id, {
        title,
        summary: summary.trim() ? summary : null,
        estimated_minutes: minutes,
        is_published: published,
      });
      setLesson(updated);
      setMessage(t.saved);
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function saveBlocks() {
    if (!lesson) return;
    setError(null);
    setMessage(null);
    const payload: BlockInput[] = [];
    for (const block of blocks) {
      try {
        const content = JSON.parse(block.contentText || "{}") as Record<string, unknown>;
        payload.push({ type: block.type, content });
      } catch {
        setError(t.blockJsonError);
        return;
      }
    }
    try {
      const updated = await replaceAdminBlocks(lesson.id, payload);
      setLesson(updated);
      setBlocks(
        updated.blocks.map((block) => ({
          type: block.type,
          contentText: JSON.stringify(block.content, null, 2),
        })),
      );
      setMessage(t.saved);
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  function addBlock() {
    setBlocks((current) => [
      ...current,
      { type: "text", contentText: JSON.stringify(defaultContent("text"), null, 2) },
    ]);
  }

  function updateBlock(index: number, patch: Partial<EditableBlock>) {
    setBlocks((current) =>
      current.map((block, position) => (position === index ? { ...block, ...patch } : block)),
    );
  }

  function moveBlock(index: number, delta: number) {
    setBlocks((current) => {
      const target = index + delta;
      if (target < 0 || target >= current.length) return current;
      const copy = [...current];
      [copy[index], copy[target]] = [copy[target], copy[index]];
      return copy;
    });
  }

  function startQuiz() {
    setQuizExists(true);
    setQuizTitle("Квиз урока");
    setQuizDescription("");
    setQuizPublished(false);
    setQuestions([emptyQuestion()]);
  }

  function updateQuestion(index: number, patch: Partial<Question>) {
    setQuestions((current) =>
      current.map((question, position) =>
        position === index ? { ...question, ...patch } : question,
      ),
    );
  }

  function addQuestion() {
    setQuestions((current) => [...current, emptyQuestion()]);
  }

  function removeQuestion(index: number) {
    setQuestions((current) => current.filter((_, position) => position !== index));
  }

  function updateOption(
    questionIndex: number,
    optionIndex: number,
    patch: { text?: string; is_correct?: boolean },
  ) {
    setQuestions((current) =>
      current.map((question, position) => {
        if (position !== questionIndex) return question;
        return {
          ...question,
          options: question.options.map((option, optionPosition) =>
            optionPosition === optionIndex ? { ...option, ...patch } : option,
          ),
        };
      }),
    );
  }

  function addOption(questionIndex: number) {
    setQuestions((current) =>
      current.map((question, position) =>
        position === questionIndex
          ? { ...question, options: [...question.options, { text: "", is_correct: false }] }
          : question,
      ),
    );
  }

  function removeOption(questionIndex: number, optionIndex: number) {
    setQuestions((current) =>
      current.map((question, position) =>
        position === questionIndex
          ? {
              ...question,
              options: question.options.filter((_, index) => index !== optionIndex),
            }
          : question,
      ),
    );
  }

  async function saveQuiz() {
    if (!lesson) return;
    setError(null);
    setMessage(null);

    const invalid = questions.some(
      (question) =>
        !question.text.trim() ||
        !question.explanation.trim() ||
        question.options.length < 2 ||
        question.options.some((option) => !option.text.trim()) ||
        !question.options.some((option) => option.is_correct),
    );
    if (!quizTitle.trim() || questions.length === 0 || invalid) {
      setError(t.quizValidation);
      return;
    }

    const losesAttempts = quizExists && attemptsCount > 0;
    if (losesAttempts && !window.confirm(t.confirmAttemptsLoss(attemptsCount))) {
      return;
    }

    try {
      const saved = await replaceAdminQuiz(lesson.id, {
        title: quizTitle,
        description: quizDescription.trim() ? quizDescription : null,
        is_published: quizPublished,
        questions,
        confirm_attempts_loss: losesAttempts,
        expected_attempts_count: attemptsCount,
      });
      setQuizExists(true);
      setAttemptsCount(0);
      setLesson((current) => (current ? { ...current, quiz_id: saved.id } : current));
      setMessage(t.saved);
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function removeQuiz() {
    if (!lesson || !window.confirm(t.deleteQuizConfirm)) return;
    setError(null);
    try {
      await deleteAdminQuiz(lesson.id, true, attemptsCount);
      setQuizExists(false);
      setQuestions([]);
      setAttemptsCount(0);
      setLesson({ ...lesson, quiz_id: null });
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  if (status === "loading") return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  if (status === "error" || lesson === null) {
    return <p className="text-sm text-muted-foreground">{t.loadError}</p>;
  }

  return (
    <div className="space-y-8">
      <p className="text-sm">
        <Link href="/admin" className="text-brand underline-offset-4 hover:underline">
          ← {t.dashboard}
        </Link>
      </p>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="text-sm text-muted-foreground">
          {message}
        </p>
      ) : null}

      <section className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{lesson.title}</h2>
          <Badge variant={published ? "default" : "outline"}>
            {published ? t.published : t.draft}
          </Badge>
        </div>
        <div className="mt-3 space-y-2">
          <label htmlFor="lesson-title" className="text-sm font-medium">
            {t.lessonName}
          </label>
          <input
            id="lesson-title"
            value={title}
            maxLength={200}
            onChange={(event) => setTitle(event.target.value)}
            className={inputClass}
          />
          <label htmlFor="lesson-summary" className="text-sm font-medium">
            {t.description} ({t.optional})
          </label>
          <textarea
            id="lesson-summary"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            className={`${textareaClass} min-h-20`}
          />
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="lesson-minutes" className="text-sm font-medium">
                {t.minutes}
              </label>
              <input
                id="lesson-minutes"
                type="number"
                min={5}
                max={600}
                value={minutes}
                onChange={(event) => setMinutes(Number(event.target.value))}
                className={`${inputClass} w-24`}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={published}
                onChange={(event) => setPublished(event.target.checked)}
              />
              {t.published}
            </label>
            <Button size="lg" className="px-4" onClick={saveMeta}>
              {t.save}
            </Button>
          </div>
        </div>
      </section>

      <section className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{t.blocks}</h2>
          <Button variant="outline" size="sm" onClick={addBlock}>
            {t.addBlock}
          </Button>
        </div>
        <ul className="mt-3 space-y-3">
          {blocks.map((block, index) => (
            <li key={index} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={block.type}
                  onChange={(event) => {
                    const type = event.target.value;
                    updateBlock(index, {
                      type,
                      contentText: JSON.stringify(defaultContent(type), null, 2),
                    });
                  }}
                  className={`${inputClass} w-40`}
                  aria-label={t.blockType}
                >
                  {BLOCK_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <Button variant="ghost" size="sm" onClick={() => moveBlock(index, -1)}>
                  ↑
                </Button>
                <Button variant="ghost" size="sm" onClick={() => moveBlock(index, 1)}>
                  ↓
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() =>
                    setBlocks((current) => current.filter((_, position) => position !== index))
                  }
                >
                  {t.delete}
                </Button>
              </div>
              <label htmlFor={`block-${index}`} className="sr-only">
                {t.blockContent}
              </label>
              <textarea
                id={`block-${index}`}
                value={block.contentText}
                onChange={(event) => updateBlock(index, { contentText: event.target.value })}
                className={`${textareaClass} mt-2 min-h-28 font-mono`}
              />
            </li>
          ))}
        </ul>
        <Button size="lg" className="mt-3 px-4" onClick={saveBlocks}>
          {t.saveBlocks}
        </Button>
      </section>

      <section className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{t.quiz}</h2>
          {quizExists ? (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={removeQuiz}
            >
              {t.deleteQuiz}
            </Button>
          ) : null}
        </div>

        {!quizExists ? (
          <div className="mt-3">
            <p className="text-sm text-muted-foreground">{t.noQuiz}</p>
            <Button size="lg" className="mt-3 px-4" onClick={startQuiz}>
              {t.createQuiz}
            </Button>
          </div>
        ) : (
          <div className="mt-3 space-y-4">
            <input
              value={quizTitle}
              maxLength={200}
              onChange={(event) => setQuizTitle(event.target.value)}
              placeholder={t.quizTitle}
              className={inputClass}
              aria-label={t.quizTitle}
            />
            <textarea
              value={quizDescription}
              onChange={(event) => setQuizDescription(event.target.value)}
              placeholder={t.quizDescription}
              className={`${textareaClass} min-h-20`}
              aria-label={t.quizDescription}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={quizPublished}
                onChange={(event) => setQuizPublished(event.target.checked)}
              />
              {t.quizPublished}
            </label>
            {attemptsCount > 0 ? (
              <p role="status" className="text-sm text-muted-foreground">
                {t.confirmAttemptsLoss(attemptsCount)}
              </p>
            ) : null}

            {questions.map((question, questionIndex) => (
              <div key={questionIndex} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold">
                    {t.question} {questionIndex + 1}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => removeQuestion(questionIndex)}
                  >
                    {t.delete}
                  </Button>
                </div>
                <select
                  value={question.kind}
                  onChange={(event) =>
                    updateQuestion(questionIndex, { kind: event.target.value })
                  }
                  className={`${inputClass} mt-2 w-48`}
                  aria-label={t.questionKind}
                >
                  {QUESTION_KINDS.map((kind) => (
                    <option key={kind} value={kind}>
                      {kind}
                    </option>
                  ))}
                </select>
                <textarea
                  value={question.text}
                  onChange={(event) =>
                    updateQuestion(questionIndex, { text: event.target.value })
                  }
                  placeholder={t.questionText}
                  className={`${textareaClass} mt-2 min-h-20`}
                  aria-label={t.questionText}
                />
                <textarea
                  value={question.explanation}
                  onChange={(event) =>
                    updateQuestion(questionIndex, { explanation: event.target.value })
                  }
                  placeholder={t.explanation}
                  className={`${textareaClass} mt-2 min-h-16`}
                  aria-label={t.explanation}
                />
                <ul className="mt-2 space-y-1">
                  {question.options.map((option, optionIndex) => (
                    <li key={optionIndex} className="flex flex-wrap items-center gap-2">
                      <input
                        value={option.text}
                        onChange={(event) =>
                          updateOption(questionIndex, optionIndex, {
                            text: event.target.value,
                          })
                        }
                        placeholder={`${t.option} ${optionIndex + 1}`}
                        className={`${inputClass} min-w-0 flex-1`}
                        aria-label={`${t.option} ${optionIndex + 1}`}
                      />
                      <label className="flex items-center gap-1 text-xs">
                        <input
                          type="checkbox"
                          checked={option.is_correct}
                          onChange={(event) =>
                            updateOption(questionIndex, optionIndex, {
                              is_correct: event.target.checked,
                            })
                          }
                        />
                        {t.correct}
                      </label>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => removeOption(questionIndex, optionIndex)}
                      >
                        {t.delete}
                      </Button>
                    </li>
                  ))}
                </ul>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => addOption(questionIndex)}
                >
                  {t.addOption}
                </Button>
              </div>
            ))}

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={addQuestion}>
                {t.addQuestion}
              </Button>
              <Button size="lg" className="px-4" onClick={saveQuiz}>
                {t.saveQuiz}
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
