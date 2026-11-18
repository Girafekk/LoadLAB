import { authContent, PASSWORD_MIN_LENGTH } from "@/content/auth";
import { ApiError } from "@/lib/api";

const { errors } = authContent;

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PASSWORD_MAX_LENGTH = 128;

/**
 * Проверки в браузере нужны только для удобства: человек сразу видит, что
 * исправить. Настоящая проверка всегда выполняется на сервере.
 */
export function validateEmail(value: string): string | null {
  const email = value.trim();
  if (!email) return errors.emailRequired;
  if (!EMAIL_PATTERN.test(email)) return errors.emailInvalid;
  return null;
}

export function validateNewPassword(value: string): string | null {
  if (!value) return errors.passwordRequired;
  if (value.length < PASSWORD_MIN_LENGTH) return errors.passwordTooShort;
  if (value.length > PASSWORD_MAX_LENGTH) return errors.passwordTooLong;
  return null;
}

/** Переводит ошибку API в понятный человеку текст. */
export function describeAuthError(error: unknown): string {
  if (!(error instanceof ApiError)) return errors.unknown;
  switch (error.code) {
    case "network_error":
      return errors.network;
    case "unauthorized":
      return errors.invalidCredentials;
    case "conflict":
      return errors.emailTaken;
    case "forbidden":
      return errors.accountDisabled;
    case "too_many_requests":
      return errors.tooManyAttempts;
    case "validation_error":
      return errors.invalidData;
    default:
      return errors.unknown;
  }
}

export const DEFAULT_AFTER_LOGIN_PATH = "/learn";

// Страницы, которые сами перенаправляют вошедшего человека дальше.
const AUTH_PAGES = ["/login", "/register"];

// Адрес-заглушка: нужен только для разбора путей, на него ничего не отправляется.
const SITE_ORIGIN = "http://localhost";

const CONTROL_CHARS = /[\u0000-\u001F\u007F]/;

/**
 * Куда перейти после входа. Принимаются только пути внутри сайта («/profile»):
 * иначе ссылкой вида /login?next=https://чужой-сайт можно было бы увести
 * человека на посторонний адрес.
 */
export function safeNextPath(next: string | null): string {
  // Управляющие символы браузеры вырезают из адреса, поэтому «/\t/evil.com»
  // читается как «//evil.com». Такие адреса не принимаем вовсе.
  if (
    !next ||
    !next.startsWith("/") ||
    next.startsWith("//") ||
    next.includes("\\") ||
    CONTROL_CHARS.test(next)
  ) {
    return DEFAULT_AFTER_LOGIN_PATH;
  }

  let url: URL;
  try {
    url = new URL(next, SITE_ORIGIN);
  } catch {
    return DEFAULT_AFTER_LOGIN_PATH;
  }

  // Только свой сайт: чужой адрес сюда попасть не должен.
  if (url.origin !== SITE_ORIGIN) return DEFAULT_AFTER_LOGIN_PATH;

  let path: string;
  try {
    path = decodeURIComponent(url.pathname);
  } catch {
    // Некорректная процентная запись — адрес считаем подозрительным.
    return DEFAULT_AFTER_LOGIN_PATH;
  }
  if (!path.startsWith("/") || path.startsWith("//") || CONTROL_CHARS.test(path)) {
    return DEFAULT_AFTER_LOGIN_PATH;
  }

  // Возврат на вход или регистрацию дал бы бесконечный круг: эти страницы
  // сразу отправляют вошедшего дальше.
  if (AUTH_PAGES.includes(path.replace(/\/+$/, ""))) return DEFAULT_AFTER_LOGIN_PATH;

  // Отдаём приведённый к обычному виду адрес, а не исходную строку.
  return `${url.pathname}${url.search}${url.hash}`;
}
