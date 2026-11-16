/**
 * Единая точка общения frontend с backend.
 * Адрес API берётся из переменной окружения NEXT_PUBLIC_API_URL
 * (см. frontend/.env.example).
 */
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

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/health`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Backend ответил со статусом ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
