"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { aiContent as t } from "@/content/trainers";
import { ApiError, askAiTeacher, fetchAiHistory, fetchAiStatus } from "@/lib/api";
import type { AiAnswer, AiHistoryItem, AiStatus } from "@/lib/ai-types";

export function AiTeacherPanel({ lessonId }: { lessonId: number }) {
  const [question, setQuestion] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");
  const [answer, setAnswer] = useState<AiAnswer | null>(null);
  const [history, setHistory] = useState<AiHistoryItem[]>([]);
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const historyRequestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++historyRequestId.current;
    fetchAiHistory(lessonId, controller.signal)
      .then((data) => {
        if (historyRequestId.current === requestId) setHistory(data);
      })
      .catch(() => {
        if (historyRequestId.current === requestId) setHistory([]);
      });
    fetchAiStatus(controller.signal)
      .then(setAiStatus)
      .catch(() => setAiStatus(null));
    return () => controller.abort();
  }, [lessonId]);

  async function askValue(value: string) {
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await askAiTeacher({ lesson_id: lessonId, question: trimmed });
      setAnswer(result);
      setLastQuestion(trimmed);
      setQuestion("");
      const requestId = ++historyRequestId.current;
      const freshHistory = await fetchAiHistory(lessonId);
      if (historyRequestId.current === requestId) setHistory(freshHistory);
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

  function ask() {
    askValue(question);
  }

  return (
    <section className="mt-10 rounded-xl border bg-card p-5" aria-labelledby="ai-teacher-title">
      <h2 id="ai-teacher-title" className="text-lg font-semibold">
        {t.title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{t.intro}</p>
      {aiStatus ? (
        <p className="mt-2 text-xs font-medium text-brand">
          {aiStatus.provider === "deepseek"
            ? `${t.providerDeepSeek}${aiStatus.model ? ` · ${t.model} ${aiStatus.model}` : ""}`
            : aiStatus.external
              ? t.providerLlm
              : t.providerLocal}
        </p>
      ) : null}

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
            {answer.provider === "deepseek"
              ? t.providerDeepSeek
              : answer.provider === "llm"
                ? t.providerLlm
                : t.providerLocal}
          </p>
          <div className="mt-2 text-sm leading-relaxed whitespace-pre-line">{answer.answer}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => askValue(lastQuestion)}
              disabled={busy || !lastQuestion}
            >
              {t.explainAgain}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => askValue("Покажи конкретный пример по теме этого урока.")}
              disabled={busy}
            >
              {t.showExample}
            </Button>
          </div>
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
