"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { fetchAdminStudent, fetchAdminStudents } from "@/lib/api";
import type { StudentProgress, StudentProgressDetail } from "@/lib/admin-types";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

export function StudentsTable() {
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [detail, setDetail] = useState<StudentProgressDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [reloadToken, setReloadToken] = useState(0);
  const detailRequest = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchAdminStudents(controller.signal)
      .then((data) => {
        setStudents(data);
        setStatus("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("error");
      });
    return () => controller.abort();
  }, [reloadToken]);

  function retry() {
    setStatus("loading");
    setReloadToken((value) => value + 1);
  }

  async function openDetail(student: StudentProgress) {
    const requestId = ++detailRequest.current;
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await fetchAdminStudent(student.id);
      if (detailRequest.current === requestId) setDetail(data);
    } catch {
      if (detailRequest.current === requestId) setDetailError(t.loadError);
    } finally {
      if (detailRequest.current === requestId) setDetailLoading(false);
    }
  }

  if (status === "loading") return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  if (status === "error") {
    return (
      <div>
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button variant="outline" size="lg" className="mt-4" onClick={retry}>
          {t.retry}
        </Button>
      </div>
    );
  }

  if (students.length === 0) {
    return <p className="text-sm text-muted-foreground">{t.noStudents}</p>;
  }

  return (
    <div className="space-y-6">
      <ul className="space-y-2 sm:hidden">
        {students.map((student) => (
          <li key={student.id} className="rounded-xl border bg-card p-4">
            <p className="text-sm font-medium break-all">{student.email}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {student.completed_lessons} / {student.total_lessons} ({student.percent} %)
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {t.attempts}: {student.quiz_attempts} · {formatDate(student.last_activity)}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => openDetail(student)}
            >
              {t.studentDetails}
            </Button>
          </li>
        ))}
      </ul>

      <div className="hidden w-full max-w-full min-w-0 overflow-x-auto rounded-xl border bg-card sm:block">
        <table className="w-full min-w-[560px] text-left text-sm">
          <caption className="sr-only">Прогресс учеников</caption>
          <thead className="bg-muted">
            <tr>
              <th scope="col" className="px-3 py-2">Почта</th>
              <th scope="col" className="px-3 py-2">{t.progress}</th>
              <th scope="col" className="px-3 py-2">{t.attempts}</th>
              <th scope="col" className="px-3 py-2">{t.date}</th>
              <th scope="col" className="px-3 py-2"><span className="sr-only">Действия</span></th>
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id} className="border-t">
                <td className="px-3 py-2 break-all">{student.email}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {student.completed_lessons} / {student.total_lessons} ({student.percent} %)
                </td>
                <td className="px-3 py-2">{student.quiz_attempts}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {formatDate(student.last_activity)}
                </td>
                <td className="px-3 py-2">
                  <Button variant="outline" size="sm" onClick={() => openDetail(student)}>
                    {t.studentDetails}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailLoading ? (
        <p className="text-sm text-muted-foreground">{t.loading}</p>
      ) : null}
      {detailError ? (
        <p role="alert" className="text-sm text-destructive">
          {detailError}
        </p>
      ) : null}
      {detail ? (
        <section className="rounded-xl border bg-card p-5">
          <h2 className="text-lg font-semibold break-all">{detail.email}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {detail.completed_lessons} / {detail.total_lessons} ({detail.percent} %)
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {detail.modules.map((module) => (
              <li key={module.module_id} className="flex flex-wrap justify-between gap-2">
                <span className="break-words">{module.title}</span>
                <span className="whitespace-nowrap">
                  {module.completed} / {module.total}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
