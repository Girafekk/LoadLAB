import type { Metadata } from "next";

import { FinalProjectChecklist } from "@/components/final-project/final-project-checklist";

export const metadata: Metadata = {
  title: "Финальный проект",
  description: "Чек-лист артефактов финального проекта Junior Load Tester.",
};

export default function FinalProjectPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Финальный проект</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        Соберите артефакты проекта: план, сценарий, прогоны, отчёт. Отмечайте пункты по мере готовности.
      </p>
      <div className="mt-8">
        <FinalProjectChecklist />
      </div>
    </div>
  );
}
