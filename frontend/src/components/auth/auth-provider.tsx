"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { fetchCurrentUser, logoutUser, setApiUser, type SessionUser } from "@/lib/api";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: SessionUser | null;
  /**
   * Номер версии сессии. Меняется при входе, выходе и сбросе.
   * Асинхронный ответ обрабатывается только для той версии, с которой начался
   * запрос: запоздалый 401 не должен разлогинить только что выполненный вход.
   */
  version: number;
  /** Вызывается после успешного входа или регистрации. */
  setUser: (user: SessionUser) => void;
  /**
   * Помечает сессию завершённой без обращения к серверу. Если передан номер
   * версии, сброс происходит только при совпадении: ответ старого запроса
   * не трогает новую сессию.
   */
  clearSession: (expectedVersion?: number) => void;
  /** Завершает сессию на сервере. При ошибке бросает исключение. */
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_CHANNEL = "loadlab-auth";

/**
 * Хранит сведения о том, кто вошёл, для всего интерфейса.
 * Сама сессия живёт в httpOnly-cookie и на сервере; здесь только результат
 * запроса GET /auth/me — чтобы показать нужные кнопки.
 *
 * Вкладки синхронизируются через BroadcastChannel, а при возврате фокуса
 * состояние перечитывается: вход в соседней вкладке не должен оставлять
 * старый экран с чужим учеником.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setCurrentUser] = useState<SessionUser | null>(null);
  const [version, setVersion] = useState(0);

  // Ставится, как только человек вошёл или вышел сам. Ответ /auth/me,
  // отправленный до этого момента, уже неактуален.
  const authChangedByUser = useRef(false);
  const versionRef = useRef(0);
  const userRef = useRef<SessionUser | null>(null);
  const channelRef = useRef<BroadcastChannel | null>(null);

  const applyUser = useCallback((nextUser: SessionUser | null) => {
    userRef.current = nextUser;
    setApiUser(nextUser?.id ?? null);
    setCurrentUser(nextUser);
    setStatus(nextUser ? "authenticated" : "anonymous");
  }, []);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      let currentUser: SessionUser | null;
      try {
        currentUser = await fetchCurrentUser(signal);
      } catch (error) {
        // Один повтор для временного сбоя сети: иначе секундная недоступность
        // сервера выглядит как «вы не вошли».
        if (signal?.aborted) throw error;
        await new Promise((resolve) => setTimeout(resolve, 500));
        currentUser = await fetchCurrentUser(signal);
      }
      if (authChangedByUser.current) return;
      if ((currentUser?.id ?? null) !== (userRef.current?.id ?? null)) {
        versionRef.current += 1;
        setVersion(versionRef.current);
      }
      applyUser(currentUser);
    },
    [applyUser],
  );

  const bumpVersion = useCallback(() => {
    versionRef.current += 1;
    setVersion(versionRef.current);
    return versionRef.current;
  }, []);

  const notifyOtherTabs = useCallback(() => {
    channelRef.current?.postMessage({ type: "changed" });
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    refresh(controller.signal).catch(() => {
      // Сервер недоступен: считаем посетителя гостем, но при возврате
      // фокуса или сообщении из другой вкладки попробуем снова.
      if (!authChangedByUser.current && !controller.signal.aborted) {
        setStatus("anonymous");
      }
    });

    let channel: BroadcastChannel | null = null;
    if (typeof BroadcastChannel !== "undefined") {
      channel = new BroadcastChannel(AUTH_CHANNEL);
      channel.onmessage = () => {
        authChangedByUser.current = false;
        refresh().catch(() => undefined);
      };
    }
    channelRef.current = channel;

    const onFocus = () => {
      if (document.visibilityState !== "visible") return;
      authChangedByUser.current = false;
      refresh().catch(() => undefined);
    };
    const onSessionChanged = () => {
      // Сервер отклонил запрос старого экрана: перечитываем владельца сессии.
      authChangedByUser.current = false;
      refresh().catch(() => undefined);
    };

    window.addEventListener("focus", onFocus);
    window.addEventListener("loadlab:session-changed", onSessionChanged);

    return () => {
      controller.abort();
      channel?.close();
      channelRef.current = null;
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("loadlab:session-changed", onSessionChanged);
    };
  }, [refresh]);

  const setUser = useCallback(
    (nextUser: SessionUser) => {
      authChangedByUser.current = true;
      bumpVersion();
      applyUser(nextUser);
      notifyOtherTabs();
    },
    [applyUser, bumpVersion, notifyOtherTabs],
  );

  const logout = useCallback(async () => {
    // Версия меняется до запроса: пока он идёт, старые ответы не должны
    // вернуть завершённую сессию. Если за это время человек войдёт снова,
    // номер версии изменится, и завершение выхода не тронет новый вход.
    const logoutVersion = bumpVersion();
    authChangedByUser.current = true;

    await logoutUser();

    if (versionRef.current !== logoutVersion) return;
    applyUser(null);
    notifyOtherTabs();
  }, [applyUser, bumpVersion, notifyOtherTabs]);

  const clearSession = useCallback(
    (expectedVersion?: number) => {
      if (expectedVersion !== undefined && expectedVersion !== versionRef.current) return;
      authChangedByUser.current = true;
      bumpVersion();
      applyUser(null);
      notifyOtherTabs();
    },
    [applyUser, bumpVersion, notifyOtherTabs],
  );

  const value = useMemo(
    () => ({ status, user, version, setUser, clearSession, logout }),
    [status, user, version, setUser, clearSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth можно вызывать только внутри AuthProvider");
  return context;
}
