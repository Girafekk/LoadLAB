"use client";

import { useState } from "react";

import { glossaryTerms } from "@/content/glossary";

export function Glossary() {
  const [query, setQuery] = useState("");
  const normalized = query.trim().toLowerCase();
  const terms = glossaryTerms.filter(
    (item) =>
      !normalized ||
      item.term.toLowerCase().includes(normalized) ||
      item.definition.toLowerCase().includes(normalized),
  );

  return (
    <div>
      <label htmlFor="glossary-search" className="text-sm font-medium">
        Поиск термина
      </label>
      <input
        id="glossary-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Например, p95 или корреляция"
        className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
      />
      <p className="mt-2 text-sm text-muted-foreground">Найдено: {terms.length}</p>
      <dl className="mt-4 divide-y rounded-xl border bg-card">
        {terms.map((item) => (
          <div key={item.term} className="p-4">
            <dt className="font-semibold">{item.term}</dt>
            <dd className="mt-1 text-sm leading-relaxed text-muted-foreground">{item.definition}</dd>
            {item.lesson ? <dd className="mt-1 text-xs text-brand">Урок {item.lesson}</dd> : null}
          </div>
        ))}
      </dl>
    </div>
  );
}
