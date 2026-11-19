export type HttpExercise = {
  id: string;
  title: string;
  task: string;
  method: string;
  path: string;
  hint: string;
};

export type CheckResult = { correct: boolean; feedback: string; expected: string | null };
export type SqlExercise = { id: string; title: string; task: string; hint: string };
export type SqlResult = {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  correct: boolean;
  feedback: string;
};
export type LinuxExercise = { id: string; title: string; task: string; hint: string };
export type LinuxResult = {
  output: string;
  cwd: string;
  correct: boolean;
  feedback: string;
};
export type AnalysisExercise = {
  id: string;
  title: string;
  situation: string;
  options: string[];
};
export type AnalysisResult = { correct: boolean; feedback: string };
