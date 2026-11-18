export type LessonNote = {
  lesson_id: number;
  content: string;
  updated_at: string | null;
};

export type LessonHighlight = {
  id: number;
  lesson_id: number;
  text: string;
  created_at: string;
};

export type SavedQuestion = {
  id: number;
  lesson_id: number | null;
  text: string;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
};

export type ReviewItem = {
  id: number;
  lesson_id: number | null;
  title: string;
  note: string | null;
  is_done: boolean;
  created_at: string;
  updated_at: string;
};

export type Cheatsheet = {
  id: number;
  lesson_id: number | null;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type WeakTopic = {
  lesson_id: number;
  lesson_title: string;
  module_title: string;
  best_percent: number;
  attempts: number;
};
