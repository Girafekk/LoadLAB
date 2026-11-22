# LoadLab

Образовательная платформа для обучения нагрузочному тестированию.
Готовы и проверены **этапы 1–3**: фундамент (главная страница, backend, база данных),
модель данных с миграциями и учётные записи со входом. **Этапы 4–13** — ядро LMS,
квизы, инструменты ученика, админка, учебный стенд, контент 9 недель, тренажёры,
AI Teacher, банк вопросов собеседований и пробное собеседование — реализованы
и ожидают внешней проверки. Остальное появится на следующих этапах
(см. [ROADMAP.md](ROADMAP.md)).

## Из чего состоит проект

| Часть | Что это | Аналогия |
|---|---|---|
| **Frontend** | Сайт, который видит пользователь | Витрина и зал магазина |
| **Backend** | Программа на Python, которая обрабатывает запросы сайта | Сотрудники и правила магазина |
| **PostgreSQL** | База данных | Склад, где всё хранится |
| **Docker** | Программа, которая запускает базу и backend в изолированных «контейнерах» | Готовые комнаты со всем нужным оборудованием |

## Что должно быть установлено

| Программа | Зачем | Проверка в терминале |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Запускает базу данных и backend | `docker --version` |
| [Node.js](https://nodejs.org/) 22 или новее | Запускает frontend | `node --version` |
| [Git](https://git-scm.com/) | Хранит историю изменений | `git --version` |

Python отдельно устанавливать **не нужно**: backend работает внутри Docker,
где уже есть Python 3.12.

> Терминал в Windows — это PowerShell. Откройте папку проекта в Проводнике,
> щёлкните правой кнопкой по пустому месту и выберите «Открыть в Терминале».

## Первый запуск (делается один раз)

**1. Создайте файл настроек.** Скопируйте `.env.example` в `.env`:

```bash
copy .env.example .env
```

Откройте `.env` в Блокноте и замените значение `POSTGRES_PASSWORD` на свой пароль
(любой набор латинских букв и цифр). Файл `.env` хранит секреты и в Git не попадает.

**2. Установите зависимости frontend:**

```bash
npm install --prefix frontend
```

## Как запустить проект

Запустите **Docker Desktop** и дождитесь, пока он полностью загрузится.
Затем выполните в терминале из корня проекта две команды.

**Шаг 1. База данных и backend:**

```bash
docker compose --profile backend up -d
```

Первый запуск занимает несколько минут: Docker скачивает PostgreSQL и собирает backend.

**Шаг 2. Frontend** (терминал останется занят — это нормально):

```bash
npm run dev --prefix frontend
```

Теперь откройте в браузере:

| Адрес | Что там |
|---|---|
| http://localhost:3000 | Сайт LoadLab |
| http://localhost:8001/api/v1/health | Ответ backend о своём состоянии |
| http://localhost:8001/api/v1/docs | Документация API (можно отправлять запросы прямо со страницы) |

Внизу сайта есть индикатор: зелёная точка и надпись «Сервер работает» означают,
что frontend, backend и база данных связаны между собой.

## Учебный стенд «Интернет-магазин»

Для практики нагрузочного тестирования есть отдельное приложение. Оно не связано
с основной базой и запускается одной командой:

```bash
docker compose -f training_stand/compose.yaml up -d --build
```

| Адрес | Что там |
|---|---|
| http://localhost:8082 | Магазин: поиск, корзина, заказы |
| http://localhost:8082/api/docs | Swagger API для JMeter, k6 и Python |

Учебные пользователи: `student1@example.com` … `student3@example.com`, пароль
`password123`. Подробности, сценарии и сброс данных — в
[training_stand/README.md](training_stand/README.md).

## ИИ-чат с DeepSeek

ИИ-чат встроен в каждый урок. Без ключа он работает локально по материалу урока.
Чтобы подключить DeepSeek, добавьте в `.env`:

```bash
DEEPSEEK_API_KEY=ваш-ключ
DEEPSEEK_MODEL=deepseek-chat
```

Затем пересоздайте backend, чтобы он прочитал окружение:

```bash
docker compose --profile backend up -d --force-recreate backend
```

Проверка провайдера: `GET /api/v1/ai/teacher/status` покажет `deepseek` и модель.
Ключ хранится только в `.env` и не передаётся в Git.

## Язык курса

Уроки и ответы написаны простым русским языком: сначала бытовой пример,
затем термин, пример из теста и граница применимости. Правила —
[docs/LANGUAGE_STYLE.md](docs/LANGUAGE_STYLE.md).

## Вопросы с собеседований
Администратор открывает `/admin/interview` и загружает TXT, PDF, DOCX или
скриншот PNG/JPG. Backend извлекает текст (для изображений — OCR), DeepSeek
разбирает его на вопросы, темы и сложность, а затем показывает отчёт покрытия
курса. Вопросы можно привязать к уроку, подтвердить или отклонить.

Ученик проходит `/mock-interview`: пять подтверждённых вопросов, ответ текстом,
разбор и баллы. Если вопросов ещё нет, администратор сначала подтверждает их в
банке. Отчёт по реальным материалам: [docs/INTERVIEW_GAP_REPORT.md](docs/INTERVIEW_GAP_REPORT.md).

## Учебный стенд: остановка и удаление данных

```bash
docker compose -f training_stand/compose.yaml down
docker compose -f training_stand/compose.yaml down -v
```

## Запуск по частям

### Только PostgreSQL

```bash
docker compose up -d
```

Проверить состояние (в колонке STATUS должно быть `healthy`):

```bash
docker compose ps
```

Зайти в базу и выполнить SQL-запрос:

```bash
docker compose exec db psql -U loadlab -d loadlab
```

Выход из `psql` — команда `\q`.

### Backend

```bash
docker compose --profile backend up -d
```

Backend сам перезапускается, когда вы меняете файлы в папке `backend`.
Посмотреть его журнал (выход — `Ctrl+C`):

```bash
docker compose logs -f backend
```

<details>
<summary>Запуск backend без Docker (нужен установленный Python 3.12)</summary>

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

База данных при этом всё равно должна быть запущена: `docker compose up -d`.

</details>

### Frontend

```bash
npm run dev --prefix frontend
```

Страница в браузере обновляется сама, когда вы сохраняете файл.

## База данных: таблицы и начальные данные

Backend должен быть запущен (`docker compose --profile backend up -d`).

**Создать или обновить таблицы.** Миграции — это пронумерованные скрипты, которые
шаг за шагом приводят структуру базы к нужному виду. Команда применяет все, что ещё
не применены; повторный запуск ничего не ломает:

```bash
docker compose exec backend alembic upgrade head
```

**Загрузить структуру курса и полный контент 9 недель** (71 урок, 994 блока,
714 вопросов). Команду можно запускать повторно — дубли не появятся:

```bash
docker compose exec backend python -m app.db.content_loader --publish-new
```

После этого опубликованы все 9 модулей и 71 урок. Флаг `--publish-new`
нужен при обновлении уже опубликованного курса: без него новые уроки
останутся черновиками до проверки администратором. Практика недель 5–8 идёт
на учебном стенде из `training_stand/` (см. раздел выше).

Если вы правите тексты уроков или квизы в коде, пересоздайте блоки и квизы:

```bash
docker compose exec backend python -m app.db.content_loader --refresh --confirm
```

**Команда `--refresh` удаляет попытки квизов**, поэтому требует `--confirm` и
запрещена при `ENVIRONMENT=production`. Для быстрой проверки только
демонстрационного урока остаётся `python -m app.db.seed --refresh-demo`.

При первом запуске проекта выполните миграции и загрузку контента по порядку.

Посмотреть, какая миграция применена сейчас:

```bash
docker compose exec backend alembic current
```

Проверить, что данные на месте:

```bash
docker compose exec db psql -U loadlab -d loadlab -c "SELECT position, title FROM modules ORDER BY position;"
```

Отменить все миграции — **удалит все таблицы вместе с данными**, используйте
только на своей локальной базе:

```bash
docker compose exec backend alembic downgrade base
```

После изменения моделей в `backend/app/models` новая миграция создаётся так
(затем её нужно прочитать и проверить):

```bash
docker compose exec backend alembic revision --autogenerate -m "краткое_описание"
```

## Учётные записи и вход

На сайте: регистрация — http://localhost:3000/register, вход — http://localhost:3000/login,
профиль — http://localhost:3000/profile. Через регистрацию создаются только ученики.

### Адреса API

Все адреса начинаются с `http://localhost:8001/api/v1`.

| Адрес | Что делает |
|---|---|
| `POST /auth/register` | Регистрация: `email`, `password` (не короче 8 символов). Сразу выполняет вход |
| `POST /auth/login` | Вход по `email` и `password` |
| `POST /auth/logout` | Выход |
| `GET /auth/me` | Кто сейчас вошёл: `id`, `email`, `role` |
| `GET /users/me` | Профиль вошедшего пользователя |
| `GET /admin/ping` | Проверка прав: отвечает только администратору |
| `GET /courses/current` | Программа курса. Гость получает её без личного прогресса (`progress: null`) |
| `GET /lessons/{id}` | Опубликованный урок с блоками. Только после входа, иначе 401; черновик — 404 |
| `POST /lessons/{id}/complete` | Отметить урок пройденным (204, повтор ничего не меняет) |
| `DELETE /lessons/{id}/complete` | Снять отметку (204) |
| `GET /lessons/{id}/quiz` | Квиз урока с вопросами и историей попыток |
| `POST /lessons/{id}/quiz/attempts` | Проверить ответы и сохранить попытку |
| `GET /lessons/{id}/quiz/attempts` | История попыток по квизу |
| `GET`, `PUT /lessons/{id}/note` | Конспект урока |
| `GET`, `POST /lessons/{id}/highlights` | Выделенные определения |
| `DELETE /highlights/{id}` | Удалить выделение |
| `GET`, `POST /saved-questions`, `PATCH`, `DELETE /saved-questions/{id}` | Сложные вопросы |
| `GET`, `POST /review-items`, `PATCH`, `DELETE /review-items/{id}` | Список повторения |
| `GET`, `POST /cheatsheets`, `PATCH`, `DELETE /cheatsheets/{id}` | Шпаргалки |
| `GET /users/me/weak-topics` | Слабые темы по квизам |
| `GET/POST /trainers/*` | Тренажёры HTTP, SQL, Linux и анализа |
| `POST /ai/teacher/ask` | Вопрос AI Teacher по уроку |
| `/admin/interview/*` | Загрузка, разбор и банк вопросов собеседований |
| `/mock-interviews/*` | Пробное собеседование и разбор ответов |
| `GET /ai/teacher/status` | Провайдер и модель без секретов |
| `GET /ai/teacher/recommendations`, `/cheatsheet` | Что повторить и шпаргалка |

Пробовать запросы удобнее всего на странице http://localhost:8001/api/v1/docs.
После входа сервер ставит cookie `loadlab_session`, и браузер сам прикладывает её
к следующим запросам.

### Как создать администратора

Администратор создаётся только командой в терминале. Она спросит почту и пароль;
пароль при вводе не отображается и не остаётся в истории команд:

```bash
docker compose exec backend python -m app.cli create_admin
```

Паролей по умолчанию в проекте нет. Проверить, что роль работает: войдите на сайте
под администратором и откройте http://localhost:8001/api/v1/admin/ping — ответ
`{"status":"ok"}`. Ученик получит ошибку `forbidden`.

### Ограничение попыток входа

После 5 неудачных попыток входа за 15 минут (для пары «IP-адрес + почта») вход
блокируется до конца этих 15 минут — так сервер защищается от подбора пароля.

**Ограничение этой защиты:** счётчик попыток хранится в памяти процесса backend.
Он сбрасывается при перезапуске backend, а если запустить backend в несколько
процессов (воркеров), у каждого будет свой счётчик. Для такой конфигурации понадобится
общее хранилище, например Redis, — это запланировано на этап подготовки к публикации.

## Репетиция production

Отдельный стек для проверки поведения перед публикацией: образ backend без
dev-зависимостей, запуск без `--reload`, исходники не монтируются, у cookie сессии
появляется флаг `Secure`, поэтому вход работает только по HTTPS.

```bash
./infrastructure/deploy.sh
```

Frontend теперь тоже собирается в контейнере (`frontend/Dockerfile`, Next.js
standalone), поэтому отдельный `npm run start` не нужен. Скрипт собирает оба
образа, поднимает стек и проверяет health через Caddy.

Адрес: **https://localhost:8443**. Сертификат выпускает сам Caddy, поэтому браузер
покажет предупреждение — это ожидаемо для локальной репетиции. Остановить стек:

```bash
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml down
```

Данные этой базы лежат в отдельном томе и с разработкой не пересекаются.

Резервные копии и восстановление: [docs/BACKUP.md](docs/BACKUP.md).
Секреты и чек-лист: [docs/SECURITY.md](docs/SECURITY.md).
Нагрузочные ориентиры: [docs/PERFORMANCE.md](docs/PERFORMANCE.md).

## Как остановить проект

- **Frontend:** нажмите `Ctrl+C` в терминале, где он запущен.
- **Backend и база данных:**

```bash
docker compose --profile backend down
```

Данные базы при этом **сохраняются**. Полностью удалить их можно командой
`docker compose --profile backend down -v` — используйте её, только если уверены.

## Как проверить, что всё в порядке

```bash
docker compose exec backend pytest
```

```bash
docker compose exec backend ruff check .
```

```bash
npm run lint --prefix frontend
```

```bash
npm run typecheck --prefix frontend
```

## Где что лежит

```
LoadLab/
├── frontend/                  Сайт (Next.js, React, TypeScript)
│   └── src/
│       ├── app/               Страницы: главная, learn/, learn/lessons/, login/, register/, profile/
│       ├── components/        Части страниц: шапка, футер, разделы главной, вход, урок и прогресс
│       ├── content/           Тексты и данные (программа курса, тексты форм)
│       └── lib/               Вспомогательный код: вызовы API, проверки форм, тема
├── backend/                   Серверная часть (Python, FastAPI)
│   ├── app/
│   │   ├── main.py            Точка входа: отсюда запускается backend
│   │   ├── core/              Настройки и обработка ошибок
│   │   ├── api/endpoints/     Адреса API: health, auth, users, admin, courses, lessons, quizzes, notes, student_tools
│   │   ├── schemas/           Описание формы данных в ответах
│   │   ├── models/            Таблицы базы данных: один файл — одна таблица
│   │   ├── services/          Логика платформы (учётные записи, курс, прогресс, квизы, материалы)
│   │   └── db/                Подключение к базе, контент 9 недель (content/), seed.py
│   ├── alembic/               Миграции — история изменений структуры базы
│   ├── tests/                 Автоматические тесты
│   └── requirements.txt       Список библиотек Python
├── infrastructure/
│   └── docker-compose.yml     Описание контейнеров: база данных и backend
├── docs/                      Дополнительная документация
├── compose.yaml               Позволяет запускать Docker из корня проекта
├── .env.example               Образец настроек (без секретов)
├── .env                       Ваши настройки и пароль (создаёте сами, не в Git)
├── README.md                  Этот файл
├── PROJECT_SPEC.md            Техническое задание
├── ARCHITECTURE.md            Как устроена система
├── ROADMAP.md                 Этапы разработки и их статус
├── CURRICULUM.md              Учебная программа на 9 недель
└── CLAUDE.md                  Правила разработки
```

## Если что-то не работает

| Проблема | Что делать |
|---|---|
| `failed to connect to the docker API` | Docker Desktop не запущен. Запустите его и подождите минуту |
| `Задайте POSTGRES_PASSWORD в файле .env` | Нет файла `.env` или в нём нет пароля — см. «Первый запуск» |
| `Запрос отправлен с неразрешённого адреса` (403) | Изменяющие запросы принимаются только с адресов из `CORS_ORIGINS` в `.env` и со страницы документации API. Запросу из curl добавьте заголовок `-H "Origin: http://localhost:3000"` |
| Внизу сайта «Сервер недоступен» | Backend не запущен: `docker compose --profile backend up -d` |
| `port is already allocated` | Порт занят другой программой. Измените `BACKEND_PORT` или `POSTGRES_PORT` в `.env`. Если меняете порт backend — укажите тот же адрес в `frontend/.env.local` (образец: `frontend/.env.example`) |
| После смены пароля в `.env` база не пускает | Пароль задаётся при первом создании базы. Самый простой путь при пустой базе — `docker compose --profile backend down -v` и запуск заново |

Порт backend — **8001**, а не привычный 8000: на Windows порт 8000 нередко занят
системными службами.
