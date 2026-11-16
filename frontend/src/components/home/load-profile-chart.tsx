/**
 * Иллюстрация для первого экрана: условный профиль нагрузочного теста —
 * разгон (ramp-up), стабильная нагрузка и завершение. Данные демонстрационные.
 */
const METRICS = [
  { label: "Пользователи", value: "200" },
  { label: "Запросов в секунду", value: "480" },
  { label: "p95, мс", value: "310" },
];

export function LoadProfileChart() {
  return (
    <figure className="rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
      <figcaption className="mb-4 flex items-center justify-between gap-3">
        <span className="text-sm font-medium">Профиль нагрузки</span>
        <span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-xs text-muted-foreground">
          пример
        </span>
      </figcaption>

      <svg
        viewBox="0 0 400 180"
        className="w-full"
        role="img"
        aria-label="График: нагрузка плавно растёт, держится на постоянном уровне и снижается"
      >
        <g className="stroke-border" strokeWidth="1">
          <line x1="0" y1="30" x2="400" y2="30" />
          <line x1="0" y1="80" x2="400" y2="80" />
          <line x1="0" y1="130" x2="400" y2="130" />
          <line x1="0" y1="179" x2="400" y2="179" />
        </g>
        <path
          d="M0 179 L110 40 L300 40 L400 179 Z"
          className="fill-primary/10"
        />
        <path
          d="M0 179 L110 40 L300 40 L400 179"
          className="stroke-primary"
          fill="none"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <path
          d="M0 150 C40 148 80 140 110 132 S200 128 300 124 S370 150 400 160"
          className="stroke-muted-foreground/70"
          fill="none"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />
      </svg>

      <div className="mt-1 flex justify-between font-mono text-[0.7rem] text-muted-foreground">
        <span>разгон</span>
        <span>стабильная нагрузка</span>
        <span>завершение</span>
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-3 border-t pt-4">
        {METRICS.map((metric) => (
          <div key={metric.label}>
            <dt className="text-xs text-muted-foreground">{metric.label}</dt>
            <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums">
              {metric.value}
            </dd>
          </div>
        ))}
      </dl>
    </figure>
  );
}
