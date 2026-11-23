/** Общие настройки сайта: название и пункты навигации. */
export const siteConfig = {
  name: "LoadLab",
  tagline: "Платформа для обучения нагрузочному тестированию",
  learnHref: "/learn",
  nav: [
    { label: "О платформе", href: "/#about" },
    { label: "Курс", href: "/#course" },
    { label: "Преимущества", href: "/#advantages" },
    { label: "Программа", href: "/learn" },
    { label: "Тренажёры", href: "/trainers" },
    { label: "Разборы", href: "/interviews" },
    { label: "Пробное собеседование", href: "/mock-interview" },
  ],
} as const;
