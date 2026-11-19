"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { checkAnalysisExercise, fetchAnalysisExercises } from "@/lib/api";
import type { AnalysisExercise, AnalysisResult } from "@/lib/trainer-types";

export function AnalysisTrainer() {
  const [exercises, setExercises] = useState<AnalysisExercise[]>([]);
  const [selected, setSelected] = useState<AnalysisExercise | null>(null);
  const [option, setOption] = useState<number | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchAnalysisExercises(controller.signal)
      .then((data) => {
        setExercises(data);
        if (data[0]) setSelected(data[0]);
      })
      .catch(() => {
        setError(t.error);
        setExercises([]);
      });
    return () => controller.abort();
  }, []);

  async function check() {
    if (!selected || option === null) return;
    setBusy(true);
    setResult(null);
    try {
      setResult(await checkAnalysisExercise({ exercise_id: selected.id, option_index: option }));
    } catch {
      setResult({ correct: false, feedback: t.error });
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
      <label className="block text-sm font-medium" htmlFor="analysis-exercise">
        {t.choose}
      </label>
      <select
        id="analysis-exercise"
        value={selected?.id ?? ""}
        onChange={(event) => {
          setSelected(exercises.find((item) => item.id === event.target.value) ?? null);
          setOption(null);
          setResult(null);
        }}
        className="h-10 w-full rounded-lg border bg-background px-3 text-sm"
      >
        {exercises.map((item) => (
          <option key={item.id} value={item.id}>
            {item.title}
          </option>
        ))}
      </select>

      {selected ? (
        <fieldset className="rounded-xl border bg-card p-4">
          <legend className="px-1 text-sm font-medium">{selected.title}</legend>
          <p className="mt-2 text-sm leading-relaxed">{selected.situation}</p>
          <div className="mt-3 space-y-2">
            {selected.options.map((item, index) => (
              <label key={index} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="analysis-option"
                  checked={option === index}
                  onChange={() => setOption(index)}
                  className="mt-1"
                />
                {item}
              </label>
            ))}
          </div>
          <Button className="mt-4" onClick={check} disabled={busy || option === null}>
            {t.check}
          </Button>
        </fieldset>
      ) : error ? null : (
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
