"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { checkHttpExercise, fetchHttpExercises } from "@/lib/api";
import type { CheckResult, HttpExercise } from "@/lib/trainer-types";

export function HttpTrainer() {
  const [exercises, setExercises] = useState<HttpExercise[]>([]);
  const [selected, setSelected] = useState<HttpExercise | null>(null);
  const [method, setMethod] = useState("GET");
  const [path, setPath] = useState("");
  const [result, setResult] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchHttpExercises(controller.signal)
      .then((data) => {
        setExercises(data);
        if (data[0]) {
          setSelected(data[0]);
          setPath("");
        }
        setLoaded(true);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setError(t.error);
        setExercises([]);
        setLoaded(true);
      });
    return () => controller.abort();
  }, []);

  async function check() {
    if (!selected) return;
    setBusy(true);
    setResult(null);
    try {
      setResult(await checkHttpExercise({ exercise_id: selected.id, method, path }));
    } catch {
      setResult({ correct: false, feedback: t.error, expected: null });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <label className="block text-sm font-medium" htmlFor="http-exercise">
        {t.choose}
      </label>
      <select
        id="http-exercise"
        value={selected?.id ?? ""}
        onChange={(event) => {
          const next = exercises.find((item) => item.id === event.target.value) ?? null;
          setSelected(next);
          setPath("");
          setResult(null);
          setShowHint(false);
        }}
        className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
      >
        {exercises.map((item) => (
          <option key={item.id} value={item.id}>
            {item.title}
          </option>
        ))}
      </select>

      {selected ? (
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm leading-relaxed">{selected.task}</p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-1 px-0"
            onClick={() => setShowHint((value) => !value)}
          >
            {showHint ? t.hideHint : t.showHint}
          </Button>
          {showHint ? (
            <p className="mt-1 text-xs text-muted-foreground">{selected.hint}</p>
          ) : null}
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <label className="text-sm">
              <span className="mb-1 block font-medium">{t.method}</span>
              <input
                value={method}
                onChange={(event) => setMethod(event.target.value)}
                className="h-10 w-24 rounded-lg border border-input bg-background px-3 font-mono text-sm"
              />
            </label>
            <label className="min-w-0 flex-1 text-sm">
              <span className="mb-1 block font-medium">{t.path}</span>
              <input
                value={path}
                onChange={(event) => setPath(event.target.value)}
                className="h-10 w-full rounded-lg border border-input bg-background px-3 font-mono text-sm"
              />
            </label>
          </div>
          <Button className="mt-4" onClick={check} disabled={busy}>
            {t.check}
          </Button>
        </div>
      ) : loaded ? (
        <p className="text-sm text-muted-foreground">{t.noExercises}</p>
      ) : (
        <p className="text-sm text-muted-foreground">{t.loading}</p>
      )}

      {result ? (
        <div className="rounded-lg border bg-surface p-4 text-sm" role="status">
          <p className="font-medium">{result.correct ? t.correct : t.wrong}</p>
          <p className="mt-1 text-muted-foreground">{result.feedback}</p>
        </div>
      ) : null}
    </div>
  );
}
