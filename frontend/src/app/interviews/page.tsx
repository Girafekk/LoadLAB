import type { Metadata } from "next";

import { InterviewList } from "@/components/interviews/interview-list";
import { interviewsContent } from "@/content/interviews";

export const metadata: Metadata = {
  title: interviewsContent.title,
  description: interviewsContent.intro,
};

export default function InterviewsPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{interviewsContent.title}</h1>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
        {interviewsContent.intro}
      </p>
      <div className="mt-8">
        <InterviewList />
      </div>
    </div>
  );
}
