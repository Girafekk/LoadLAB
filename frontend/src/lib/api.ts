/**
 * Единая точка общения frontend с backend.
 * Адрес API берётся из переменной окружения NEXT_PUBLIC_API_URL
 * (см. frontend/.env.example).
 *
 * Вход работает через cookie сессии с флагом httpOnly: браузер сам хранит её
 * и прикладывает к запросам, а JavaScript прочитать её не может. Поэтому здесь
 * нет ни токенов, ни localStorage — только `credentials: "include"`.
 */
import type { CourseOverview, LessonRead } from "@/lib/learn-types";

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
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
      method,
      signal,
      cache: "no-store",
      credentials: "include",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, "network_error", "Не удалось связаться с сервером");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = payload?.error;
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
