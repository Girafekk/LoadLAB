/**
 * Единая точка общения frontend с backend.
 * Адрес API берётся из переменной окружения NEXT_PUBLIC_API_URL
 * (см. frontend/.env.example).
 *
 * Вход работает через cookie сессии с флагом httpOnly: браузер сам хранит её
 * и прикладывает к запросам, а JavaScript прочитать её не может. Поэтому здесь
 * нет ни токенов, ни localStorage — только `credentials: "include"`.
 */
import type {
  CourseOverview,
  LessonRead,
  QuizAnswerInput,
  QuizAttemptResult,
  QuizWithHistory,
} from "@/lib/learn-types";

import type {
  AiAnswer,
  AiHistoryItem,
  AiRecommendation,
  AiStatus,
  CheatsheetSuggestion,
} from "@/lib/ai-types";
import type {
  AnalyzeResult,
  InterviewQuestion,
  InterviewReport,
  InterviewSource,
  LessonOption,
} from "@/lib/interview-types";
import type {
  MockAnswerResult,
  MockReport,
  MockSession,
} from "@/lib/mock-interview-types";
import type {
  BlockInput,
  CourseAdmin,
  CourseTree,
  LessonAdmin,
  LessonBriefAdmin,
  ModuleAdmin,
  QuizAdmin,
  QuizPayload,
  StudentProgress,
  StudentProgressDetail,
} from "@/lib/admin-types";
import type {
  AnalysisExercise,
  AnalysisResult,
  CheckResult,
  HttpExercise,
  LinuxExercise,
  LinuxResult,
  SqlExercise,
  SqlResult,
} from "@/lib/trainer-types";
import type {
  Cheatsheet,
  LessonHighlight,
  LessonNote,
  ReviewItem,
  SavedQuestion,
  WeakTopic,
} from "@/lib/tools-types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

const API_PREFIX = "/api/v1";

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: "ok" | "unavailable";
  timestamp: string;
};

export type UserRole = "student" | "admin";

/** Кто сейчас вошёл. */
export type SessionUser = {
  id: number;
  email: string;
  role: UserRole;
};

export type Credentials = {
  email: string;
  password: string;
};

/**
 * Ученик, от имени которого экран собирается действовать. Уходит заголовком
 * `X-LoadLab-User`: если в соседней вкладке уже вошли другим учеником, сервер
 * отклонит запись со старым экраном (409), а не сохранит черновик в чужой аккаунт.
 */
let expectedUserId: number | null = null;

export function setApiUser(userId: number | null): void {
  expectedUserId = userId;
}

type ErrorDetail = { field: string; message: string };

/** Ошибка API в едином формате backend. `status: 0` — сервер недоступен. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: ErrorDetail[] | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;

  let response: Response;
  try {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (expectedUserId !== null) headers["X-LoadLab-User"] = String(expectedUserId);
    response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
      method,
      signal,
      cache: "no-store",
      credentials: "include",
      headers: body === undefined && expectedUserId === null ? undefined : headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = payload?.error;
    if (response.status === 409 && typeof window !== "undefined") {
      // Экран устарел: в другой вкладке сменился ученик. Провайдер авторизации
      // перечитает /auth/me, а личные компоненты пересоздадутся по новому ключу.
      window.dispatchEvent(new Event("loadlab:session-changed"));
    }
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? `Сервер ответил со статусом ${response.status}`,
      Array.isArray(error?.details) ? error.details : null,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export function registerUser(credentials: Credentials): Promise<SessionUser> {
  return apiRequest<SessionUser>("/auth/register", { method: "POST", body: credentials });
}

export function loginUser(credentials: Credentials): Promise<SessionUser> {
  return apiRequest<SessionUser>("/auth/login", { method: "POST", body: credentials });
}

export function logoutUser(): Promise<void> {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}

/** Текущий пользователь или `null`, если вход не выполнен. */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<SessionUser | null> {
  try {
    return await apiRequest<SessionUser>("/auth/me", { signal });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Программа курса с опубликованными уроками. Гость получает `progress: null`. */
export function fetchCourse(signal?: AbortSignal): Promise<CourseOverview> {
  return apiRequest<CourseOverview>("/courses/current", { signal });
}

/**
 * Урок с содержимым. Доступен только после входа: гостю backend отвечает 401,
 * а черновой урок выглядит как отсутствующий (404).
 */
export function fetchLesson(lessonId: number, signal?: AbortSignal): Promise<LessonRead> {
  return apiRequest<LessonRead>(`/lessons/${lessonId}`, { signal });
}

/** Ставит или снимает отметку «урок пройден». Ответ 204 без тела. */
export function setLessonCompleted(lessonId: number, completed: boolean): Promise<void> {
  return apiRequest<void>(`/lessons/${lessonId}/complete`, {
    method: completed ? "POST" : "DELETE",
  });
}

/** Квиз урока с историей попыток. 404 — квиза ещё нет. */
export function fetchLessonQuiz(lessonId: number, signal?: AbortSignal): Promise<QuizWithHistory> {
  return apiRequest<QuizWithHistory>(`/lessons/${lessonId}/quiz`, { signal });
}

/** Отправка ответов. Проверку выполняет только сервер. */
export function submitQuizAttempt(
  lessonId: number,
  answers: QuizAnswerInput[],
): Promise<QuizAttemptResult> {
  return apiRequest<QuizAttemptResult>(`/lessons/${lessonId}/quiz/attempts`, {
    method: "POST",
    body: { answers },
  });
}

// --- Инструменты ученика ---------------------------------------------------------

export function fetchNote(lessonId: number, signal?: AbortSignal): Promise<LessonNote> {
  return apiRequest<LessonNote>(`/lessons/${lessonId}/note`, { signal });
}

export function saveNote(lessonId: number, content: string): Promise<LessonNote> {
  return apiRequest<LessonNote>(`/lessons/${lessonId}/note`, {
    method: "PUT",
    body: { content },
  });
}

export function fetchHighlights(
  lessonId: number,
  signal?: AbortSignal,
): Promise<LessonHighlight[]> {
  return apiRequest<LessonHighlight[]>(`/lessons/${lessonId}/highlights`, { signal });
}

export function addHighlight(lessonId: number, text: string): Promise<LessonHighlight> {
  return apiRequest<LessonHighlight>(`/lessons/${lessonId}/highlights`, {
    method: "POST",
    body: { text },
  });
}

export function deleteHighlight(highlightId: number): Promise<void> {
  return apiRequest<void>(`/highlights/${highlightId}`, { method: "DELETE" });
}

export function fetchSavedQuestions(signal?: AbortSignal): Promise<SavedQuestion[]> {
  return apiRequest<SavedQuestion[]>("/saved-questions", { signal });
}

export function createSavedQuestion(
  text: string,
  lessonId: number | null,
): Promise<SavedQuestion> {
  return apiRequest<SavedQuestion>("/saved-questions", {
    method: "POST",
    body: { text, lesson_id: lessonId },
  });
}

export function setSavedQuestionResolved(
  questionId: number,
  isResolved: boolean,
): Promise<SavedQuestion> {
  return apiRequest<SavedQuestion>(`/saved-questions/${questionId}`, {
    method: "PATCH",
    body: { is_resolved: isResolved },
  });
}

export function deleteSavedQuestion(questionId: number): Promise<void> {
  return apiRequest<void>(`/saved-questions/${questionId}`, { method: "DELETE" });
}

export function fetchReviewItems(signal?: AbortSignal): Promise<ReviewItem[]> {
  return apiRequest<ReviewItem[]>("/review-items", { signal });
}

export function createReviewItem(title: string, note: string | null): Promise<ReviewItem> {
  return apiRequest<ReviewItem>("/review-items", {
    method: "POST",
    body: { title, note },
  });
}

export function setReviewItemDone(itemId: number, isDone: boolean): Promise<ReviewItem> {
  return apiRequest<ReviewItem>(`/review-items/${itemId}`, {
    method: "PATCH",
    body: { is_done: isDone },
  });
}

export function deleteReviewItem(itemId: number): Promise<void> {
  return apiRequest<void>(`/review-items/${itemId}`, { method: "DELETE" });
}

export function fetchCheatsheets(signal?: AbortSignal): Promise<Cheatsheet[]> {
  return apiRequest<Cheatsheet[]>("/cheatsheets", { signal });
}

export function createCheatsheet(title: string, content: string): Promise<Cheatsheet> {
  return apiRequest<Cheatsheet>("/cheatsheets", {
    method: "POST",
    body: { title, content },
  });
}

export function deleteCheatsheet(cheatsheetId: number): Promise<void> {
  return apiRequest<void>(`/cheatsheets/${cheatsheetId}`, { method: "DELETE" });
}

export function updateCheatsheet(
  cheatsheetId: number,
  title: string,
  content: string,
): Promise<Cheatsheet> {
  return apiRequest<Cheatsheet>(`/cheatsheets/${cheatsheetId}`, {
    method: "PATCH",
    body: { title, content },
  });
}

export function fetchWeakTopics(signal?: AbortSignal): Promise<WeakTopic[]> {
  return apiRequest<WeakTopic[]>("/users/me/weak-topics", { signal });
}

// --- Административная панель -----------------------------------------------------

export function fetchAdminCourses(signal?: AbortSignal): Promise<CourseAdmin[]> {
  return apiRequest<CourseAdmin[]>("/admin/courses", { signal });
}

export function createAdminCourse(body: {
  slug: string;
  title: string;
  description: string | null;
}): Promise<CourseAdmin> {
  return apiRequest<CourseAdmin>("/admin/courses", { method: "POST", body });
}

export function fetchAdminCourse(courseId: number, signal?: AbortSignal): Promise<CourseTree> {
  return apiRequest<CourseTree>(`/admin/courses/${courseId}`, { signal });
}

export function updateAdminCourse(
  courseId: number,
  body: { title?: string; description?: string | null; is_published?: boolean },
): Promise<CourseAdmin> {
  return apiRequest<CourseAdmin>(`/admin/courses/${courseId}`, { method: "PATCH", body });
}

export function deleteAdminCourse(courseId: number): Promise<void> {
  return apiRequest<void>(`/admin/courses/${courseId}`, { method: "DELETE" });
}

export function createAdminModule(
  courseId: number,
  body: { title: string; summary: string | null },
): Promise<ModuleAdmin> {
  return apiRequest<ModuleAdmin>(`/admin/courses/${courseId}/modules`, {
    method: "POST",
    body,
  });
}

export function updateAdminModule(
  moduleId: number,
  body: { title?: string; summary?: string | null; position?: number },
): Promise<ModuleAdmin> {
  return apiRequest<ModuleAdmin>(`/admin/modules/${moduleId}`, { method: "PATCH", body });
}

export function deleteAdminModule(moduleId: number): Promise<void> {
  return apiRequest<void>(`/admin/modules/${moduleId}`, { method: "DELETE" });
}

export function createAdminLesson(
  moduleId: number,
  body: { title: string; summary: string | null; estimated_minutes: number },
): Promise<LessonBriefAdmin> {
  return apiRequest<LessonBriefAdmin>(`/admin/modules/${moduleId}/lessons`, {
    method: "POST",
    body,
  });
}

export function fetchAdminLesson(lessonId: number, signal?: AbortSignal): Promise<LessonAdmin> {
  return apiRequest<LessonAdmin>(`/admin/lessons/${lessonId}`, { signal });
}

export function updateAdminLesson(
  lessonId: number,
  body: {
    title?: string;
    summary?: string | null;
    estimated_minutes?: number;
    position?: number;
    is_published?: boolean;
  },
): Promise<LessonAdmin> {
  return apiRequest<LessonAdmin>(`/admin/lessons/${lessonId}`, { method: "PATCH", body });
}

export function deleteAdminLesson(lessonId: number): Promise<void> {
  return apiRequest<void>(`/admin/lessons/${lessonId}`, { method: "DELETE" });
}

export function moveAdminLesson(
  lessonId: number,
  direction: "up" | "down",
): Promise<LessonAdmin> {
  return apiRequest<LessonAdmin>(`/admin/lessons/${lessonId}/move`, {
    method: "POST",
    body: { direction },
  });
}

export function replaceAdminBlocks(
  lessonId: number,
  blocks: BlockInput[],
): Promise<LessonAdmin> {
  return apiRequest<LessonAdmin>(`/admin/lessons/${lessonId}/blocks`, {
    method: "PUT",
    body: { blocks },
  });
}

export function fetchAdminQuiz(
  lessonId: number,
  signal?: AbortSignal,
): Promise<QuizAdmin | null> {
  return apiRequest<QuizAdmin | null>(`/admin/lessons/${lessonId}/quiz`, { signal });
}

export function replaceAdminQuiz(lessonId: number, body: QuizPayload): Promise<QuizAdmin> {
  return apiRequest<QuizAdmin>(`/admin/lessons/${lessonId}/quiz`, { method: "PUT", body });
}

export function deleteAdminQuiz(
  lessonId: number,
  confirmAttemptsLoss = false,
): Promise<void> {
  const query = confirmAttemptsLoss ? "?confirm_attempts_loss=true" : "";
  return apiRequest<void>(`/admin/lessons/${lessonId}/quiz${query}`, {
    method: "DELETE",
  });
}

export function fetchAdminStudents(signal?: AbortSignal): Promise<StudentProgress[]> {
  return apiRequest<StudentProgress[]>("/admin/students", { signal });
}

export function fetchAdminStudent(
  userId: number,
  signal?: AbortSignal,
): Promise<StudentProgressDetail> {
  return apiRequest<StudentProgressDetail>(`/admin/students/${userId}`, { signal });
}

// --- Тренажёры ------------------------------------------------------------------

export function fetchHttpExercises(signal?: AbortSignal): Promise<HttpExercise[]> {
  return apiRequest<HttpExercise[]>("/trainers/http", { signal });
}

export function checkHttpExercise(body: {
  exercise_id: string;
  method: string;
  path: string;
}): Promise<CheckResult> {
  return apiRequest<CheckResult>("/trainers/http/check", { method: "POST", body });
}

export function fetchSqlExercises(signal?: AbortSignal): Promise<SqlExercise[]> {
  return apiRequest<SqlExercise[]>("/trainers/sql", { signal });
}

export function runSqlExercise(body: {
  exercise_id: string;
  query: string;
}): Promise<SqlResult> {
  return apiRequest<SqlResult>("/trainers/sql/run", { method: "POST", body });
}

export function fetchLinuxExercises(signal?: AbortSignal): Promise<LinuxExercise[]> {
  return apiRequest<LinuxExercise[]>("/trainers/linux", { signal });
}

export function runLinuxExercise(body: {
  exercise_id: string;
  command: string;
  cwd?: string;
}): Promise<LinuxResult> {
  return apiRequest<LinuxResult>("/trainers/linux/run", { method: "POST", body });
}

export function fetchAnalysisExercises(signal?: AbortSignal): Promise<AnalysisExercise[]> {
  return apiRequest<AnalysisExercise[]>("/trainers/analysis", { signal });
}

export function checkAnalysisExercise(body: {
  exercise_id: string;
  option_index: number;
}): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>("/trainers/analysis/check", { method: "POST", body });
}

// --- AI Teacher -----------------------------------------------------------------

export function askAiTeacher(body: {
  lesson_id: number;
  question: string;
}): Promise<AiAnswer> {
  return apiRequest<AiAnswer>("/ai/teacher/ask", { method: "POST", body });
}

export function fetchAiHistory(
  lessonId: number | null,
  signal?: AbortSignal,
): Promise<AiHistoryItem[]> {
  const query = lessonId === null ? "" : `?lesson_id=${lessonId}`;
  return apiRequest<AiHistoryItem[]>(`/ai/teacher/history${query}`, { signal });
}

export function fetchAiStatus(signal?: AbortSignal): Promise<AiStatus> {
  return apiRequest<AiStatus>("/ai/teacher/status", { signal });
}

export function fetchAiRecommendations(signal?: AbortSignal): Promise<AiRecommendation[]> {
  return apiRequest<AiRecommendation[]>("/ai/teacher/recommendations", { signal });
}

export function fetchAiCheatsheet(signal?: AbortSignal): Promise<CheatsheetSuggestion> {
  return apiRequest<CheatsheetSuggestion>("/ai/teacher/cheatsheet", { signal });
}

export async function uploadInterviewSource(file: File): Promise<InterviewSource> {
  const form = new FormData();
  form.append("file", file);
  const headers: Record<string, string> = {};
  if (expectedUserId !== null) headers["X-LoadLab-User"] = String(expectedUserId);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${API_PREFIX}/admin/interview/sources`, {
      method: "POST",
      credentials: "include",
      headers,
      body: form,
    });
  } catch {
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = payload?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? "Не удалось загрузить файл",
    );
  }
  return (await response.json()) as InterviewSource;
}

export function fetchInterviewSources(signal?: AbortSignal): Promise<InterviewSource[]> {
  return apiRequest<InterviewSource[]>("/admin/interview/sources", { signal });
}

export function analyzeInterviewSource(
  sourceId: number,
  allowExternal = false,
): Promise<AnalyzeResult> {
  const query = allowExternal ? "?allow_external=true" : "";
  return apiRequest<AnalyzeResult>(`/admin/interview/sources/${sourceId}/analyze${query}`, {
    method: "POST",
  });
}

export function fetchInterviewQuestions(
  status?: string,
  signal?: AbortSignal,
): Promise<InterviewQuestion[]> {
  const query = status ? `?status=${status}` : "";
  return apiRequest<InterviewQuestion[]>(`/admin/interview/questions${query}`, { signal });
}

export function updateInterviewQuestion(
  questionId: number,
  data: Partial<Pick<InterviewQuestion, "topic" | "difficulty" | "level" | "status" | "lesson_id">>,
): Promise<InterviewQuestion> {
  return apiRequest<InterviewQuestion>(`/admin/interview/questions/${questionId}`, {
    method: "PATCH",
    body: data,
  });
}

export function fetchInterviewReport(signal?: AbortSignal): Promise<InterviewReport> {
  return apiRequest<InterviewReport>("/admin/interview/report", { signal });
}

export function fetchInterviewLessons(signal?: AbortSignal): Promise<LessonOption[]> {
  return apiRequest<LessonOption[]>("/admin/interview/lessons", { signal });
}

export function approveAllInterviewQuestions(): Promise<{ approved: number }> {
  return apiRequest<{ approved: number }>("/admin/interview/approve-all", { method: "POST" });
}

export function deduplicateInterviewQuestions(): Promise<{ removed: number }> {
  return apiRequest<{ removed: number }>("/admin/interview/deduplicate", { method: "POST" });
}

export function generateInterviewAnswers(): Promise<{
  generated: number;
  fallback: number;
  total: number;
}> {
  return apiRequest<{ generated: number; fallback: number; total: number }>(
    "/admin/interview/generate-answers?limit=50",
    { method: "POST" },
  );
}

export function startMockInterview(): Promise<MockSession> {
  return apiRequest<MockSession>("/mock-interviews", { method: "POST" });
}

export function submitMockAnswer(
  interviewId: number,
  answer: string,
  answerId?: number,
): Promise<MockAnswerResult> {
  return apiRequest<MockAnswerResult>(`/mock-interviews/${interviewId}/answers`, {
    method: "POST",
    body: answerId === undefined ? { answer } : { answer, answer_id: answerId },
  });
}

export function fetchMockInterview(interviewId: number): Promise<MockReport> {
  return apiRequest<MockReport>(`/mock-interviews/${interviewId}`);
}
