export type CourseAdmin = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  is_published: boolean;
  module_count: number;
  lesson_count: number;
};

export type LessonBriefAdmin = {
  id: number;
  title: string;
  position: number;
  estimated_minutes: number;
  is_published: boolean;
  quiz_id: number | null;
};

export type ModuleAdmin = {
  id: number;
  title: string;
  summary: string | null;
  position: number;
  lessons: LessonBriefAdmin[];
};

export type CourseTree = CourseAdmin & { modules: ModuleAdmin[] };

export type BlockAdmin = {
  type: string;
  content: Record<string, unknown>;
  position: number;
};

export type LessonAdmin = {
  id: number;
  module_id: number;
  title: string;
  summary: string | null;
  estimated_minutes: number;
  position: number;
  is_published: boolean;
  blocks: BlockAdmin[];
  quiz_id: number | null;
};

export type QuizOptionAdmin = { text: string; is_correct: boolean };
export type QuizQuestionAdmin = {
  kind: string;
  text: string;
  explanation: string;
  options: QuizOptionAdmin[];
};
export type QuizAdmin = {
  id: number;
  title: string;
  description: string | null;
  is_published: boolean;
  attempts_count: number;
  questions: QuizQuestionAdmin[];
};

export type BlockInput = { type: string; content: Record<string, unknown> };

export type CourseImportBlock = {
  type: string;
  content: Record<string, unknown>;
};

export type CourseImportLesson = {
  title: string;
  summary: string | null;
  position: number;
  blocks: CourseImportBlock[];
};

export type CourseImportModule = {
  title: string;
  summary: string | null;
  position: number;
  lessons: CourseImportLesson[];
};

export type CourseImportDraft = {
  title: string;
  description: string | null;
  modules: CourseImportModule[];
  source_name?: string;
  used_ai?: boolean;
};

export type CourseImportPreview = {
  token: string;
  course: CourseImportDraft;
  source_chars: number;
};
export type QuizPayload = {
  title: string;
  description: string | null;
  is_published: boolean;
  questions: QuizQuestionAdmin[];
  confirm_attempts_loss?: boolean;
  expected_attempts_count?: number;
  expected_quiz_id?: number;
};

export type ReviewItem = {
  id: number;
  text: string;
  topic: string | null;
  reference_answer: string | null;
  answer_criteria: string | null;
  review_status: string;
  review_comment: string | null;
};

export type ReviewQueue = {
  items: ReviewItem[];
  total: number;
  counts: Record<string, number>;
};

export type StudentProgress = {
  id: number;
  email: string;
  completed_lessons: number;
  total_lessons: number;
  percent: number;
  quiz_attempts: number;
  last_activity: string | null;
};

export type ModuleProgress = {
  module_id: number;
  title: string;
  completed: number;
  total: number;
};

export type StudentProgressDetail = StudentProgress & { modules: ModuleProgress[] };
