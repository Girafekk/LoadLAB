import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { course, curriculumWeeks } from "@/content/curriculum";

export const metadata: Metadata = {
  title: "Программа курса",
  description: `Программа курса «${course.title}»: ${course.durationWeeks} недель от основ IT до итогового проекта.`,
};

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
      <p className="mb-2 text-sm font-semibold tracking-wide text-brand uppercase">
        Программа курса
      </p>
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {course.title}
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
        {course.durationWeeks} недель, {course.hoursPerWeek} часов в неделю. Каждая
        неделя — отдельный модуль с короткими уроками, практикой и квизом.
      </p>

      <p className="mt-6 rounded-lg border bg-surface px-4 py-3 text-sm leading-relaxed text-muted-foreground">
        Платформа в разработке: уроки, практика и квизы откроются на следующих
        этапах. Пока здесь можно познакомиться с программой обучения.
      </p>

      <ol className="mt-10 space-y-4">
        {curriculumWeeks.map((week) => (
          <li key={week.number} className="rounded-xl border bg-card p-5 sm:p-6">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <Badge variant="secondary" className="font-mono">
                Неделя {week.number}
              </Badge>
              <h2 className="text-lg font-semibold">{week.title}</h2>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{week.summary}</p>
            <ul className="mt-4 grid gap-x-8 gap-y-1.5 text-sm sm:grid-cols-2">
              {week.topics.map((topic) => (
                <li key={topic} className="flex gap-2">
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand" aria-hidden="true" />
                  {topic}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      <p className="mt-10 text-sm">
        <Link href="/" className="font-medium text-brand underline-offset-4 hover:underline">
          ← Вернуться на главную
        </Link>
      </p>
    </div>
  );
}
