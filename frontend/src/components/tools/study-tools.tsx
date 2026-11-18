"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { toolsContent as t } from "@/content/tools";
import {
  ApiError,
  createCheatsheet,
  createReviewItem,
  deleteCheatsheet,
  deleteReviewItem,
  deleteSavedQuestion,
  fetchCheatsheets,
  fetchReviewItems,
  fetchSavedQuestions,
  fetchWeakTopics,
  setReviewItemDone,
  setSavedQuestionResolved,
  updateCheatsheet,
} from "@/lib/api";
import type { Cheatsheet, ReviewItem, SavedQuestion, WeakTopic } from "@/lib/tools-types";
import { cn } from "@/lib/utils";

type Status = "loading" | "ready" | "error";

/** Личные материалы: слабые темы, повторение, вопросы и шпаргалки. */
export function StudyTools() {
  const { user, version } = useAuth();
  // Ключ по ученику и версии сессии: при смене пользователя списки и черновики
  // начинаются заново, даже если ID остался тем же после повторного входа.
  return <StudyToolsContent key={`tools-${user?.id ?? "guest"}-${version}`} />;
}

function StudyToolsContent() {
  const router = useRouter();
  const { status: authStatus, clearSession, version } = useAuth();
  const [status, setStatus] = useState<Status>("loading");
  const [reloadToken, setReloadToken] = useState(0);

  const [weak, setWeak] = useState<WeakTopic[]>([]);
  const [review, setReview] = useState<ReviewItem[]>([]);
  const [questions, setQuestions] = useState<SavedQuestion[]>([]);
  const [cheatsheets, setCheatsheets] = useState<Cheatsheet[]>([]);

  const [newReview, setNewReview] = useState("");
  const [cheatTitle, setCheatTitle] = useState("");
  const [cheatContent, setCheatContent] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [addingReview, setAddingReview] = useState(false);
  const [addingCheatsheet, setAddingCheatsheet] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // Текущие черновики: успех применяется только к отправленной версии текста.
  const reviewRef = useRef("");
  const cheatTitleRef = useRef("");
  const cheatContentRef = useRef("");

  function handleFailure(caught: unknown) {
    // Истёкшая сессия: сбрасываем общий вход, чтобы не предлагать «повторить»
    // действие, которое сервер всё равно отклонит. Только для той версии
    // сессии, с которой началось действие.
    if (caught instanceof ApiError && caught.status === 401) {
      clearSession(version);
      return;
    }
    if (caught instanceof ApiError && caught.status === 409) {
      setFormError(t.sessionChanged);
      return;
    }
    setFormError(t.saveError);
  }

  useEffect(() => {
    if (authStatus === "anonymous") {
      router.replace("/login?next=%2Fprofile%2Ftools");
    }
  }, [authStatus, router]);

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    const controller = new AbortController();
    Promise.all([
      fetchWeakTopics(controller.signal),
      fetchReviewItems(controller.signal),
      fetchSavedQuestions(controller.signal),
      fetchCheatsheets(controller.signal),
    ])
      .then(([weakData, reviewData, questionData, cheatsheetData]) => {
        setWeak(weakData);
        setReview(reviewData);
        setQuestions(questionData);
        setCheatsheets(cheatsheetData);
        setStatus("ready");
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        if (caught instanceof ApiError && caught.status === 401) {
          clearSession(version);
        } else {
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, [authStatus, reloadToken, clearSession, version]);

  if (authStatus === "anonymous") {
    return <p className="text-sm text-muted-foreground">{t.loginRequired}</p>;
  }
  if (authStatus === "loading" || status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  }
  if (status === "error") {
    return (
      <div>
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button
          variant="outline"
          size="lg"
          className="mt-4"
          onClick={() => {
            setStatus("loading");
            setReloadToken((value) => value + 1);
          }}
        >
          {t.retry}
        </Button>
      </div>
    );
  }

  async function addReview() {
    const title = newReview.trim();
    if (!title || addingReview) return;
    setFormError(null);
    setAddingReview(true);
    try {
      const created = await createReviewItem(title, null);
      setReview((current) => [created, ...current]);
      if (reviewRef.current.trim() === title) {
        setNewReview("");
        reviewRef.current = "";
      }
      setFormError(null);
    } catch (caught) {
      handleFailure(caught);
    } finally {
      setAddingReview(false);
    }
  }

  async function toggleReview(item: ReviewItem) {
    setFormError(null);
    try {
      const updated = await setReviewItemDone(item.id, !item.is_done);
      setReview((current) => current.map((entry) => (entry.id === item.id ? updated : entry)));
    } catch (caught) {
      handleFailure(caught);
    }
  }

  async function removeReview(item: ReviewItem) {
    setFormError(null);
    try {
      await deleteReviewItem(item.id);
      setReview((current) => current.filter((entry) => entry.id !== item.id));
    } catch (caught) {
      handleFailure(caught);
    }
  }

  async function addCheatsheet() {
    const title = cheatTitle.trim();
    const content = cheatContent.trim();
    if (!title || !content || addingCheatsheet) return;
    setFormError(null);
    setAddingCheatsheet(true);
    try {
      const created = await createCheatsheet(title, content);
      setCheatsheets((current) => [created, ...current]);
      if (
        cheatTitleRef.current.trim() === title &&
        cheatContentRef.current.trim() === content
      ) {
        setCheatTitle("");
        setCheatContent("");
        cheatTitleRef.current = "";
        cheatContentRef.current = "";
      }
      setFormError(null);
    } catch (caught) {
      handleFailure(caught);
    } finally {
      setAddingCheatsheet(false);
    }
  }

  function startEdit(item: Cheatsheet) {
    setEditingId(item.id);
    setEditTitle(item.title);
    setEditContent(item.content);
    setFormError(null);
  }

  async function saveCheatsheet(item: Cheatsheet) {
    const title = editTitle.trim();
    const content = editContent.trim();
    if (!title || !content || savingEdit) return;
    setSavingEdit(true);
    setFormError(null);
    try {
      const updated = await updateCheatsheet(item.id, title, content);
      setCheatsheets((current) =>
        current.map((entry) => (entry.id === item.id ? updated : entry)),
      );
      setEditingId(null);
    } catch (caught) {
      handleFailure(caught);
    } finally {
      setSavingEdit(false);
    }
  }

  async function removeCheatsheet(item: Cheatsheet) {
    setFormError(null);
    try {
      await deleteCheatsheet(item.id);
      setCheatsheets((current) => current.filter((entry) => entry.id !== item.id));
    } catch (caught) {
      handleFailure(caught);
    }
  }

  async function toggleQuestion(item: SavedQuestion) {
    setFormError(null);
    try {
      const updated = await setSavedQuestionResolved(item.id, !item.is_resolved);
      setQuestions((current) =>
        current.map((entry) => (entry.id === item.id ? updated : entry)),
      );
    } catch (caught) {
      handleFailure(caught);
    }
  }

  async function removeQuestion(item: SavedQuestion) {
    setFormError(null);
    try {
      await deleteSavedQuestion(item.id);
      setQuestions((current) => current.filter((entry) => entry.id !== item.id));
    } catch (caught) {
      handleFailure(caught);
    }
  }

  return (
    <div className="space-y-8">
      {formError ? (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      ) : null}

      <section aria-labelledby="weak-heading" className="rounded-xl border bg-card p-5">
        <h2 id="weak-heading" className="text-lg font-semibold">
          {t.weakTitle}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{t.weakIntro}</p>
        {weak.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.weakEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {weak.map((topic) => (
              <li key={topic.lesson_id}>
                <Link
                  href={`/learn/lessons/${topic.lesson_id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-background px-4 py-3 hover:bg-muted"
                >
                  <span>
                    <span className="block text-sm font-medium">{topic.lesson_title}</span>
                    <span className="text-xs text-muted-foreground">
                      {t.weakLine(topic.best_percent, topic.attempts, topic.module_title)}
                    </span>
                  </span>
                  <Badge variant="destructive">{topic.best_percent} %</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="review-heading" className="rounded-xl border bg-card p-5">
        <h2 id="review-heading" className="text-lg font-semibold">
          {t.reviewTitle}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{t.reviewIntro}</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <label htmlFor="review-title" className="sr-only">
            {t.reviewTitleLabel}
          </label>
          <input
            id="review-title"
            value={newReview}
            maxLength={300}
            onChange={(event) => {
              setNewReview(event.target.value);
              reviewRef.current = event.target.value;
            }}
            placeholder={t.reviewPlaceholder}
            className="h-9 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button size="lg" className="px-4" onClick={addReview} disabled={addingReview}>
            {t.reviewAdd}
          </Button>
        </div>
        {review.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.reviewEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {review.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2"
              >
                <span className={cn("break-words text-sm", item.is_done && "text-muted-foreground line-through")}>
                  {item.title}
                </span>
                <span className="flex items-center gap-2">
                  <Badge variant={item.is_done ? "default" : "outline"}>
                    {item.is_done ? t.reviewDone : t.reviewNotDone}
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={() => toggleReview(item)}>
                    {item.is_done ? t.reviewNotDone : t.reviewDone}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    aria-label={`${t.delete}: ${item.title}`}
                    onClick={() => removeReview(item)}
                  >
                    {t.delete}
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="questions-heading" className="rounded-xl border bg-card p-5">
        <h2 id="questions-heading" className="text-lg font-semibold">
          {t.questionsTitle}
        </h2>
        {questions.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.questionsEmpty}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {questions.map((item) => (
              <li key={item.id} className="rounded-lg border px-3 py-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <span className="min-w-0 text-sm leading-relaxed break-words">{item.text}</span>
                  <Badge variant={item.is_resolved ? "default" : "outline"}>
                    {item.is_resolved ? t.resolved : t.unresolved}
                  </Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button variant="ghost" size="sm" onClick={() => toggleQuestion(item)}>
                    {item.is_resolved ? t.unresolved : t.resolved}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    aria-label={`${t.delete}: ${item.text}`}
                    onClick={() => removeQuestion(item)}
                  >
                    {t.delete}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="cheatsheets-heading" className="rounded-xl border bg-card p-5">
        <h2 id="cheatsheets-heading" className="text-lg font-semibold">
          {t.cheatsheetsTitle}
        </h2>
        <div className="mt-3 space-y-2">
          <label htmlFor="cheat-title" className="sr-only">
            {t.cheatsheetTitleLabel}
          </label>
          <input
            id="cheat-title"
            value={cheatTitle}
            maxLength={200}
            onChange={(event) => {
              setCheatTitle(event.target.value);
              cheatTitleRef.current = event.target.value;
            }}
            placeholder={t.cheatsheetTitlePlaceholder}
            className="h-9 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <label htmlFor="cheat-content" className="sr-only">
            {t.cheatsheetContentLabel}
          </label>
          <textarea
            id="cheat-content"
            value={cheatContent}
            maxLength={20_000}
            onChange={(event) => {
              setCheatContent(event.target.value);
              cheatContentRef.current = event.target.value;
            }}
            placeholder={t.cheatsheetContentPlaceholder}
            className="min-h-24 w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button
            size="lg"
            className="px-4"
            onClick={addCheatsheet}
            disabled={addingCheatsheet}
          >
            {t.create}
          </Button>
        </div>
        {cheatsheets.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.cheatsheetsEmpty}</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {cheatsheets.map((item) => (
              <li key={item.id} className="rounded-lg border p-3">
                {editingId === item.id ? (
                  <div className="space-y-2">
                    <label htmlFor={`edit-title-${item.id}`} className="sr-only">
                      {t.cheatsheetEditTitle}
                    </label>
                    <input
                      id={`edit-title-${item.id}`}
                      value={editTitle}
                      maxLength={200}
                      onChange={(event) => setEditTitle(event.target.value)}
                      className="h-9 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    />
                    <label htmlFor={`edit-content-${item.id}`} className="sr-only">
                      {t.cheatsheetEditContent}
                    </label>
                    <textarea
                      id={`edit-content-${item.id}`}
                      value={editContent}
                      maxLength={20_000}
                      onChange={(event) => setEditContent(event.target.value)}
                      className="min-h-24 w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        onClick={() => saveCheatsheet(item)}
                        disabled={savingEdit}
                      >
                        {t.saveChanges}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingId(null);
                          setFormError(null);
                        }}
                      >
                        {t.cancel}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold break-words">{item.title}</h3>
                      <div className="flex flex-wrap gap-1">
                        <Button variant="ghost" size="sm" onClick={() => startEdit(item)}>
                          {t.edit}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          aria-label={`${t.delete}: ${item.title}`}
                          onClick={() => removeCheatsheet(item)}
                        >
                          {t.delete}
                        </Button>
                      </div>
                    </div>
                    <p className="mt-1 text-sm leading-relaxed break-words whitespace-pre-line">
                      {item.content}
                    </p>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <p>
        <Link
          href="/profile"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "px-4")}
        >
          ← Профиль
        </Link>
      </p>
    </div>
  );
}
