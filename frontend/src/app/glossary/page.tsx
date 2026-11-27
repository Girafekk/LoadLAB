import type { Metadata } from "next";

import { Glossary } from "@/components/glossary/glossary";

export const metadata: Metadata = {
  title: "Словарь терминов",
  description: "Термины нагрузочного тестирования с пояснениями и ссылками на уроки.",
};

export default function GlossaryPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Словарь терминов</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        Короткие определения терминов, которые встречаются в курсе и на собеседовании.
      </p>
      <div className="mt-8">
        <Glossary />
      </div>
    </div>
  );
}
