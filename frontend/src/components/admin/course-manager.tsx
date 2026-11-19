"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { adminContent as t } from "@/content/admin";
import { adminErrorMessage } from "@/lib/admin-error";
import {
  createAdminCourse,
  createAdminLesson,
  createAdminModule,
  deleteAdminCourse,
  deleteAdminLesson,
  deleteAdminModule,
  fetchAdminCourse,
  fetchAdminCourses,
  moveAdminLesson,
  updateAdminCourse,
  updateAdminLesson,
  updateAdminModule,
} from "@/lib/api";
import type { CourseAdmin, CourseTree, ModuleAdmin } from "@/lib/admin-types";

const inputClass =
  "h-9 rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

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

export function CourseManager() {
  const [courses, setCourses] = useState<CourseAdmin[]>([]);
  const [tree, setTree] = useState<CourseTree | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const [newSlug, setNewSlug] = useState("");
  const [newTitle, setNewTitle] = useState("");
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
    const slug = newSlug.trim();
    const title = newTitle.trim();
    if (!slug || !title) return;
    setError(null);
    try {
      await createAdminCourse({ slug, title, description: null });
      setNewSlug("");
      setNewTitle("");
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
            onChange={(event) => setNewSlug(event.target.value)}
            placeholder={t.slug}
            className={`${inputClass} sm:w-48`}
          />
          <input
            value={newTitle}
            onChange={(event) => setNewTitle(event.target.value)}
            placeholder={t.courseName}
            className={`${inputClass} min-w-0 flex-1`}
          />
          <Button size="lg" className="px-4" onClick={createCourse}>
            {t.create}
          </Button>
        </div>
      </section>

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
