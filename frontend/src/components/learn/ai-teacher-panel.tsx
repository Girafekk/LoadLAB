"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { aiContent as t } from "@/content/trainers";
import { ApiError, askAiTeacher, fetchAiHistory } from "@/lib/api";
import type { AiAnswer, AiHistoryItem } from "@/lib/ai-types";

export function AiTeacherPanel({ lessonId }: { lessonId: number }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AiAnswer | null>(null);
  const [history, setHistory] = useState<AiHistoryItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchAiHistory(lessonId, controller.signal)
      .then(setHistory)
      .catch(() => setHistory([]));
    return () => controller.abort();
  }, [lessonId]);

  async function ask() {
    const value = question.trim();
    if (!value || busy) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await askAiTeacher({ lesson_id: lessonId, question: value });
      setAnswer(result);
      setQuestion("");
      setHistory(await fetchAiHistory(lessonId));
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 429
          ? "Слишком много вопросов. Подождите минуту и попробуйте снова."
          : t.error,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-10 rounded-xl border bg-card p-5" aria-labelledby="ai-teacher-title">
      <h2 id="ai-teacher-title" className="text-lg font-semibold">
        {t.title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{t.intro}</p>

      <label htmlFor="ai-question" className="mt-4 block text-sm font-medium">
        {t.placeholder}
      </label>
      <textarea
        id="ai-question"
        value={question}
        maxLength={1000}
        onChange={(event) => setQuestion(event.target.value)}
        className="mt-1 min-h-20 w-full rounded-lg border bg-background px-3 py-2 text-sm"
      />
      <Button className="mt-3" onClick={ask} disabled={busy || !question.trim()}>
        {busy ? t.asking : t.ask}
      </Button>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {answer ? (
        <div className="mt-4 rounded-lg border bg-surface p-4" role="status">
          <p className="text-xs font-medium text-muted-foreground">
            {answer.mode === "simpler" ? t.simpler : t.answer} ·{" "}
            {answer.provider === "llm" ? t.providerLlm : t.providerLocal}
          </p>
          <div className="mt-2 text-sm leading-relaxed whitespace-pre-line">{answer.answer}</div>
        </div>
      ) : null}

      {history.length > 0 ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium">{t.history}</summary>
          <ul className="mt-2 space-y-2">
            {history.map((item) => (
              <li key={item.id} className="rounded border p-2 text-sm">
                <p className="font-medium">{item.question}</p>
                <p className="mt-1 text-muted-foreground whitespace-pre-line">{item.answer}</p>
              </li>
            ))}
          </ul>
        </details>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">{t.noHistory}</p>
      )}
    </section>
  );
}
