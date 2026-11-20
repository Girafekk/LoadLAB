import type { Metadata } from "next";

import { MockInterview } from "@/components/mock-interview/mock-interview";
import { mockInterviewContent } from "@/content/mock-interview";

export const metadata: Metadata = {
  title: mockInterviewContent.title,
};

export default function MockInterviewPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1 className="mb-6 text-3xl font-semibold tracking-tight">{mockInterviewContent.title}</h1>
      <MockInterview />
    </div>
  );
}
