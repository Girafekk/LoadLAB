import { Section } from "@/components/home/section";
import { Badge } from "@/components/ui/badge";

const FEATURES = [
  {
    title: "Уроки и отслеживание прогресса",
    text: "Личный кабинет, в котором видно, что уже пройдено и что изучать дальше.",
  },
  {
    title: "Интерактивные квизы",
    text: "Проверка знаний с объяснением каждого ответа, результатом в баллах и повторным прохождением.",
  },
  {
    title: "Конспекты и шпаргалки",
    text: "Собственные заметки к урокам, важные определения и список тем для повторения.",
  },
  {
    title: "Учебные тренажёры",
    text: "Практика HTTP-запросов, SQL и разбора результатов тестов прямо в браузере.",
  },
  {
    title: "AI-преподаватель",
    text: "Объяснит сложную тему другими словами и подскажет, что стоит повторить.",
  },
  {
    title: "Подготовка к собеседованию",
    text: "Разбор реальных вопросов с собеседований и дополнительные квизы на их основе.",
  },
];

export function UpcomingFeatures() {
  return (
    <Section
      id="upcoming"
      eyebrow="Скоро"
      title="Будущие возможности платформы"
      description="LoadLab развивается поэтапно. Эти функции запланированы и появятся на следующих этапах разработки."
      className="border-t bg-surface"
    >
      <ul className="grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature) => (
          <li key={feature.title} className="border-t pt-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-base font-semibold">{feature.title}</h3>
              <Badge variant="outline" className="mt-0.5 text-muted-foreground">
                в планах
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.text}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
