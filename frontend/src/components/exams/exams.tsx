"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { examsContent as t } from "@/content/exams";
import { fetchExamModules, fetchExamQuestions, submitExam } from "@/lib/api";
import type { ExamModule, ExamQuestion, ExamResult } from "@/lib/exam-types";

type Answers = Record<number, number[]>;

export function Exams() {
  const [modules, setModules] = useState<ExamModule[]>([]);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [answers, setAnswers] = useState<Answers>({});
  const [result, setResult] = useState<ExamResult | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "ready">("loading");
  const [active, setActive] = useState<number | "final" | null>(null);
  const [history, setHistory] = useState<{ title: string; percent: number; date: string }[]>([]);

  useEffect(() => {
    fetchExamModules()
      .then((data) => {
        setModules(data);
        setStatus("idle");
      })
      .catch(() => setStatus("error"));
    try {
      const frame = requestAnimationFrame(() => {
        try {
          setHistory(JSON.parse(localStorage.getItem("loadlab:exam-history") ?? "[]"));
        } catch {
          setHistory([]);
        }
      });
      return () => cancelAnimationFrame(frame);
    } catch {
      // localStorage может быть недоступен; история просто пустая.
    }
  }, []);

  async function start(moduleId: number | "final") {
    setActive(moduleId);
    setStatus("loading");
    setResult(null);
    setAnswers({});
    try {
      const data = await fetchExamQuestions(moduleId === "final" ? 0 : moduleId, moduleId === "final" ? 20 : 10);
      setQuestions(data.questions);
      setStatus(data.questions.length ? "ready" : "error");
    } catch {
      setStatus("error");
    }
  }

  function toggle(questionId: number, optionId: number) {
    setAnswers((current) => {
      const selected = current[questionId] ?? [];
      return {
        ...current,
        [questionId]: selected.includes(optionId)
          ? selected.filter((id) => id !== optionId)
          : [...selected, optionId],
      };
    });
  }

  async function check() {
    const payload = questions.map((question) => ({
      question_id: question.id,
      option_ids: answers[question.id] ?? [],
    }));
    const data = await submitExam(payload);
    setResult(data);
    const title = active === "final" ? t.final : modules.find((m) => m.id === active)?.title ?? "";
    const next = [{ title, percent: data.percent, date: new Date().toLocaleString("ru-RU") }, ...history].slice(0, 5);
    setHistory(next);
    localStorage.setItem("loadlab:exam-history", JSON.stringify(next));
  }

  return (
    <div>
      <section className="rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.modules}</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {modules.map((module) => (
            <button
              key={module.id}
              type="button"
              onClick={() => void start(module.id)}
              className="rounded-lg border border-input bg-background p-4 text-left transition-colors hover:bg-muted"
            >
              <span className="text-sm font-medium">{module.position}. {module.title}</span>
              <span className="mt-1 block text-xs text-muted-foreground">{module.questions} вопросов</span>
            </button>
          ))}
        </div>
        <div className="mt-4 rounded-lg border border-brand/40 bg-surface p-4">
          <p className="font-medium">{t.final}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t.finalHint}</p>
          <Button className="mt-3" onClick={() => void start("final")}>{t.start}</Button>
        </div>
      </section>

      {status === "loading" ? <p className="mt-6 text-sm text-muted-foreground">{t.loading}</p> : null}
      {status === "error" ? <p className="mt-6 text-sm text-destructive">{t.error}</p> : null}
      {status === "ready" && !result ? (
        <section className="mt-6 space-y-4">
          <p className="text-sm text-muted-foreground">{t.choose}</p>
          {questions.map((question, index) => (
            <fieldset key={question.id} className="rounded-xl border bg-card p-4">
              <legend className="px-1 text-sm font-medium">{index + 1}. {question.text}</legend>
              <div className="mt-3 space-y-2">
                {question.options.map((option) => (
                  <label key={option.id} className="flex cursor-pointer items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={(answers[question.id] ?? []).includes(option.id)}
                      onChange={() => toggle(question.id, option.id)}
                    />
                    <span>{option.text}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <Button onClick={() => void check()}>{t.submit}</Button>
        </section>
      ) : null}

      {result ? (
        <section className="mt-6 rounded-xl border bg-card p-5">
          <p className="text-lg font-semibold">{t.result(result.correct, result.total, result.percent)}</p>
          <div className="mt-4 space-y-2">
            {result.details.map((detail, index) => (
              <div key={detail.question_id} className="rounded-lg border p-3 text-sm">
                <Badge variant={detail.correct ? "secondary" : "destructive"}>
                  {detail.correct ? "Верно" : "Ошибка"} · вопрос {index + 1}
                </Badge>
                <p className="mt-2 text-muted-foreground">{detail.explanation}</p>
              </div>
            ))}
          </div>
          <Button className="mt-4" variant="outline" onClick={() => setResult(null)}>{t.again}</Button>
        </section>
      ) : null}

      {history.length ? (
        <section className="mt-6 rounded-xl border bg-card p-5">
          <h2 className="text-sm font-semibold">{t.history}</h2>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {history.map((item, index) => (
              <li key={`${item.date}-${index}`}>{item.title}: {item.percent} % · {item.date}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
