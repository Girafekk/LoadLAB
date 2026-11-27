"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchReviewQueue, reviewInterviewAnswer } from "@/lib/api";
import type { ReviewItem } from "@/lib/admin-types";

export function AnswerReview() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    fetchReviewQueue(status, 0, 25)
      .then((data) => {
        setItems(data.items);
        setCounts(data.counts);
        setTotal(data.total);
      })
      .catch(() => setError("Не удалось загрузить очередь."));
  }, [status, reload]);

  function patchLocal(id: number, patch: Partial<ReviewItem>) {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function save(item: ReviewItem, next: "approved" | "rejected") {
    setBusy(true);
    setError(null);
    try {
      await reviewInterviewAnswer(item.id, {
        status: next,
        comment: item.review_comment,
        reference_answer: item.reference_answer,
        answer_criteria: item.answer_criteria,
      });
      setItems((current) => current.filter((row) => row.id !== item.id));
      setReload((value) => value + 1);
    } catch {
      setError("Не удалось сохранить проверку.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        {(["pending", "approved", "rejected"] as const).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={status === value ? "default" : "outline"}
            aria-pressed={status === value}
            onClick={() => setStatus(value)}
          >
            {value === "pending" ? "Ожидают" : value === "approved" ? "Приняты" : "Отклонены"} ({counts[value] ?? 0})
          </Button>
        ))}
        <span className="text-sm text-muted-foreground">Всего: {total}</span>
      </div>
      {error ? <p role="alert" className="mt-3 text-sm text-destructive">{error}</p> : null}
      <div className="mt-4 space-y-4">
        {items.map((item) => (
          <section key={item.id} className="rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="min-w-0 font-medium break-words">{item.text}</p>
              <Badge variant={item.review_status === "pending" ? "outline" : "secondary"}>
                {item.review_status}
              </Badge>
            </div>
            {item.topic ? <p className="mt-1 text-xs text-muted-foreground">{item.topic}</p> : null}
            <label className="mt-3 block text-sm font-medium" htmlFor={`answer-${item.id}`}>
              Эталонный ответ
            </label>
            <textarea
              id={`answer-${item.id}`}
              value={item.reference_answer ?? ""}
              onChange={(event) => patchLocal(item.id, { reference_answer: event.target.value })}
              className="mt-1 min-h-28 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm leading-relaxed"
            />
            <label className="mt-3 block text-sm font-medium" htmlFor={`criteria-${item.id}`}>
              Критерии
            </label>
            <textarea
              id={`criteria-${item.id}`}
              value={item.answer_criteria ?? ""}
              onChange={(event) => patchLocal(item.id, { answer_criteria: event.target.value })}
              className="mt-1 min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm leading-relaxed"
            />
            <label className="mt-3 block text-sm font-medium" htmlFor={`comment-${item.id}`}>
              Комментарий
            </label>
            <input
              id={`comment-${item.id}`}
              value={item.review_comment ?? ""}
              onChange={(event) => patchLocal(item.id, { review_comment: event.target.value })}
              className="mt-1 h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" disabled={busy} onClick={() => void save(item, "approved")}>
                Принять
              </Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => void save(item, "rejected")}>
                Отклонить
              </Button>
            </div>
          </section>
        ))}
        {items.length === 0 ? <p className="text-sm text-muted-foreground">Очередь пуста.</p> : null}
      </div>
    </div>
  );
}
