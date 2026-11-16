import { ArrowRight, CalendarDays, Clock, GraduationCap } from "lucide-react";
import Link from "next/link";

import { Section } from "@/components/home/section";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { course, curriculumWeeks } from "@/content/curriculum";
import { siteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

const FACTS = [
  { icon: CalendarDays, label: `${course.durationWeeks} недель` },
  { icon: Clock, label: `${course.hoursPerWeek} часов в неделю` },
  { icon: GraduationCap, label: `Уровень: ${course.level.toLowerCase()}` },
];

export function CourseCard() {
  return (
    <Section
      id="course"
      eyebrow="Основной курс"
      title="С чего начать"
      description="Одна последовательная программа, которая ведёт от базовых понятий к самостоятельному проекту."
      className="border-y bg-surface"
    >
      <Card className="[--card-spacing:--spacing(6)]">
        <CardHeader>
          <CardTitle className="text-xl font-semibold sm:text-2xl">
            «{course.title}»
          </CardTitle>
          <CardDescription className="max-w-3xl text-base leading-relaxed">
            {course.description}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <ul className="flex flex-col gap-3 text-sm sm:flex-row sm:flex-wrap sm:gap-x-8">
            {FACTS.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-2">
                <Icon className="size-4 text-brand" aria-hidden="true" />
                {label}
              </li>
            ))}
          </ul>

          <ol className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            {curriculumWeeks.map((week) => (
              <li key={week.number} className="flex gap-3">
                <span className="w-16 shrink-0 font-mono text-xs leading-5 text-muted-foreground">
                  Неделя {week.number}
                </span>
                <span>{week.title}</span>
              </li>
            ))}
          </ol>

          <ul className="flex flex-wrap gap-2" aria-label="Инструменты и технологии курса">
            {course.tools.map((tool) => (
              <li key={tool}>
                <Badge variant="secondary">{tool}</Badge>
              </li>
            ))}
          </ul>
        </CardContent>

        <CardFooter>
          <Link
            href={siteConfig.learnHref}
            className={cn(buttonVariants({ size: "lg" }), "h-10 px-4")}
          >
            Смотреть программу курса
            <ArrowRight data-icon="inline-end" />
          </Link>
        </CardFooter>
      </Card>
    </Section>
  );
}
