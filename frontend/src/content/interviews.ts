export const interviewsContent = {
  title: "Разборы собеседований",
  intro:
    "Вопросы и эталонные ответы из загруженных файлов: собеседования, учебные материалы, методики и шаблоны. Выберите файл и разбирайте темы по порядку.",
  categories: {
    interview: "Собеседование",
    course: "Учебный материал",
    prompt: "Промпт",
    method: "Методика",
    template: "Шаблон",
  } as Record<string, string>,
  loading: "Загружаем собеседования…",
  error: "Не удалось загрузить разборы.",
  empty: "Пока нет опубликованных разборов.",
  questions: (count: number) => {
    const tail = count % 100;
    const word =
      tail >= 11 && tail <= 14
        ? "вопросов"
        : count % 10 === 1
          ? "вопрос"
          : count % 10 >= 2 && count % 10 <= 4
            ? "вопроса"
            : "вопросов";
    return `${count} ${word}`;
  },
  date: "Дата",
  open: "Открыть разбор",
  back: "← Ко всем собеседованиям",
  answer: "Эталонный ответ",
  criteria: "Критерии ответа",
  noAnswer: "Ответ ещё не подготовлен.",
  notFound: "Собеседование не найдено.",
  loadingOne: "Загружаем вопросы…",
  source: "Источник",
} as const;
