export type InterviewSource = {
  id: number;
  filename: string;
  media_type: string;
  size_bytes: number;
  status: string;
  error: string | null;
  created_at: string;
  questions_count: number;
};

export type InterviewQuestion = {
  id: number;
  text: string;
  topic: string | null;
  difficulty: string;
  level: string;
  status: string;
  occurrences: number;
  source_id: number | null;
  lesson_id: number | null;
  reference_answer: string | null;
  answer_criteria: string | null;
};

export type InterviewReport = {
  total_questions: number;
  approved: number;
  proposed: number;
  rejected: number;
  answers_ready: number;
  answers_missing: number;
  criteria_ready: number;
  questions_without_lesson: number;
  by_topic: { topic: string; questions: number; lessons: number }[];
  coverage: { lesson_id: number; lesson_title: string; questions: number }[];
  gaps: string[];
  suggestions: string[];
};

export type AnalyzeResult = {
  sources_processed: number;
  questions_created: number;
  duplicates: number;
  provider: string;
};

export type LessonOption = { id: number; title: string };
