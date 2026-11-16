"use client";

import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

/**
 * Переключатель светлой и тёмной темы.
 * Текущая тема хранится в классе `dark` на <html>, выбор — в localStorage.
 * Обе иконки отрисованы сразу, нужную показывает CSS — так нет расхождений
 * между серверной и клиентской разметкой.
 */
export function ThemeToggle() {
  function toggleTheme() {
    const root = document.documentElement;
    const next: Theme = root.classList.contains("dark") ? "light" : "dark";
    root.classList.toggle("dark", next === "dark");
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
      aria-label="Переключить тему оформления"
      title="Переключить тему"
    >
      <Sun className="hidden dark:block" />
      <Moon className="dark:hidden" />
    </Button>
  );
}
