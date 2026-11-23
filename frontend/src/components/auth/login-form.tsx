"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { AuthCard, FormError } from "@/components/auth/auth-card";
import { useAuth } from "@/components/auth/auth-provider";
import { FormField } from "@/components/auth/form-field";
import { useAuthRedirect } from "@/components/auth/use-auth-redirect";
import { Button } from "@/components/ui/button";
import { authContent } from "@/content/auth";
import { loginUser } from "@/lib/api";
import { describeAuthError, validateEmail } from "@/lib/auth-forms";

const { fields, login: text, errors } = authContent;

export function LoginForm() {
  const { setUser, version } = useAuth();
  const { withNext } = useAuthRedirect();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string | null; password?: string | null }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const versionRef = useRef(version);
  const mountedRef = useRef(true);
  useEffect(() => {
    versionRef.current = version;
  }, [version]);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    const nextErrors = {
      email: validateEmail(email),
      password: password ? null : errors.passwordRequired,
    };
    setFieldErrors(nextErrors);
    setFormError(null);
    if (nextErrors.email || nextErrors.password) {
      const first = nextErrors.email ? "email" : "password";
      requestAnimationFrame(() => document.getElementById(first)?.focus());
      return;
    }

    setSubmitting(true);
    const startVersion = version;
    try {
      const user = await loginUser({ email, password });
      if (!mountedRef.current || versionRef.current !== startVersion) return;
      setUser(user);
    } catch (error) {
      if (!mountedRef.current || versionRef.current !== startVersion) return;
      setFormError(describeAuthError(error));
      requestAnimationFrame(() => document.getElementById("email")?.focus());
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title={text.title}
      description={text.description}
      footer={
        <>
          {text.switchQuestion}{" "}
          <Link
            href={withNext("/register")}
            className="font-medium text-brand underline-offset-4 hover:underline"
          >
            {text.switchLink}
          </Link>
        </>
      }
    >
      {/*
        method и action заданы намеренно: если обработчик не успел подключиться
        (не загрузился JS, задержалась гидратация), браузер отправит форму
        обычным POST и пароль не попадёт в адресную строку и журналы.
      */}
      <form
        onSubmit={handleSubmit}
        method="post"
        action="/login"
        noValidate
        aria-busy={submitting}
        className="space-y-5"
      >
        <FormError message={formError} />
        <FormField
          id="email"
          name="email"
          type="email"
          label={fields.email}
          placeholder={fields.emailPlaceholder}
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldErrors.email}
        />
        <FormField
          id="password"
          name="password"
          type="password"
          label={fields.password}
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
        />
        <Button type="submit" size="lg" aria-busy={submitting} aria-disabled={submitting} className="h-10 w-full text-base">
          {submitting ? text.submitting : text.submit}
        </Button>
      </form>
    </AuthCard>
  );
}
