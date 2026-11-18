"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { fetchCurrentUser, logoutUser, type SessionUser } from "@/lib/api";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: SessionUser | null;
  /** Вызывается после успешного входа или регистрации. */
  setUser: (user: SessionUser) => void;
  /**
   * Помечает сессию завершённой без обращения к серверу: например, когда
   * backend ответил 401 на запрос со страницы урока. Нужно, чтобы страница
   * входа не отправляла человека обратно к недоступному уроку.
   */
  clearSession: () => void;
  /** Завершает сессию на сервере. При ошибке бросает исключение. */
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Хранит сведения о том, кто вошёл, для всего интерфейса.
 * Сама сессия живёт в httpOnly-cookie и на сервере; здесь только результат
 * запроса GET /auth/me — чтобы показать нужные кнопки.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setCurrentUser] = useState<SessionUser | null>(null);

  // Ставится, как только человек вошёл или вышел сам. Ответ /auth/me,
  // отправленный до этого момента, уже неактуален: применить его нельзя,
  // иначе медленный стартовый запрос затрёт только что выполненный вход.
  const authChangedByUser = useRef(false);

  useEffect(() => {
    const controller = new AbortController();

    fetchCurrentUser(controller.signal)
      .then((currentUser) => {
        if (authChangedByUser.current) return;
        setCurrentUser(currentUser);
        setStatus(currentUser ? "authenticated" : "anonymous");
      })
      .catch(() => {
        // Сервер недоступен: считаем посетителя гостем.
        if (!authChangedByUser.current && !controller.signal.aborted) {
          setStatus("anonymous");
        }
      });

    return () => controller.abort();
  }, []);

  const setUser = useCallback((nextUser: SessionUser) => {
    authChangedByUser.current = true;
    setCurrentUser(nextUser);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    // Отмечаем до запроса: пока он идёт, старый ответ /auth/me уже не должен
    // вернуть в интерфейс завершённую сессию.
    authChangedByUser.current = true;
    await logoutUser();
    setCurrentUser(null);
    setStatus("anonymous");
  }, []);

  const clearSession = useCallback(() => {
    authChangedByUser.current = true;
    setCurrentUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo(
    () => ({ status, user, setUser, clearSession, logout }),
    [status, user, setUser, clearSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth можно вызывать только внутри AuthProvider");
  return context;
}
