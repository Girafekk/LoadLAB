import type { Metadata } from "next";

import { SearchPage } from "@/components/search/search-page";

export const metadata: Metadata = {
  title: "Поиск по курсу",
  description: "Поиск по урокам, квизам и разборам собеседований LoadLab.",
};

export default function SearchRoute() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Поиск по курсу</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        Ищите по урокам, вопросам квизов и разборам собеседований.
      </p>
      <div className="mt-8">
        <SearchPage />
      </div>
    </div>
  );
}
