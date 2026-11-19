"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { aiContent as t } from "@/content/trainers";
import { fetchAiCheatsheet, fetchAiRecommendations } from "@/lib/api";
import type { AiRecommendation, CheatsheetSuggestion } from "@/lib/ai-types";

export function AiStudyHelper() {
  const { status } = useAuth();
  const [recommendations, setRecommendations] = useState<AiRecommendation[]>([]);
  const [cheatsheet, setCheatsheet] = useState<CheatsheetSuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") return;
    const controller = new AbortController();
    fetchAiRecommendations(controller.signal)
      .then(setRecommendations)
      .catch(() => setRecommendations([]));
    return () => controller.abort();
  }, [status]);

  async function suggest() {
    setError(null);
    setBusy(true);
    try {
      setCheatsheet(await fetchAiCheatsheet());
    } catch {
      setError(t.error);
    } finally {
      setBusy(false);
    }
  }

  if (status !== "authenticated") return null;

  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="text-lg font-semibold">{t.recommendations}</h2>
      {recommendations.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{t.noRecommendations}</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm">
          {recommendations.map((item) => (
            <li key={item.lesson_id}>
              <Link
                href={`/learn/lessons/${item.lesson_id}`}
                className="font-medium text-brand underline-offset-4 hover:underline"
              >
                {item.title}
              </Link>{" "}
              <span className="text-muted-foreground">— {item.reason}</span>
            </li>
          ))}
        </ul>
      )}
      <Button variant="outline" size="sm" className="mt-4" onClick={suggest} disabled={busy}>
        {t.cheatsheet}
      </Button>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {cheatsheet ? (
        <div className="mt-3 rounded-lg border bg-surface p-3 text-sm">
          <p className="font-medium">{cheatsheet.title}</p>
          <p className="mt-1 whitespace-pre-line text-muted-foreground">{cheatsheet.content}</p>
        </div>
      ) : null}
    </section>
  );
}
