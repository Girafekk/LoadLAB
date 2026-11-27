export type ExamModule = {
  id: number;
  title: string;
  position: number;
  questions: number;
};

export type ExamQuestion = {
  id: number;
  text: string;
  options: { id: number; text: string }[];
};

export type ExamQuestions = {
  total: number;
  questions: ExamQuestion[];
};

export type ExamResult = {
  total: number;
  correct: number;
  percent: number;
  details: {
    question_id: number;
    correct: boolean;
    correct_option_ids: number[];
    explanation: string;
  }[];
};
