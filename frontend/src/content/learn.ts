/**
 * Тексты страниц «Программа курса» и «Урок».
 * Данные уроков приходят из API, здесь — только подписи интерфейса.
 */
import { course } from "@/content/curriculum";

export const learnContent = {
  program: "Программа курса",
  description: `Программа курса «${course.title}»: ${course.durationWeeks} недель от основ IT до итогового проекта.`,
  planIntro: `${course.durationWeeks} недель, ${course.hoursPerWeek} часов в неделю. Каждая неделя — отдельный модуль с уроками, практикой и квизом.`,
  publicationNote:
    "Первый урок уже открыт. Остальные уроки, практика и квизы появятся по мере готовности — ниже видно, что доступно сейчас.",
  planOnly:
    "Ниже — публичный учебный план. Сейчас не удалось проверить, какие уроки доступны.",
  programLoadError: "Не удалось загрузить доступные уроки.",
  week: (position: number) => `Неделя ${position}`,
  duration: (minutes: number) => `${minutes} мин`,
  planned: "В планах",
  available: "Доступен",
  completed: "Пройден",
  incomplete: "Не пройден",
  home: "← Вернуться на главную",
  back: "← К программе курса",
  lesson: "Урок",
  login: "Войти, чтобы открыть урок",
  loginAction: "Войти",
  loginPrompt:
    "Программа курса открыта всем. Войдите, чтобы прочитать урок и сохранять прогресс.",
  availableHeading: "Доступные уроки",
  availableIntro:
    "Открыты уроки, которые уже опубликованы. Остальные темы программы появятся по мере готовности.",
  lessonMeta: (week: number, position: number) => `Неделя ${week} · урок ${position}`,
  loadingProgram: "Загружаем программу…",
  loadingLesson: "Загружаем урок…",
  lessonLoadError: "Не удалось загрузить урок.",
  lessonNotFound: "Урок не найден или ещё не опубликован.",
  lessonEmpty: "В этом уроке пока нет материалов.",
  retry: "Повторить",
  previousLesson: "← Предыдущий урок",
  nextLesson: "Следующий урок →",
  lessonNav: "Навигация по урокам",
  progress: "Ваш прогресс",
  progressCount: (completed: number, total: number) =>
    `Пройдено ${completed} из ${total} опубликованных уроков`,
  progressDone: "Вы прошли все опубликованные уроки.",
  progressPercent: (percent: number) => `${percent} %`,
  progressEmpty: "Опубликованных уроков пока нет.",
  progressLoadError: "Не удалось обновить прогресс и навигацию.",
  continue: "Продолжить обучение",
  review: "Вернуться к последнему пройденному",
  mark: "Отметить урок пройденным",
  unmark: "Снять отметку",
  saving: "Сохраняем…",
  saveError: "Не удалось сохранить отметку. Попробуйте ещё раз.",
  refreshError:
    "Отметка сохранена, но счётчик прогресса не обновился. Он обновится при следующей загрузке.",
  navError: "Не удалось загрузить навигацию по урокам.",
  lessonUnavailable: "Этот урок больше недоступен.",
  sectionTitle: (position: number, title: string) => `${position}. ${title}`,
  unavailableBlock: "Этот блок пока не удалось отобразить.",
  lessonTable: "Таблица урока",
  lessonCode: (language: string) =>
    language === "python" ? "Пример кода на Python" : "Пример кода",
} as const;
