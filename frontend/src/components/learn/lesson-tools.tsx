"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { toolsContent as t } from "@/content/tools";
import {
  ApiError,
  addHighlight,
  createSavedQuestion,
  deleteHighlight,
  fetchHighlights,
  fetchNote,
  saveNote,
} from "@/lib/api";
import type { LessonHighlight } from "@/lib/tools-types";

const textareaClass =
  "mt-2 min-h-28 w-full rounded-lg border bg-background px-3 py-2 text-sm leading-relaxed outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

/**
 * Личные материалы урока: конспект, выделенные определения и сложный вопрос.
 * Всё приватно: сервер отдаёт записи только их владельцу.
 */
export function LessonTools({ lessonId }: { lessonId: number }) {
  const { status: authStatus, clearSession, version } = useAuth();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [note, setNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteStatus, setNoteStatus] = useState<"idle" | "saved" | "error">("idle");
  const [highlights, setHighlights] = useState<LessonHighlight[]>([]);
  const [newHighlight, setNewHighlight] = useState("");
  const [highlightError, setHighlightError] = useState<string | null>(null);
  const [addingHighlight, setAddingHighlight] = useState(false);
  const [question, setQuestion] = useState("");
  const [questionStatus, setQuestionStatus] = useState<"idle" | "saved" | "error">("idle");
  const [savingQuestion, setSavingQuestion] = useState(false);
  // Текущие значения полей: после ответа сервера проверяем, не изменился ли
  // текст, пока шёл запрос. Успех относится только к отправленной версии.
  const noteRef = useRef("");
  const highlightRef = useRef("");
  const questionRef = useRef("");

  function handleFailure(caught: unknown, setMessage: (value: string | null) => void) {
    if (caught instanceof ApiError && caught.status === 401) {
      clearSession(version);
      return;
    }
    if (caught instanceof ApiError && caught.status === 409) {
      setMessage(t.sessionChanged);
      return;
    }
    setMessage(t.saveError);
  }

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    const controller = new AbortController();
    Promise.all([
      fetchNote(lessonId, controller.signal),
      fetchHighlights(lessonId, controller.signal),
    ])
      .then(([noteData, highlightData]) => {
        setNote(noteData.content);
        noteRef.current = noteData.content;
        setHighlights(highlightData);
        setLoading(false);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        if (caught instanceof ApiError && caught.status === 401) {
          clearSession(version);
        } else {
          setLoadError(true);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [authStatus, lessonId, clearSession, version]);

  if (authStatus !== "authenticated") return null;

  if (loading) {
    return <p className="mt-10 text-sm text-muted-foreground">{t.loading}</p>;
  }
  if (loadError) {
    return (
      <div className="mt-10 rounded-xl border bg-card p-5">
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button
          variant="outline"
          size="lg"
          className="mt-4"
          onClick={() => window.location.reload()}
        >
          {t.retry}
        </Button>
      </div>
    );
  }

  async function handleSaveNote() {
    const sent = note;
    setSavingNote(true);
    setNoteStatus("idle");
    try {
      await saveNote(lessonId, sent);
      // Пока шёл запрос, текст могли изменить: «Сохранено» относится только
      // к отправленной версии, новый текст остаётся несохранённым.
      setNoteStatus(noteRef.current === sent ? "saved" : "idle");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        clearSession(version);
        return;
      }
      setNoteStatus("error");
    } finally {
      setSavingNote(false);
    }
  }

  async function handleAddHighlight() {
    const text = newHighlight.trim();
    if (!text || addingHighlight) return;
    setHighlightError(null);
    setAddingHighlight(true);
    try {
      const created = await addHighlight(lessonId, text);
      setHighlights((current) => [created, ...current]);
      if (highlightRef.current.trim() === text) {
        setNewHighlight("");
        highlightRef.current = "";
      }
    } catch (caught) {
      handleFailure(caught, setHighlightError);
    } finally {
      setAddingHighlight(false);
    }
  }

  async function handleDeleteHighlight(id: number) {
    setHighlightError(null);
    try {
      await deleteHighlight(id);
      setHighlights((current) => current.filter((item) => item.id !== id));
    } catch (caught) {
      handleFailure(caught, setHighlightError);
    }
  }

  async function handleSaveQuestion() {
    const text = question.trim();
    if (!text) return;
    setSavingQuestion(true);
    setQuestionStatus("idle");
    try {
      await createSavedQuestion(text, lessonId);
      if (questionRef.current.trim() === text) {
        setQuestion("");
        questionRef.current = "";
      }
      setQuestionStatus("saved");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        clearSession(version);
        return;
      }
      if (caught instanceof ApiError && caught.status === 409) {
        setQuestionStatus("error");
        return;
      }
      setQuestionStatus("error");
    } finally {
      setSavingQuestion(false);
    }
  }

  return (
    <section aria-labelledby="lesson-tools-heading" className="mt-12 border-t pt-8">
      <h2 id="lesson-tools-heading" className="text-xl font-semibold">
        {t.lessonHeading}
      </h2>

      <div className="mt-4 rounded-xl border bg-card p-5">
        <h3 className="text-base font-semibold">{t.noteTitle}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{t.noteHint}</p>
        <label htmlFor="lesson-note" className="sr-only">
          {t.noteTitle}
        </label>
        <textarea
          id="lesson-note"
          value={note}
          maxLength={20_000}
          onChange={(event) => {
            setNote(event.target.value);
            noteRef.current = event.target.value;
            setNoteStatus("idle");
          }}
          placeholder={t.notePlaceholder}
          className={textareaClass}
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button size="lg" className="px-4" onClick={handleSaveNote} disabled={savingNote}>
            {savingNote ? t.saving : t.save}
          </Button>
          <span role="status" aria-live="polite" className="text-sm text-muted-foreground">
            {noteStatus === "saved" ? t.saved : ""}
          </span>
          {noteStatus === "error" ? (
            <span role="alert" className="text-sm text-destructive">
              {t.saveError}
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 rounded-xl border bg-card p-5">
        <h3 className="text-base font-semibold">{t.highlightTitle}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{t.highlightHint}</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <label htmlFor="highlight-text" className="sr-only">
            {t.highlightTitle}
          </label>
          <input
            id="highlight-text"
            value={newHighlight}
            maxLength={1_000}
            onChange={(event) => {
              setNewHighlight(event.target.value);
              highlightRef.current = event.target.value;
            }}
            placeholder={t.highlightPlaceholder}
            className="h-9 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button size="lg" className="px-4" onClick={handleAddHighlight} disabled={addingHighlight}>
            {t.addHighlight}
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="px-4"
            onClick={() => {
              // Берём текст, который человек выделил мышью в уроке выше.
              const selected = window.getSelection()?.toString().trim();
              if (selected) {
                setNewHighlight(selected);
                highlightRef.current = selected;
              }
            }}
          >
            {t.useSelection}
          </Button>
        </div>
        {highlightError ? (
          <p role="alert" className="mt-2 text-sm text-destructive">
            {highlightError}
          </p>
        ) : null}
        {highlights.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.emptyHighlights}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {highlights.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-3 rounded-lg bg-surface px-3 py-2 text-sm"
              >
                <span className="min-w-0 leading-relaxed break-words">{item.text}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-destructive"
                  aria-label={`${t.delete}: ${item.text}`}
                  onClick={() => handleDeleteHighlight(item.id)}
                >
                  {t.delete}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-4 rounded-xl border bg-card p-5">
        <h3 className="text-base font-semibold">{t.questionTitle}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{t.questionHint}</p>
        <label htmlFor="saved-question" className="sr-only">
          {t.questionTitle}
        </label>
        <textarea
          id="saved-question"
          value={question}
          maxLength={2_000}
          onChange={(event) => {
            setQuestion(event.target.value);
            questionRef.current = event.target.value;
            setQuestionStatus("idle");
          }}
          placeholder={t.questionPlaceholder}
          className={textareaClass}
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button size="lg" className="px-4" onClick={handleSaveQuestion} disabled={savingQuestion}>
            {t.saveQuestion}
          </Button>
          <span role="status" aria-live="polite" className="text-sm text-muted-foreground">
            {questionStatus === "saved" ? t.questionSaved : ""}
          </span>
          {questionStatus === "error" ? (
            <span role="alert" className="text-sm text-destructive">
              {t.questionError}
            </span>
          ) : null}
        </div>
      </div>
    </section>
  );
}
