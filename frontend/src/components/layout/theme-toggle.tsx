"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

/**
 * Переключатель светлой и тёмной темы.
 * Текущая тема хранится в классе `dark` на <html>, выбор — в localStorage.
 * Обе иконки отрисованы сразу, нужную показывает CSS — так нет расхождений
 * между серверной и клиентской разметкой.
 */
export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setDark(document.documentElement.classList.contains("dark"));
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function toggleTheme() {
    const root = document.documentElement;
    const next: Theme = root.classList.contains("dark") ? "light" : "dark";
    root.classList.toggle("dark", next === "dark");
    setDark(next === "dark");
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // localStorage может быть недоступен (приватный режим) — тема
      // всё равно переключится, просто не запомнится.
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon-lg"
      onClick={toggleTheme}
      aria-pressed={dark}
      aria-label={dark ? "Включить светлую тему" : "Включить тёмную тему"}
      title={dark ? "Включить светлую тему" : "Включить тёмную тему"}
    >
      <Sun className="hidden dark:block" />
      <Moon className="dark:hidden" />
    </Button>
  );
}
