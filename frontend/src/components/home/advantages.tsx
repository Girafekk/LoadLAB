import { BookOpenText, ListChecks, Route, Wrench } from "lucide-react";

import { Section } from "@/components/home/section";

const ADVANTAGES = [
  {
    icon: BookOpenText,
    title: "Простой язык",
    text: "Сначала объяснение обычными словами и пример из жизни, и только потом — профессиональный термин.",
  },
  {
    icon: Route,
    title: "Маленькие шаги",
    text: "Большие темы разбиты на короткие уроки, которые идут в продуманной последовательности.",
  },
  {
    icon: Wrench,
    title: "Практика на реальных инструментах",
    text: "Apache JMeter, k6, Linux, SQL и Python — то, с чем тестировщик работает каждый день.",
  },
  {
    icon: ListChecks,
    title: "Проверка понимания",
    text: "После каждой темы — квиз с разбором: почему ответ верный или неверный.",
  },
];

export function Advantages() {
  return (
    <Section
      id="advantages"
      eyebrow="Преимущества"
      title="Как устроено обучение"
      description="Методика рассчитана на тех, кто только знакомится с IT: понимание важнее заучивания."
    >
      <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {ADVANTAGES.map(({ icon: Icon, title, text }) => (
          <li key={title} className="rounded-xl border bg-card p-5">
            <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-brand">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            <h3 className="mt-4 text-base font-semibold">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{text}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
