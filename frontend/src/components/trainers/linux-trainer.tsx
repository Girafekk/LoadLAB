"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { trainersContent as t } from "@/content/trainers";
import { fetchLinuxExercises, runLinuxExercise } from "@/lib/api";
import type { LinuxExercise, LinuxResult } from "@/lib/trainer-types";

export function LinuxTrainer() {
  const [exercises, setExercises] = useState<LinuxExercise[]>([]);
  const [selected, setSelected] = useState<LinuxExercise | null>(null);
  const [command, setCommand] = useState("");
  const [result, setResult] = useState<LinuxResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cwd, setCwd] = useState("/srv/app");

  useEffect(() => {
    const controller = new AbortController();
    fetchLinuxExercises(controller.signal)
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

  async function run() {
    if (!selected || !command.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      const data = await runLinuxExercise({ exercise_id: selected.id, command, cwd });
      setResult(data);
      setCwd(data.cwd);
    } catch {
      setResult({ output: "", cwd: "/srv/app", correct: false, feedback: t.error });
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
      <label className="block text-sm font-medium" htmlFor="linux-exercise">
        {t.choose}
      </label>
      <select
        id="linux-exercise"
        value={selected?.id ?? ""}
        onChange={(event) => {
          setSelected(exercises.find((item) => item.id === event.target.value) ?? null);
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
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm leading-relaxed">{selected.task}</p>
          <p className="mt-2 text-xs text-muted-foreground">{selected.hint}</p>
          <label className="mt-4 block text-sm font-medium" htmlFor="linux-command">
            {t.command}
          </label>
          <input
            id="linux-command"
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") run();
            }}
            className="mt-1 h-10 w-full rounded-lg border bg-background px-3 font-mono text-sm"
            spellCheck={false}
          />
          <Button className="mt-3" onClick={run} disabled={busy}>
            {t.run}
          </Button>
        </div>
      ) : error ? null : (
        <p className="text-sm text-muted-foreground">{t.loading}</p>
      )}

      {result ? (
        <div className="rounded-lg border bg-surface p-4 text-sm" role="status">
          <p className="font-medium">{result.correct ? t.correct : t.wrong}</p>
          <p className="mt-1 text-muted-foreground">{result.feedback}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            {t.cwd}: {result.cwd}
          </p>
          <pre className="mt-2 overflow-x-auto rounded bg-muted p-3 text-xs">{result.output}</pre>
        </div>
      ) : null}
    </div>
  );
}
