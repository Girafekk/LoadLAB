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
  useEffect(() => {
    versionRef.current = version;
  }, [version]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = {
      email: validateEmail(email),
      password: password ? null : errors.passwordRequired,
    };
    setFieldErrors(nextErrors);
    setFormError(null);
    if (nextErrors.email || nextErrors.password) return;

    setSubmitting(true);
    const startVersion = version;
    try {
      const user = await loginUser({ email, password });
      if (versionRef.current !== startVersion) return;
      setUser(user);
    } catch (error) {
      if (versionRef.current !== startVersion) return;
      setFormError(describeAuthError(error));
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
        <Button type="submit" size="lg" className="h-10 w-full text-base" disabled={submitting}>
          {submitting ? text.submitting : text.submit}
        </Button>
      </form>
    </AuthCard>
  );
}
