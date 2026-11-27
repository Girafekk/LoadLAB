import type { Metadata } from "next";

import { Exams } from "@/components/exams/exams";
import { examsContent } from "@/content/exams";

export const metadata: Metadata = {
  title: examsContent.title,
  description: examsContent.intro,
};

export default function ExamsPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{examsContent.title}</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">{examsContent.intro}</p>
      <div className="mt-8">
        <Exams />
      </div>
    </div>
  );
}
