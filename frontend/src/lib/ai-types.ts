export type AiAnswer = {
  answer: string;
  mode: string;
  provider: string;
  lesson_id: number;
};

export type AiHistoryItem = {
  id: number;
  question: string;
  answer: string;
  mode: string;
  created_at: string;
};

export type AiRecommendation = {
  lesson_id: number;
  title: string;
  percent: number;
  reason: string;
};

export type CheatsheetSuggestion = {
  title: string;
  content: string;
  lesson_ids: number[];
};
