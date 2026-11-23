"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { adminErrorMessage } from "@/lib/admin-error";
import {
  approveCourseImport,
  cancelCourseImport,
  createAdminCourse,
  createAdminLesson,
  createAdminModule,
  deleteAdminCourse,
  deleteAdminLesson,
  deleteAdminModule,
  fetchAdminCourse,
  fetchAdminCourses,
  moveAdminLesson,
  previewCourseImport,
  updateAdminCourse,
  updateAdminLesson,
  updateAdminModule,
} from "@/lib/api";
import type {
  CourseAdmin,
  CourseImportPreview,
  CourseTree,
  ModuleAdmin,
} from "@/lib/admin-types";

const inputClass =
  "h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const TRANSLIT: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh",
  з: "z", и: "i", й: "y", к: "k", л: "l", м: "m", н: "n", о: "o",
  п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "ts",
  ч: "ch", ш: "sh", щ: "sch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu",
  я: "ya",
};

/** Адрес курса: латиница, цифры и дефис; кириллица транслитерируется. */
function toSlug(value: string): string {
  return value
    .toLowerCase()
    .split("")
    .map((char) => TRANSLIT[char] ?? char)
    .join("")
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function AddLessonForm({
  module,
  onCreated,
}: {
  module: ModuleAdmin;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const value = title.trim();
    if (!value || saving) return;
    setSaving(true);
    setError(null);
    try {
      await createAdminLesson(module.id, {
        title: value,
        summary: null,
        estimated_minutes: 90,
      });
      setTitle("");
      onCreated();
    } catch (error) {
      setError(adminErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder={t.lessonName}
        aria-label={t.lessonName}
        className={`${inputClass} min-w-0 flex-1`}
      />
      <Button size="sm" onClick={submit} disabled={saving}>
        {t.add}
      </Button>
      {error ? (
        <p role="alert" className="w-full text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function CourseImportSection({ onCreated }: { onCreated: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CourseImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function parse() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setPreview(await previewCourseImport(file));
    } catch (caught) {
      setError(adminErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!preview || busy) return;
    setBusy(true);
    setError(null);
    try {
      await approveCourseImport(preview.token);
      setPreview(null);
      setFile(null);
      setMessage(t.importDone);
      onCreated();
    } catch (caught) {
      setError(adminErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="text-lg font-semibold">{t.importTitle}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{t.importHint}</p>
      <p className="mt-1 text-xs text-warning-text">{t.importPrivacy}</p>
      <a
        href="/course-import-template.docx"
        className="mt-2 inline-block text-sm font-medium text-brand underline underline-offset-4"
      >
        {t.importTemplate}
      </a>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-lg border border-input bg-background px-3 py-2 text-sm focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
          <span className="font-medium">{t.importChoose}</span>
          <span className="truncate text-muted-foreground">{file?.name ?? t.importEmpty}</span>
          <input
            type="file"
            accept=".txt,.md,.pdf,.doc,.docx"
            aria-label={t.importTitle}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setPreview(null);
              setError(null);
              setMessage(null);
            }}
            className="sr-only"
          />
        </label>
        <Button size="lg" className="px-4" onClick={parse} disabled={!file || busy}>
          {busy ? "Разбираю…" : t.importPreview}
        </Button>
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="mt-2 text-sm text-success">
          {message}
        </p>
      ) : null}
      {preview ? (
        <div className="mt-4 rounded-lg border bg-surface p-4">
          <p className="font-medium">{preview.course.title}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Модулей: {preview.course.modules.length} · уроков:{" "}
            {preview.course.modules.reduce((sum, module) => sum + module.lessons.length, 0)} ·{" "}
            символов: {preview.source_chars} · {preview.course.used_ai ? "AI-разбор" : "локальный разбор"}
          </p>
          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
            {preview.course.modules.map((module) => (
              <details key={`${module.position}-${module.title}`} className="rounded border bg-background p-2">
                <summary className="cursor-pointer text-sm font-medium">{module.title}</summary>
                <ul className="mt-2 space-y-1 pl-4 text-sm text-muted-foreground">
                  {module.lessons.map((lesson) => (
                    <li key={`${module.position}-${lesson.position}-${lesson.title}`}>
                      <p>{lesson.title} · блоков: {lesson.blocks.length}</p>
                      {typeof lesson.blocks[0]?.content.text === "string" ? (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {lesson.blocks[0].content.text}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">{t.importNoQuiz}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" onClick={approve} disabled={busy}>
              {busy ? "Создаю…" : t.importApprove}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                if (preview) void cancelCourseImport(preview.token).catch(() => {});
                setPreview(null);
                setFile(null);
              }}
              disabled={busy}
            >
              {t.importCancel}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function CourseManager() {
  const [courses, setCourses] = useState<CourseAdmin[]>([]);
  const [tree, setTree] = useState<CourseTree | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const [newSlug, setNewSlug] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [newModuleTitle, setNewModuleTitle] = useState("");
  const treeRequestId = useRef(0);

  function loadCourses() {
    fetchAdminCourses()
      .then((data) => {
        setCourses(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    loadCourses();
  }, []);

  async function openCourse(courseId: number) {
    setError(null);
    setTree(null);
    const requestId = ++treeRequestId.current;
    try {
      const data = await fetchAdminCourse(courseId);
      if (treeRequestId.current === requestId) setTree(data);
    } catch {
      if (treeRequestId.current === requestId) setError(t.loadError);
    }
  }

  async function refreshTree() {
    if (tree) setTree(await fetchAdminCourse(tree.id));
  }

  async function createCourse() {
    const title = newTitle.trim();
    const slug = toSlug(newSlug.trim() || title);
    if (!slug || !title) {
      setError(t.slugRequired);
      return;
    }
    setError(null);
    try {
      await createAdminCourse({ slug, title, description: null });
      setNewSlug("");
      setNewTitle("");
      setSlugEdited(false);
      loadCourses();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function toggleCourse(course: CourseAdmin) {
    setError(null);
    try {
      await updateAdminCourse(course.id, { is_published: !course.is_published });
      loadCourses();
      if (tree?.id === course.id) await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function renameCourse(course: CourseAdmin) {
    const title = window.prompt(t.courseName, course.title)?.trim();
    if (!title) return;
    try {
      await updateAdminCourse(course.id, { title });
      loadCourses();
      if (tree?.id === course.id) await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function editCourseDescription(course: CourseAdmin) {
    const description = window.prompt(t.description, course.description ?? "");
    if (description === null) return;
    try {
      await updateAdminCourse(course.id, {
        description: description.trim() ? description : null,
      });
      loadCourses();
      if (tree?.id === course.id) await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function renameModule(module: ModuleAdmin) {
    const title = window.prompt(t.moduleName, module.title)?.trim();
    if (!title) return;
    try {
      await updateAdminModule(module.id, { title });
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function moveLesson(lessonId: number, direction: "up" | "down") {
    try {
      await moveAdminLesson(lessonId, direction);
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function removeLesson(lessonId: number) {
    if (!window.confirm(t.confirmDelete)) return;
    try {
      await deleteAdminLesson(lessonId);
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function toggleLesson(lessonId: number, isPublished: boolean) {
    setError(null);
    try {
      await updateAdminLesson(lessonId, { is_published: !isPublished });
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function addModule() {
    const title = newModuleTitle.trim();
    if (!title || !tree) return;
    setError(null);
    try {
      await createAdminModule(tree.id, { title, summary: null });
      setNewModuleTitle("");
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function removeModule(module: ModuleAdmin) {
    if (!window.confirm(`${t.confirmDelete}: ${module.title}`)) return;
    try {
      await deleteAdminModule(module.id);
      await refreshTree();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  async function removeCourse(course: CourseAdmin) {
    if (!window.confirm(`${t.confirmDelete}: ${course.title}`)) return;
    try {
      await deleteAdminCourse(course.id);
      if (tree?.id === course.id) setTree(null);
      loadCourses();
    } catch (error) {
      setError(adminErrorMessage(error));
    }
  }

  if (status === "loading") return <p className="text-sm text-muted-foreground">{t.loading}</p>;
  if (status === "error") {
    return (
      <div>
        <p className="text-sm text-muted-foreground">{t.loadError}</p>
        <Button variant="outline" size="lg" className="mt-4" onClick={loadCourses}>
          {t.retry}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <section className="rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.newCourse}</h2>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            value={newSlug}
            onChange={(event) => {
              setNewSlug(toSlug(event.target.value));
              setSlugEdited(true);
            }}
            placeholder={t.slug}
            aria-label={t.slug}
            className={`${inputClass} sm:w-48`}
          />
          <input
            value={newTitle}
            onChange={(event) => {
              const value = event.target.value;
              setNewTitle(value);
              if (!slugEdited) setNewSlug(toSlug(value));
            }}
            placeholder={t.courseName}
            aria-label={t.courseName}
            className={`${inputClass} min-w-0 flex-1`}
          />
          <Button size="lg" className="px-4" onClick={createCourse}>
            {t.create}
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{t.slugHint}</p>
      </section>

      <CourseImportSection onCreated={loadCourses} />

      <section className="rounded-xl border bg-card p-5">
        <h2 className="text-lg font-semibold">{t.courseTitle}</h2>
        {courses.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">{t.noCourses}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {courses.map((course) => (
              <li
                key={course.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium break-words">{course.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {course.slug} · модулей: {course.module_count} · уроков:{" "}
                    {course.lesson_count}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={course.is_published ? "default" : "outline"}>
                    {course.is_published ? t.published : t.draft}
                  </Badge>
                  <Button variant="outline" size="sm" onClick={() => toggleCourse(course)}>
                    {course.is_published ? t.unpublish : t.publish}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => renameCourse(course)}>
                    {t.edit}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editCourseDescription(course)}
                  >
                    {t.description}
                  </Button>
                  <Button size="sm" onClick={() => openCourse(course.id)}>
                    {t.open}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => removeCourse(course)}
                  >
                    {t.delete}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {tree ? (
        <section className="rounded-xl border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">{tree.title}</h2>
            <Badge variant={tree.is_published ? "default" : "outline"}>
              {tree.is_published ? t.published : t.draft}
            </Badge>
          </div>

          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={newModuleTitle}
              onChange={(event) => setNewModuleTitle(event.target.value)}
              placeholder={t.moduleName}
              aria-label={t.moduleName}
              className={`${inputClass} min-w-0 flex-1`}
            />
            <Button size="lg" className="px-4" onClick={addModule}>
              {t.newModule}
            </Button>
          </div>

          <ul className="mt-4 space-y-3">
            {tree.modules.map((module) => (
              <li key={module.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold break-words">
                    {module.position}. {module.title}
                  </h3>
                  <span className="flex flex-wrap gap-1">
                    <Button variant="ghost" size="sm" onClick={() => renameModule(module)}>
                      {t.edit}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => removeModule(module)}
                    >
                      {t.delete}
                    </Button>
                  </span>
                </div>
                <ul className="mt-2 space-y-1">
                  {module.lessons.map((lesson) => (
                    <li
                      key={lesson.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-surface px-2 py-1.5"
                    >
                      <span className="min-w-0 text-sm break-words">
                        {lesson.position}. {lesson.title}
                      </span>
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge variant={lesson.is_published ? "default" : "outline"}>
                          {lesson.is_published ? t.published : t.draft}
                        </Badge>
                        <Link
                          href={`/admin/lessons/${lesson.id}`}
                          className="text-xs font-medium text-brand underline-offset-4 hover:underline"
                        >
                          {t.openLesson}
                        </Link>
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => toggleLesson(lesson.id, lesson.is_published)}
                        >
                          {lesson.is_published ? t.unpublish : t.publish}
                        </Button>
                        <Button
                          variant="ghost"
                          size="xs"
                          aria-label="Выше"
                          onClick={() => moveLesson(lesson.id, "up")}
                        >
                          ↑
                        </Button>
                        <Button
                          variant="ghost"
                          size="xs"
                          aria-label="Ниже"
                          onClick={() => moveLesson(lesson.id, "down")}
                        >
                          ↓
                        </Button>
                        <Button
                          variant="ghost"
                          size="xs"
                          className="text-destructive"
                          onClick={() => removeLesson(lesson.id)}
                        >
                          {t.delete}
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
                <AddLessonForm module={module} onCreated={refreshTree} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
