import type { Metadata } from "next";

import { Trainers } from "@/components/trainers/trainers";
import { trainersContent } from "@/content/trainers";

export const metadata: Metadata = {
  title: trainersContent.title,
  description: trainersContent.intro,
};

export default function TrainersPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{trainersContent.title}</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        {trainersContent.intro}
      </p>
      <div className="mt-8">
        <Trainers />
      </div>
    </div>
  );
}
