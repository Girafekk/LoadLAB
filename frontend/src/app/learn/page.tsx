import type { Metadata } from "next";
import Link from "next/link";

import { CourseProgress } from "@/components/learn/course-progress";
import { Badge } from "@/components/ui/badge";
import { course, curriculumWeeks } from "@/content/curriculum";
import { learnContent } from "@/content/learn";

export const metadata: Metadata = {
  title: learnContent.program,
  description: learnContent.description,
};

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
      <p className="mb-2 text-sm font-semibold tracking-wide text-brand uppercase">
        {learnContent.program}
      </p>
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {course.title}
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
        {learnContent.planIntro}
      </p>

      <p className="mt-6 rounded-lg border bg-surface px-4 py-3 text-sm leading-relaxed text-muted-foreground">
        {learnContent.publicationNote}
      </p>

      <CourseProgress />

      <h2 className="mt-12 text-xl font-semibold">Полная программа</h2>
      <ol className="mt-6 space-y-4">
        {curriculumWeeks.map((week) => (
          <li key={week.number} className="rounded-xl border bg-card p-5 sm:p-6">
            <Badge variant="secondary" className="font-mono">
              {learnContent.week(week.number)}
            </Badge>
            <h3 className="mt-3 text-lg font-semibold">{week.title}</h3>
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
          {learnContent.home}
        </Link>
      </p>
    </div>
  );
}
