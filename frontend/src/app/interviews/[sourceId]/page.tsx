import type { Metadata } from "next";
import { Suspense } from "react";

import { InterviewDetail } from "@/components/interviews/interview-detail";
import { interviewsContent } from "@/content/interviews";

export const metadata: Metadata = {
  title: interviewsContent.title,
  description: interviewsContent.intro,
};

export default function InterviewDetailPage({
  params,
}: {
  params: Promise<{ sourceId: string }>;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <Suspense
        fallback={<p className="text-sm text-muted-foreground">{interviewsContent.loadingOne}</p>}
      >
        {params.then(({ sourceId }) => {
          const id = /^[1-9]\d*$/.test(sourceId) ? Number(sourceId) : null;
          return <InterviewDetail sourceId={id} />;
        })}
      </Suspense>
    </div>
  );
}
