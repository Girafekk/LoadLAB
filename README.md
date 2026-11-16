# LoadLab

Образовательная платформа для обучения нагрузочному тестированию.
Сейчас готов **этап 1 — технический фундамент**: главная страница, backend с проверкой
состояния и база данных. Уроки, квизы и остальное появятся на следующих этапах
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
| [Node.js](https://nodejs.org/) 20.9 или новее | Запускает frontend | `node --version` |
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
│       ├── app/               Страницы: page.tsx — главная, learn/ — программа курса
│       ├── components/        Части страниц: шапка, футер, разделы главной
│       ├── content/           Тексты и данные (программа курса)
│       └── lib/               Вспомогательный код: вызовы API, тема
├── backend/                   Серверная часть (Python, FastAPI)
│   ├── app/
│   │   ├── main.py            Точка входа: отсюда запускается backend
│   │   ├── core/              Настройки и обработка ошибок
│   │   ├── api/endpoints/     Адреса API (сейчас только health)
│   │   ├── schemas/           Описание формы данных в ответах
│   │   ├── models/            Таблицы базы данных (пока пусто)
│   │   ├── services/          Логика платформы (пока пусто)
│   │   └── db/                Подключение к базе данных
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
├── CURRICULUM.md              Учебная программа на 8 недель
└── CLAUDE.md                  Правила разработки
```

## Если что-то не работает

| Проблема | Что делать |
|---|---|
| `failed to connect to the docker API` | Docker Desktop не запущен. Запустите его и подождите минуту |
| `Задайте POSTGRES_PASSWORD в файле .env` | Нет файла `.env` или в нём нет пароля — см. «Первый запуск» |
| Внизу сайта «Сервер недоступен» | Backend не запущен: `docker compose --profile backend up -d` |
| `port is already allocated` | Порт занят другой программой. Измените `BACKEND_PORT` или `POSTGRES_PORT` в `.env`. Если меняете порт backend — укажите тот же адрес в `frontend/.env.local` (образец: `frontend/.env.example`) |
| После смены пароля в `.env` база не пускает | Пароль задаётся при первом создании базы. Самый простой путь при пустой базе — `docker compose --profile backend down -v` и запуск заново |

Порт backend — **8001**, а не привычный 8000: на Windows порт 8000 нередко занят
системными службами.
