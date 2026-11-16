# LoadLab — frontend

Сайт платформы: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui.
Общая инструкция по запуску проекта — в [README.md](../README.md) в корне.

```bash
npm install      # установить зависимости (один раз)
npm run dev      # запуск для разработки: http://localhost:3000
npm run lint     # проверка кода
npm run typecheck
npm run build    # production-сборка
```

Адрес backend задаётся переменной `NEXT_PUBLIC_API_URL` в файле `.env.local`
(образец — `.env.example`). По умолчанию используется `http://localhost:8001`.

Структура папок описана в [ARCHITECTURE.md](../ARCHITECTURE.md).
