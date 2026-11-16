import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { LoadProfileChart } from "@/components/home/load-profile-chart";
import { buttonVariants } from "@/components/ui/button";
import { course } from "@/content/curriculum";
import { siteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

export function Hero() {
  return (
    <section className="border-b bg-surface">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-[1.1fr_1fr] lg:gap-14">
        <div>
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
            <span className="size-1.5 rounded-full bg-brand" aria-hidden="true" />
            Курс на {course.durationWeeks} недель · с нуля до уровня Junior
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Добро пожаловать в <span className="text-brand">LoadLab</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground">
            Учитесь нагрузочному тестированию шаг за шагом: короткие уроки простым
            языком, практика на реальных инструментах и проверка знаний после каждой
            темы.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href={siteConfig.learnHref}
              className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-base")}
            >
              Перейти к обучению
              <ArrowRight data-icon="inline-end" />
            </Link>
            <Link
              href="/#course"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-11 px-5 text-base")}
            >
              Что входит в курс
            </Link>
          </div>
        </div>

        <LoadProfileChart />
      </div>
    </section>
  );
}
