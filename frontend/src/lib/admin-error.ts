import { ApiError } from "@/lib/api";

/** Понятное сообщение для ошибок административных запросов. */
export function adminErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Сессия истекла. Войдите снова.";
    if (error.status === 403) return "Недостаточно прав для этого действия.";
    if (error.status === 404) return "Объект не найден. Обновите страницу.";
    if (error.status === 409) return error.message;
    if (error.status === 422) {
      const detail = error.details?.[0]?.message;
      return detail ?? error.message;
    }
    if (error.status >= 500) return "Сервер не смог выполнить действие. Попробуйте позже.";
    return error.message;
  }
  return "Не удалось выполнить действие. Проверьте соединение.";
}
