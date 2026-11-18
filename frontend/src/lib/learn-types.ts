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
