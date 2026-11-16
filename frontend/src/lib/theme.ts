/** Ключ localStorage, в котором хранится выбранная пользователем тема. */
export const THEME_STORAGE_KEY = "loadlab-theme";

export type Theme = "light" | "dark";

/**
 * Скрипт выполняется до первой отрисовки страницы и выставляет класс `dark`
 * на <html>. Благодаря этому страница не «мигает» светлой темой при загрузке.
 * Порядок: сохранённый выбор пользователя → системная настройка.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}})();`;
