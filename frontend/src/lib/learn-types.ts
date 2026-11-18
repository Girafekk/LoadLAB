export type CourseProgress = {
  completed_lessons: number;
  total_lessons: number;
  percent: number;
  next_lesson_id: number | null;
  last_completed_lesson_id: number | null;
};

export type LessonBrief = {
  id: number;
  title: string;
  position: number;
  estimated_minutes: number;
  is_completed: boolean;
};

export type CourseModule = {
  id: number;
  title: string;
  summary: string | null;
  position: number;
  lessons: LessonBrief[];
};

export type CourseOverview = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  modules: CourseModule[];
  progress: CourseProgress | null;
};

export type LessonBlock = {
  type: string;
  content: Record<string, unknown>;
  position: number;
};

export type LessonRead = {
  id: number;
  title: string;
  summary: string | null;
  estimated_minutes: number;
  is_completed: boolean;
  blocks: LessonBlock[];
};

export type QuizOption = {
  id: number;
  text: string;
  position: number;
};

export type QuizQuestion = {
  id: number;
  kind: string;
  text: string;
  position: number;
  multiple: boolean;
  options: QuizOption[];
};

export type QuizRead = {
  id: number;
  title: string;
  description: string | null;
  questions: QuizQuestion[];
};

export type QuizAttemptSummary = {
  id: number;
  score: number;
  max_score: number;
  percent: number;
  created_at: string;
};

export type QuizWithHistory = {
  quiz: QuizRead;
  attempts: QuizAttemptSummary[];
  attempts_total: number;
  best_percent: number | null;
};

export type QuizAnswerInput = {
  question_id: number;
  option_ids: number[];
};

export type QuizQuestionResult = {
  question_id: number;
  is_correct: boolean;
  selected_option_ids: number[];
  correct_option_ids: number[];
  explanation: string;
};

export type QuizAttemptResult = {
  id: number;
  score: number;
  max_score: number;
  percent: number;
  created_at: string;
  questions: QuizQuestionResult[];
};
