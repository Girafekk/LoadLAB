export type MockQuestion = {
  answer_id: number;
  question_id: number | null;
  text: string;
  topic: string | null;
  position: number;
};

export type MockSession = {
  id: number;
  status: string;
  score: number;
  total: number;
  current: MockQuestion | null;
};

export type MockAnswerResult = {
  answer_id: number;
  score: number;
  feedback: string;
  completed: boolean;
  next_question: MockQuestion | null;
};

export type MockReport = {
  id: number;
  status: string;
  score: number;
  total: number;
  created_at: string;
  completed_at: string | null;
  answers: {
    position: number;
    question: string;
    answer: string | null;
    feedback: string | null;
    score: number | null;
  }[];
};
