/** Общие настройки сайта: название и пункты навигации. */
export const siteConfig = {
  name: "LoadLab",
  tagline: "Платформа для обучения нагрузочному тестированию",
  learnHref: "/learn",
  nav: [
    { label: "О платформе", href: "/#about" },
    { label: "Курс", href: "/#course" },
    { label: "Преимущества", href: "/#advantages" },
    { label: "Скоро", href: "/#upcoming" },
    { label: "Программа", href: "/learn" },
    { label: "Тренажёры", href: "/trainers" },
  ],
} as const;
