"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { mockInterviewContent as t } from "@/content/mock-interview";
import { ApiError, fetchMockInterview, fetchMockInterviews, startMockInterview, submitMockAnswer } from "@/lib/api";
import type { MockQuestion, MockReport, MockSession } from "@/lib/mock-interview-types";

export function MockInterview() {
  const { status, version, user, clearSession } = useAuth();
  const owner = user ? `${user.id}:${version}` : null;
  const ownerRef = useRef<string | null>(owner);
  useEffect(() => {
    ownerRef.current = owner;
  }, [owner]);
  const [sessionOwner, setSessionOwner] = useState<string | null>(null);
  const [attempts, setAttempts] = useState<MockSession[]>([]);
  const [session, setSession] = useState<MockSession | null>(null);
  const [current, setCurrent] = useState<MockQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<{ score: number; text: string } | null>(null);
  const [report, setReport] = useState<MockReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [useAi, setUseAi] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    const controller = new AbortController();
    fetchMockInterviews()
      .then((items) => setAttempts(items))
      .catch(() => setAttempts([]));
    return () => controller.abort();
  }, [status, owner]);

  if (status === "loading") {
    return <p className="text-sm text-muted-foreground">{t.starting}</p>;
  }
  if (status !== "authenticated") {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">{t.needAuth}</p>
        <Link
          href="/login?next=%2Fmock-interview"
          className="mt-4 inline-flex rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground"
        >
          {t.login}
        </Link>
      </div>
    );
  }

  async function start() {
    const requestOwner = owner;
    setBusy(true);
    setError(null);
    setReport(null);
    setFeedback(null);
    try {
      const created = await startMockInterview();
      if (requestOwner === null || ownerRef.current !== requestOwner) return;
      setSession(created);
      setSessionOwner(requestOwner);
      setCurrent(created.current);
      setAnswer("");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        clearSession(version);
      } else if (caught instanceof ApiError && caught.status === 422) {
        setError(t.noQuestions);
      } else {
        setError(t.loadError);
      }
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    if (!session || !answer.trim()) return;
    setBusy(true);
    setError(null);
    const requestOwner = owner;
    const answerId = current?.answer_id;
    if (answerId === undefined) return;
    try {
      const result = await submitMockAnswer(
        session.id,
        answer.trim(),
        answerId,
        useAi,
      );
      if (requestOwner === null || ownerRef.current !== requestOwner) return;
      setFeedback({ score: result.score, text: result.feedback });
      setAnswer("");
      setCurrent(result.next_question);
      if (result.completed) {
        const completedReport = await fetchMockInterview(session.id);
        if (ownerRef.current !== requestOwner) return;
        setReport(completedReport);
        setSession((value) => (value ? { ...value, status: "completed" } : value));
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        clearSession(version);
      } else if (caught instanceof ApiError && caught.status === 429) {
        setError(t.tooMany);
      } else {
        setError(t.error);
      }
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setSession(null);
    setSessionOwner(null);
    setCurrent(null);
    setReport(null);
    setFeedback(null);
    setAnswer("");
    setError(null);
    setUseAi(false);
  }

  async function reloadReport() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const completed = await fetchMockInterview(session.id);
      setReport(completed);
      setSession((value) => (value ? { ...value, status: "completed" } : value));
    } catch {
      setError(t.loadError);
    } finally {
      setBusy(false);
    }
  }

  if (session && !current && !report) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button className="mt-4" onClick={() => void reloadReport()} disabled={busy}>
          {t.reportRetry}
        </Button>
      </div>
    );
  }

  if (session && sessionOwner !== owner) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">{t.sessionChanged}</p>
        <Button className="mt-4" onClick={reset}>
          {t.retry}
        </Button>
      </div>
    );
  }

  function resume(item: MockSession) {
    if (item.current === null) return;
    setSession(item);
    setSessionOwner(owner);
    setCurrent(item.current);
    setReport(null);
    setFeedback(null);
    setAnswer("");
    setError(null);
  }

  if (!session) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="max-w-2xl text-sm text-muted-foreground">{t.intro}</p>
        <label className="mt-4 flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={useAi}
            onChange={(event) => setUseAi(event.target.checked)}
            className="mt-1"
          />
          <span>
            {t.useAi}
            <span className="block text-xs text-muted-foreground">{t.useAiHint}</span>
          </span>
        </label>
        {error ? (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button className="mt-4" size="lg" onClick={() => void start()} disabled={busy}>
          {busy ? t.starting : t.start}
        </Button>
        <Link
          href="/trainers"
          className="mt-4 ml-3 inline-flex text-sm text-brand underline-offset-4 hover:underline"
        >
          {t.backToTrainers}
        </Link>
        {attempts.some((item) => item.status === "active" && item.current) ? (
          <div className="mt-4">
            <p className="text-sm font-medium">{t.continueTitle}</p>
            <ul className="mt-2 space-y-2 text-sm">
              {attempts
                .filter((item) => item.status === "active" && item.current)
                .map((item) => (
                  <li key={item.id}>
                    <Button variant="outline" size="sm" onClick={() => resume(item)}>
                      {t.continueSession} #{item.id}
                    </Button>
                  </li>
                ))}
            </ul>
          </div>
        ) : null}
      </div>
    );
  }

  if (report) {
    const max = report.total * 5;
    return (
      <div className="space-y-4">
        <section className="rounded-xl border bg-card p-6">
          <h2 className="text-xl font-semibold">{t.completed}</h2>
          <p className="mt-2 text-2xl font-semibold">{t.score(report.score, max)}</p>
          <Button className="mt-4" onClick={reset}>
            {t.retry}
          </Button>
        </section>
        <section className="rounded-xl border bg-card p-6">
          <h3 className="text-lg font-semibold">{t.report}</h3>
          <ol className="mt-3 space-y-4">
            {report.answers.map((item) => (
              <li key={item.position} className="rounded-lg border p-4 text-sm">
                <p className="font-medium break-words">
                  {item.position}. {item.question}
                </p>
                <p className="mt-2 whitespace-pre-line text-muted-foreground">
                  {item.answer ?? t.noAnswer}
                </p>
                {item.feedback ? (
                  <p className="mt-2 rounded-lg bg-surface px-3 py-2">
                    <span className="font-medium">{t.feedback}: </span>
                    {item.feedback}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border bg-card p-6">
        <p className="text-xs text-muted-foreground">
          {t.question} {current?.position ?? session.total} {t.of} {session.total}
        </p>
        <h2 className="mt-2 text-xl leading-relaxed font-medium break-words">
          {current?.text ?? t.completed}
        </h2>
        {feedback ? (
          <div className="mt-4 rounded-lg bg-surface p-3 text-sm" role="status">
            <p className="font-medium">
              {t.feedback}: {feedback.score} / 5
            </p>
            <p className="mt-1 whitespace-pre-line">{feedback.text}</p>
          </div>
        ) : null}
        {current ? (
          <div className="mt-4">
            <label htmlFor="mock-answer" className="text-sm font-medium">
              {t.answer}
            </label>
            <textarea
              id="mock-answer"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              maxLength={6000}
              placeholder={t.answerPlaceholder}
              className="mt-2 min-h-40 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            />
            <Button
              className="mt-3"
              size="lg"
              onClick={() => void send()}
              disabled={busy || !answer.trim()}
            >
              {busy ? t.sending : t.send}
            </Button>
          </div>
        ) : null}
        {error ? (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </section>
    </div>
  );
}
