import type { Metadata } from "next";
import { Suspense } from "react";

import { LessonView } from "@/components/learn/lesson-view";
import { learnContent } from "@/content/learn";

export const metadata: Metadata = {
  title: "Урок",
  description: "Урок курса «Нагрузочное тестирование с нуля».",
};

/**
 * Страница урока. Значение из адреса становится известно только во время
 * запроса, поэтому обращение к params обёрнуто в Suspense: так страница
 * получает статический каркас, а содержимое загружается в браузере.
 */
export default function LessonPage({ params }: { params: Promise<{ lessonId: string }> }) {
  return (
    <Suspense
      fallback={
        <p className="mx-auto max-w-2xl px-4 py-16 text-sm text-muted-foreground sm:px-6">
          {learnContent.loadingLesson}
        </p>
      }
    >
      {params.then(({ lessonId }) => {
        // Принимаем только каноническую запись числа: «1e3», «01» и «1abc»
        // не должны превращаться в другой идентификатор урока.
        const id = /^[1-9]\d*$/.test(lessonId) ? Number(lessonId) : null;
        return <LessonView lessonId={id} />;
      })}
    </Suspense>
  );
}
