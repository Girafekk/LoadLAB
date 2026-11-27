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
  InterviewQuestionPage,
  InterviewReport,
  InterviewSource,
  InterviewLibraryDetail,
  InterviewLibrarySource,
  LessonOption,
} from "@/lib/interview-types";
import type {
  ExamModule,
  ExamQuestions,
  ExamResult,
} from "@/lib/exam-types";
import type {
  MockAnswerResult,
  MockReport,
  MockSession,
} from "@/lib/mock-interview-types";
import type {
  BlockInput,
  CourseAdmin,
  CourseImportPreview,
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
  session_id?: string | null;
  session_token?: string | null;
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
let sessionStale = false;
let sessionGeneration = 0;
let activeSessionId: string | null = null;

export function setApiUser(
  userId: number | null,
  sessionId: string | null = null,
): void {
  if (
    userId !== expectedUserId ||
    sessionId !== activeSessionId ||
    sessionStale
  ) {
    sessionGeneration += 1;
  }
  expectedUserId = userId;
  activeSessionId = sessionId;
  sessionStale = false;
}

export function bumpSessionGeneration(): void {
  sessionGeneration += 1;
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
  headers?: Record<string, string>;
  skipUserHeader?: boolean;
  credentials?: RequestCredentials;
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    signal,
    headers: extraHeaders,
    skipUserHeader,
    credentials = "include",
  } = options;
  if (sessionStale && method !== "GET") {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }
  if (sessionStale && !path.startsWith("/auth/") && path !== "/health") {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }

  let response: Response;
  const requestExpectedUserId = expectedUserId;
  const requestGeneration = sessionGeneration;
  try {
    const headers: Record<string, string> = { ...extraHeaders };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (!skipUserHeader && expectedUserId !== null && headers["X-LoadLab-User"] === undefined) {
      headers["X-LoadLab-User"] = String(expectedUserId);
    }
    response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
      method,
      signal,
      cache: "no-store",
      credentials,
      headers: body === undefined && expectedUserId === null ? undefined : headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    if (requestGeneration !== sessionGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }

  if (requestGeneration !== sessionGeneration) {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    if (requestGeneration !== sessionGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    const error = payload?.error;
    if (
      response.status === 409 &&
      response.headers.get("x-session-changed") === "1" &&
      typeof window !== "undefined"
    ) {
      // Сначала снимаем устаревший заголовок: иначе /auth/me повторит его.
      // Поздний 409 старого запроса не должен сбрасывать уже новый ID.
      if (
        expectedUserId === requestExpectedUserId &&
        sessionGeneration === requestGeneration
      ) {
        expectedUserId = null;
        sessionStale = true;
        bumpSessionGeneration();
        window.dispatchEvent(new Event("loadlab:session-changed"));
      }
    }
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? `Сервер ответил со статусом ${response.status}`,
      Array.isArray(error?.details) ? error.details : null,
    );
  }

  if (response.status === 204) return undefined as T;
  let data: T;
  try {
    data = (await response.json()) as T;
  } catch (error) {
    if (requestGeneration !== sessionGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    throw error;
  }
  if (requestGeneration !== sessionGeneration) {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }
  return data;
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export function fetchExamModules(signal?: AbortSignal): Promise<ExamModule[]> {
  return apiRequest<ExamModule[]>("/exams/modules", { signal });
}

export function fetchExamQuestions(
  moduleId: number,
  limit: number,
  signal?: AbortSignal,
): Promise<ExamQuestions> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (moduleId) params.set("module_id", String(moduleId));
  return apiRequest<ExamQuestions>(`/exams/questions?${params}`, { signal });
}

export function submitExam(
  answers: { question_id: number; option_ids: number[] }[],
): Promise<ExamResult> {
  return apiRequest<ExamResult>("/exams/submit", { method: "POST", body: { answers } });
}

export async function registerUser(credentials: Credentials): Promise<SessionUser> {
  const issued = await apiRequest<SessionUser>("/auth/register?token_only=true", {
    method: "POST",
    body: credentials,
  });
  return attachSession(issued.session_token ?? "");
}

export async function loginUser(credentials: Credentials): Promise<SessionUser> {
  const issued = await apiRequest<SessionUser>("/auth/login?token_only=true", {
    method: "POST",
    body: credentials,
  });
  return attachSession(issued.session_token ?? "");
}

async function attachSession(token: string): Promise<SessionUser> {
  if (!token) throw new ApiError(401, "auth_error", "Сессия не создана");
  return apiRequest<SessionUser>("/auth/attach", {
    method: "POST",
    body: { session_token: token },
  });
}

export function logoutUser(userId?: number): Promise<void> {
  return apiRequest<void>("/auth/logout", {
    method: "POST",
    headers: userId ? { "X-LoadLab-User": String(userId) } : undefined,
  });
}

/** Текущий пользователь или `null`, если вход не выполнен. */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<SessionUser | null> {
  try {
    return await apiRequest<SessionUser>("/auth/me", { signal, skipUserHeader: true });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Программа курса с опубликованными уроками. Гость получает `progress: null`. */
export function fetchCourse(
  signal?: AbortSignal,
  authenticated = true,
): Promise<CourseOverview> {
  return apiRequest<CourseOverview>("/courses/current", {
    signal,
    credentials: authenticated ? "include" : "omit",
    skipUserHeader: !authenticated,
  });
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
  clientToken?: string,
): Promise<QuizAttemptResult> {
  return apiRequest<QuizAttemptResult>(`/lessons/${lessonId}/quiz/attempts`, {
    method: "POST",
    body: { answers, client_token: clientToken },
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

export async function previewCourseImport(file: File): Promise<CourseImportPreview> {
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${API_PREFIX}/admin/course-imports/preview`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
  } catch {
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.error?.code ?? "http_error",
      payload?.error?.message ?? payload?.detail ?? "Не удалось разобрать файл",
    );
  }
  return payload as CourseImportPreview;
}

export function approveCourseImport(token: string): Promise<{
  course_id: number;
  title: string;
  modules: number;
  lessons: number;
}> {
  return apiRequest(`/admin/course-imports/${token}/approve`, { method: "POST" });
}

export function cancelCourseImport(token: string): Promise<void> {
  return apiRequest<void>(`/admin/course-imports/${token}`, { method: "DELETE" });
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
  expectedAttemptsCount?: number,
  expectedQuizId?: number,
): Promise<void> {
  const params = new URLSearchParams();
  if (confirmAttemptsLoss) params.set("confirm_attempts_loss", "true");
  if (expectedAttemptsCount !== undefined) {
    params.set("expected_attempts_count", String(expectedAttemptsCount));
  }
  if (expectedQuizId !== undefined) params.set("expected_quiz_id", String(expectedQuizId));
  const query = params.size ? `?${params.toString()}` : "";
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
  if (sessionStale) {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }
  const form = new FormData();
  const requestGeneration = sessionGeneration;
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
    if (sessionGeneration !== requestGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    if (sessionGeneration !== requestGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    const error = payload?.error;
    if (
      response.status === 409 &&
      response.headers.get("x-session-changed") === "1" &&
      sessionGeneration === requestGeneration &&
      typeof window !== "undefined"
    ) {
      expectedUserId = null;
      sessionStale = true;
      bumpSessionGeneration();
      window.dispatchEvent(new Event("loadlab:session-changed"));
    }
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? "Не удалось загрузить файл",
    );
  }
  const data = (await response.json().catch((error: unknown) => {
    if (sessionGeneration !== requestGeneration) {
      throw new ApiError(409, "session_changed", "Сессия изменилась");
    }
    throw error;
  })) as InterviewSource;
  if (sessionGeneration !== requestGeneration) {
    throw new ApiError(409, "session_changed", "Сессия изменилась");
  }
  return data;
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

export function fetchInterviewQuestionPage(
  status: string | undefined,
  offset: number,
  limit: number,
  signal?: AbortSignal,
): Promise<InterviewQuestionPage> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (status) params.set("status", status);
  return apiRequest<InterviewQuestionPage>(`/admin/interview/questions/page?${params}`, { signal });
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

export function fetchInterviewLibrary(signal?: AbortSignal): Promise<InterviewLibrarySource[]> {
  return apiRequest<InterviewLibrarySource[]>("/interviews/sources", { signal });
}

export function fetchInterviewLibraryItem(
  sourceId: number,
  signal?: AbortSignal,
): Promise<InterviewLibraryDetail> {
  return apiRequest<InterviewLibraryDetail>(`/interviews/sources/${sourceId}`, { signal });
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

export function generateInterviewAnswers(allowExternal = false): Promise<{
  generated: number;
  fallback: number;
  total: number;
}> {
  const query = allowExternal ? "?limit=50&allow_external=true" : "?limit=50";
  return apiRequest<{ generated: number; fallback: number; total: number }>(
    `/admin/interview/generate-answers${query}`,
    { method: "POST" },
  );
}

export function startMockInterview(): Promise<MockSession> {
  return apiRequest<MockSession>("/mock-interviews", { method: "POST" });
}

export function submitMockAnswer(
  interviewId: number,
  answer: string,
  answerId: number,
  allowExternal = false,
): Promise<MockAnswerResult> {
  return apiRequest<MockAnswerResult>(`/mock-interviews/${interviewId}/answers`, {
    method: "POST",
    body: { answer, answer_id: answerId, allow_external: allowExternal },
  });
}

export function fetchMockInterview(interviewId: number): Promise<MockReport> {
  return apiRequest<MockReport>(`/mock-interviews/${interviewId}`);
}

export function fetchMockInterviews(): Promise<MockSession[]> {
  return apiRequest<MockSession[]>("/mock-interviews");
}
