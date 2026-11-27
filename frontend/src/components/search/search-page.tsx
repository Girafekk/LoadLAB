"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { searchCourse, type SearchResult } from "@/lib/api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setError(null);
    try {
      const data = await searchCourse(query.trim());
      setResults(data.results);
      setTotal(data.total);
    } catch {
      setError("Не удалось выполнить поиск.");
    }
  }

  return (
    <div>
      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
        <label htmlFor="search-query" className="sr-only">Поиск по курсу</label>
        <input
          id="search-query"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Например, p95, корреляция, JMeter"
          className="h-10 min-w-0 flex-1 rounded-lg border border-input bg-background px-3 text-sm"
        />
        <Button type="submit">Найти</Button>
      </form>
      {total !== null ? <p className="mt-3 text-sm text-muted-foreground">Найдено: {total}</p> : null}
      {error ? <p role="alert" className="mt-3 text-sm text-destructive">{error}</p> : null}
      <ul className="mt-4 space-y-2">
        {results.map((item) => (
          <li key={`${item.url}-${item.title}`}>
            <Link href={item.url} className="block rounded-lg border bg-card p-4 hover:bg-muted">
              <span className="text-xs font-medium text-brand">{item.type}</span>
              <span className="mt-1 block font-medium">{item.title}</span>
              <span className="mt-1 block text-xs text-muted-foreground">{item.context}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
