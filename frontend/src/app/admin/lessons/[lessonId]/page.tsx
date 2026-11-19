import type { Metadata } from "next";
import { Suspense } from "react";

import { LessonEditor } from "@/components/admin/lesson-editor";
import { adminContent } from "@/content/admin";

export const metadata: Metadata = {
  title: adminContent.lessonEditor,
};

export default function AdminLessonPage({
  params,
}: {
  params: Promise<{ lessonId: string }>;
}) {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">{adminContent.loading}</p>}>
      {params.then(({ lessonId }) => {
        const id = /^[1-9]\d*$/.test(lessonId) ? Number(lessonId) : 0;
        return id ? (
          <LessonEditor key={id} lessonId={id} />
        ) : (
          <p className="text-sm text-muted-foreground">{adminContent.loadError}</p>
        );
      })}
    </Suspense>
  );
}
