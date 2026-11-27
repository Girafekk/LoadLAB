"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

export function JmeterSimulator() {
  const [threads, setThreads] = useState(10);
  const [rampUp, setRampUp] = useState(5);
  const [duration, setDuration] = useState(60);
  const [thinkTime, setThinkTime] = useState(1);
  const [path, setPath] = useState("/api/products");
  const [result, setResult] = useState<string | null>(null);

  function run() {
    const problems: string[] = [];
    if (threads < 1) problems.push("Число потоков должно быть больше 0.");
    if (rampUp < 0) problems.push("Ramp-up не может быть отрицательным.");
    if (duration < 1) problems.push("Длительность должна быть больше 0.");
    if (rampUp > duration) problems.push("Ramp-up больше длительности: часть потоков не успеет выйти.");
    if (thinkTime < 0) problems.push("Think time не может быть отрицательным.");
    if (!path.startsWith("/")) problems.push("Путь должен начинаться с /.");

    if (problems.length) {
      setResult(`Конфигурация неверна:\n${problems.join("\n")}`);
      return;
    }

    const estimatedRps = threads / (thinkTime + 0.2);
    const p95 = Math.round(120 + threads * 4 + thinkTime * 20);
    setResult(
      [
        "Конфигурация корректна.",
        `Ожидаемый RPS ≈ ${estimatedRps.toFixed(1)} (оценка, не реальный прогон).`,
        `Ожидаемый p95 ≈ ${p95} мс при ответе 200 мс (оценка).`,
        `Сценарий: GET ${path}, ${threads} потоков, ramp-up ${rampUp} с, ${duration} с.`,
        "Проверьте на стенде: код 200, непустой ответ, p95 и ошибки.",
      ].join("\n"),
    );
  }

  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium">
          Потоки
          <input type="number" min={1} value={threads} onChange={(e) => setThreads(Number(e.target.value))} className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3" />
        </label>
        <label className="text-sm font-medium">
          Ramp-up, с
          <input type="number" min={0} value={rampUp} onChange={(e) => setRampUp(Number(e.target.value))} className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3" />
        </label>
        <label className="text-sm font-medium">
          Длительность, с
          <input type="number" min={1} value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3" />
        </label>
        <label className="text-sm font-medium">
          Think time, с
          <input type="number" min={0} step="0.1" value={thinkTime} onChange={(e) => setThinkTime(Number(e.target.value))} className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3" />
        </label>
        <label className="text-sm font-medium sm:col-span-2">
          Путь HTTP-запроса
          <input value={path} onChange={(e) => setPath(e.target.value)} className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3 font-mono" />
        </label>
      </div>
      <Button className="mt-4" onClick={run}>Проверить конфигурацию</Button>
      {result ? (
        <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-surface p-4 text-sm leading-relaxed">{result}</pre>
      ) : null}
      <p className="mt-3 text-xs text-muted-foreground">
        Это симулятор конфигурации и оценка метрик, а не запуск JMeter. Реальный прогон — на учебном стенде.
      </p>
    </div>
  );
}
