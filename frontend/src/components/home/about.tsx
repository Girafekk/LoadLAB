import { Section } from "@/components/home/section";

const FACTS = [
  {
    title: "Для кого",
    text: "Для тех, кто начинает путь в IT или переходит из смежной области. Глубокие знания программирования не нужны — всё необходимое объясняется по ходу курса.",
  },
  {
    title: "Чему учит",
    text: "Понимать, как работают веб-приложения, создавать и запускать нагрузочные тесты в Apache JMeter, читать метрики и находить узкие места в системе.",
  },
  {
    title: "Какой результат",
    text: "Практические навыки уровня Junior Load Tester, собственный итоговый проект и готовность отвечать на типовые вопросы технического собеседования.",
  },
];

export function About() {
  return (
    <Section
      id="about"
      eyebrow="О платформе"
      title="Образовательная платформа для будущих нагрузочных тестировщиков"
      description="LoadLab объединяет теорию, практику и проверку знаний в одном месте. Нагрузочное тестирование отвечает на вопрос: выдержит ли система, когда ей начнут пользоваться тысячи людей одновременно. Мы учим находить ответ на него."
    >
      <dl className="grid gap-6 md:grid-cols-3">
        {FACTS.map((fact) => (
          <div key={fact.title} className="border-l-2 border-brand/60 pl-4">
            <dt className="text-base font-semibold">{fact.title}</dt>
            <dd className="mt-2 text-sm leading-relaxed text-muted-foreground">{fact.text}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
