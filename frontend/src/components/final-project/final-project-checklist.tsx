"use client";

import { useEffect, useState } from "react";

const ITEMS = [
  "Описание системы и границ тестирования",
  "Требования и SLA: p95, ошибки, нагрузка",
  "Профиль нагрузки и сценарии",
  "JMeter Test Plan с корреляцией",
  "CSV-параметризация и данные",
  "Load-прогон",
  "Stress-прогон",
  "HTML-отчёт и .jtl",
  "Анализ узких мест",
  "Итоговый отчёт с ограничениями",
];

const KEY = "loadlab:final-project-checklist";

export function FinalProjectChecklist() {
  const [done, setDone] = useState<boolean[]>(Array(ITEMS.length).fill(false));

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const stored = JSON.parse(localStorage.getItem(KEY) ?? "[]");
        if (Array.isArray(stored) && stored.length === ITEMS.length) setDone(stored);
      } catch {
        // ignore broken local storage
      }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function toggle(index: number) {
    const next = done.map((value, itemIndex) => (itemIndex === index ? !value : value));
    setDone(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  }

  const completed = done.filter(Boolean).length;

  return (
    <div>
      <p className="text-sm text-muted-foreground">
        Отмечено {completed} из {ITEMS.length}. Прогресс хранится в этом браузере.
      </p>
      <ul className="mt-4 space-y-2">
        {ITEMS.map((item, index) => (
          <li key={item}>
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border bg-card p-3 text-sm">
              <input type="checkbox" checked={done[index]} onChange={() => toggle(index)} className="mt-0.5" />
              <span>{item}</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-brand" style={{ width: `${(completed / ITEMS.length) * 100}%` }} />
      </div>
    </div>
  );
}
