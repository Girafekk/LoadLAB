import type { Metadata } from "next";

import { JmeterSimulator } from "@/components/jmeter/jmeter-simulator";

export const metadata: Metadata = {
  title: "JMeter-симулятор",
  description: "Проверка конфигурации нагрузочного сценария и оценка метрик.",
};

export default function JmeterPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">JMeter-симулятор</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        Проверьте параметры Thread Group до реального прогона: потоки, ramp-up, длительность, think time и путь.
      </p>
      <div className="mt-8">
        <JmeterSimulator />
      </div>
    </div>
  );
}
