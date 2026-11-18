"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";

/**
 * Пересоздаёт форму при смене версии сессии. Next сохраняет состояние
 * клиентских компонентов между переходами, и без ключа введённый пароль
 * мог остаться в поле после выхода.
 */
export function LoginFormGate() {
  const { version } = useAuth();
  return <LoginForm key={`login-${version}`} />;
}

export function RegisterFormGate() {
  const { version } = useAuth();
  return <RegisterForm key={`register-${version}`} />;
}
