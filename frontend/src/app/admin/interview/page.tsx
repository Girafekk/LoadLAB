import type { Metadata } from "next";

import { InterviewManager } from "@/components/admin/interview-manager";
import { interviewContent } from "@/content/interview";

export const metadata: Metadata = {
  title: interviewContent.title,
};

export default function AdminInterviewPage() {
  return <InterviewManager />;
}
