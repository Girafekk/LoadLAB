import type { Metadata } from "next";

import { AnswerReview } from "@/components/admin/answer-review";

export const metadata: Metadata = {
  title: "Проверка ответов",
  description: "Ручная вычитка эталонных ответов банка собеседований.",
};

export default function AdminAnswersPage() {
  return <AnswerReview />;
}
