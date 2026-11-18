"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";

import { AuthCard, FormError } from "@/components/auth/auth-card";
import { useAuth } from "@/components/auth/auth-provider";
import { FormField } from "@/components/auth/form-field";
import { useAuthRedirect } from "@/components/auth/use-auth-redirect";
import { Button } from "@/components/ui/button";
import { authContent } from "@/content/auth";
import { registerUser } from "@/lib/api";
import { describeAuthError, validateEmail, validateNewPassword } from "@/lib/auth-forms";

const { fields, register: text, errors } = authContent;

type FieldErrors = {
  email?: string | null;
  password?: string | null;
  passwordRepeat?: string | null;
};

export function RegisterForm() {
  const { setUser } = useAuth();
  const { withNext } = useAuthRedirect();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordRepeat, setPasswordRepeat] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: FieldErrors = {
      email: validateEmail(email),
      password: validateNewPassword(password),
      passwordRepeat: password === passwordRepeat ? null : errors.passwordMismatch,
    };
    setFieldErrors(nextErrors);
    setFormError(null);
    if (nextErrors.email || nextErrors.password || nextErrors.passwordRepeat) return;

    setSubmitting(true);
    try {
      // После setUser переход выполнит useAuthRedirect.
      setUser(await registerUser({ email, password }));
    } catch (error) {
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
            href={withNext("/login")}
            className="font-medium text-brand underline-offset-4 hover:underline"
          >
            {text.switchLink}
          </Link>
        </>
      }
    >
      {/*
        Запасной путь без JS: обычный POST, а не GET с паролем в адресе.
        Смотри login-form.tsx — там то же решение и та же причина.
      */}
      <form
        onSubmit={handleSubmit}
        method="post"
        action="/register"
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
          hint={fields.passwordHint}
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
        />
        <FormField
          id="password-repeat"
          name="password-repeat"
          type="password"
          label={fields.passwordRepeat}
          autoComplete="new-password"
          value={passwordRepeat}
          onChange={(event) => setPasswordRepeat(event.target.value)}
          error={fieldErrors.passwordRepeat}
        />
        <Button type="submit" size="lg" className="h-10 w-full text-base" disabled={submitting}>
          {submitting ? text.submitting : text.submit}
        </Button>
      </form>
    </AuthCard>
  );
}
