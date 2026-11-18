import type { Metadata } from "next";

import { StudyTools } from "@/components/tools/study-tools";
import { toolsContent } from "@/content/tools";

export const metadata: Metadata = {
  title: toolsContent.profileTitle,
  description: toolsContent.profileIntro,
};

export default function ToolsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {toolsContent.profileTitle}
      </h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        {toolsContent.profileIntro}
      </p>
      <div className="mt-8">
        <StudyTools />
      </div>
    </div>
  );
}
