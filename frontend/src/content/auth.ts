/** Тексты страниц входа, регистрации и профиля. */
export const PASSWORD_MIN_LENGTH = 8;

export const authContent = {
  fields: {
    email: "Электронная почта",
    emailPlaceholder: "you@example.com",
    password: "Пароль",
    passwordHint: `Не короче ${PASSWORD_MIN_LENGTH} символов`,
    passwordRepeat: "Пароль ещё раз",
  },
  login: {
    title: "Вход",
    description: "Войдите, чтобы продолжить обучение.",
    submit: "Войти",
    submitting: "Входим…",
    switchQuestion: "Ещё нет учётной записи?",
    switchLink: "Зарегистрироваться",
  },
  register: {
    title: "Регистрация",
    description: "Создайте учётную запись, чтобы сохранять прогресс обучения.",
    submit: "Зарегистрироваться",
    submitting: "Создаём учётную запись…",
    switchQuestion: "Уже есть учётная запись?",
    switchLink: "Войти",
  },
  profile: {
    title: "Профиль",
    description: "Ваша учётная запись на платформе LoadLab.",
    email: "Электронная почта",
    role: "Роль",
    logout: "Выйти",
    loggingOut: "Выходим…",
    loading: "Загружаем профиль…",
    redirecting: "Переходим на страницу входа…",
  },
  roles: {
    student: "Ученик",
    admin: "Администратор",
  },
  menu: {
    login: "Войти",
    register: "Регистрация",
    profile: "Профиль",
    logout: "Выйти",
  },
  errors: {
    emailRequired: "Укажите электронную почту",
    emailInvalid: "Проверьте адрес: он должен выглядеть как name@example.com",
    passwordRequired: "Введите пароль",
    passwordTooShort: `Пароль должен быть не короче ${PASSWORD_MIN_LENGTH} символов`,
    passwordTooLong: "Пароль слишком длинный: не больше 128 символов",
    passwordMismatch: "Пароли не совпадают",
    invalidCredentials: "Неверная электронная почта или пароль",
    emailTaken: "Пользователь с такой почтой уже зарегистрирован. Попробуйте войти",
    accountDisabled: "Учётная запись отключена. Обратитесь к администратору",
    tooManyAttempts: "Слишком много неудачных попыток. Подождите 15 минут и попробуйте снова",
    invalidData: "Проверьте введённые данные",
    network: "Не удалось связаться с сервером. Проверьте, что он запущен, и повторите попытку",
    unknown: "Что-то пошло не так. Повторите попытку позже",
    logoutFailed: "Не удалось выйти. Повторите попытку",
  },
} as const;
