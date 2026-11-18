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
