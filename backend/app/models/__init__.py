"""Модели SQLAlchemy (таблицы базы данных).

Каждую новую модель нужно импортировать в этом файле — тогда Alembic
увидит её при создании миграций.
"""

from app.models.ai_teacher_message import AiTeacherMessage
from app.models.cheatsheet import Cheatsheet
from app.models.course import Course
from app.models.interview import InterviewQuestion, InterviewSource
from app.models.lesson import Lesson
from app.models.lesson_block import LessonBlock
from app.models.lesson_highlight import LessonHighlight
from app.models.lesson_note import LessonNote
from app.models.lesson_progress import LessonProgress
from app.models.mock_interview import MockInterview, MockInterviewAnswer
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_attempt_answer import QuizAttemptAnswer, quiz_attempt_selected_options
from app.models.quiz_option import QuizOption
from app.models.quiz_question import QuizQuestion
from app.models.review_item import ReviewItem
from app.models.saved_question import SavedQuestion
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "AiTeacherMessage",
    "Cheatsheet",
    "Course",
    "InterviewQuestion",
    "InterviewSource",
    "Lesson",
    "LessonBlock",
    "LessonHighlight",
    "LessonNote",
    "LessonProgress",
    "Module",
    "MockInterview",
    "MockInterviewAnswer",
    "Quiz",
    "QuizAttempt",
    "QuizAttemptAnswer",
    "QuizOption",
    "QuizQuestion",
    "ReviewItem",
    "SavedQuestion",
    "User",
    "UserSession",
    "quiz_attempt_selected_options",
]
