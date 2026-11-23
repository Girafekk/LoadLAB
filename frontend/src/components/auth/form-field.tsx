"use client";

import { useState } from "react";
import type { ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type FormFieldProps = Omit<ComponentProps<"input">, "id"> & {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
};

/** Поле формы: подпись, ввод, подсказка и сообщение об ошибке. */
export function FormField({ id, label, hint, error, ...inputProps }: FormFieldProps) {
  const [revealed, setRevealed] = useState(false);
  const isPassword = inputProps.type === "password";
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  // Подсказка и ошибка показываются по очереди, поэтому в aria-describedby
  // должен попасть только тот элемент, который действительно есть на экране.
  const describedBy = error ? errorId : hintId;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          className={isPassword ? "h-10 px-3 pr-12" : "h-10 px-3"}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...inputProps}
          type={isPassword && revealed ? "text" : inputProps.type}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setRevealed((value) => !value)}
            className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-foreground hover:text-brand"
            aria-label={revealed ? "Скрыть пароль" : "Показать пароль"}
          >
            {revealed ? "скрыть" : "показать"}
          </button>
        ) : null}
      </div>
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : (
        hint && (
          <p id={hintId} className="text-sm text-muted-foreground">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
