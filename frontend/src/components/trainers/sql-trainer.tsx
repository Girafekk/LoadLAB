"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { fetchSqlExercises, runSqlExercise } from "@/lib/api";
import type { SqlExercise, SqlResult } from "@/lib/trainer-types";

export function SqlTrainer() {
  const [exercises, setExercises] = useState<SqlExercise[]>([]);
  const [selected, setSelected] = useState<SqlExercise | null>(null);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SqlResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchSqlExercises(controller.signal)
      .then((data) => {
        setExercises(data);
        if (data[0]) setSelected(data[0]);
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

  async function run() {
    if (!selected || !query.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      setResult(await runSqlExercise({ exercise_id: selected.id, query }));
    } catch {
      setResult({ columns: [], rows: [], correct: false, feedback: t.error });
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
      <label className="block text-sm font-medium" htmlFor="sql-exercise">
        {t.choose}
      </label>
      <select
        id="sql-exercise"
        value={selected?.id ?? ""}
        onChange={(event) => {
          setSelected(exercises.find((item) => item.id === event.target.value) ?? null);
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
          <label className="mt-4 block text-sm font-medium" htmlFor="sql-query">
            {t.query}
          </label>
          <textarea
            id="sql-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="mt-1 min-h-28 w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
            spellCheck={false}
          />
          <Button className="mt-3" onClick={run} disabled={busy}>
            {t.run}
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
          {result.columns.length > 0 ? (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr>
                    {result.columns.map((column) => (
                      <th key={column} scope="col" className="border-b px-2 py-1 font-semibold">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, index) => (
                    <tr key={index} className="border-b">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-2 py-1">
                          {String(cell ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
