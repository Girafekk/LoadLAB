import { Section } from "@/components/home/section";
import { Badge } from "@/components/ui/badge";

const FEATURES = [
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
      eyebrow="Уже работает"
      title="Возможности платформы"
      description="Курс, прогресс, квизы и конспекты уже работают. Тренажёры, AI-преподаватель и подготовка к собеседованию доступны в разделе «Тренажёры»."
      className="border-t bg-surface"
    >
      <ul className="grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature) => (
          <li key={feature.title} className="border-t pt-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-base font-semibold">{feature.title}</h3>
              <Badge variant="outline" className="mt-0.5 text-muted-foreground">
                доступно
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.text}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
