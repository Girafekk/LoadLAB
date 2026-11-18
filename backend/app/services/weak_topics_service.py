"""Слабые темы ученика по результатам квизов."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Lesson, Module, Quiz, QuizAttempt
from app.schemas.tools import WeakTopicRead

# Ниже этого результата тема считается слабой и попадает в рекомендации.
WEAK_TOPIC_THRESHOLD = 80


@dataclass
class _TopicStats:
    lesson_title: str
    module_title: str
    best_score: int
    best_max: int
    attempts: int

    @property
    def best_percent(self) -> int:
        return round(100 * self.best_score / self.best_max) if self.best_max else 0

    @property
    def is_weak(self) -> bool:
        # Сравнение без округления: 79,5 % не должно стать 80 % и покинуть список.
        return self.best_score * 100 < WEAK_TOPIC_THRESHOLD * self.best_max


def weak_topics(db: Session, user_id: int) -> list[WeakTopicRead]:
    """Темы, где лучший результат ученика ниже порога.

    Считается по лучшей попытке: если ученик разобрался и пересдал квиз,
    тема перестаёт быть слабой. Темы без попыток сюда не попадают.
    """
    rows = db.execute(
        select(
            Lesson.id,
            Lesson.title,
            Module.title,
            QuizAttempt.score,
            QuizAttempt.max_score,
        )
        .join(Quiz, Quiz.lesson_id == Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .join(Course, Course.id == Module.course_id)
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.max_score > 0,
            Lesson.is_published.is_(True),
            Quiz.is_published.is_(True),
            Course.is_published.is_(True),
        )
    ).all()

    stats: dict[int, _TopicStats] = {}
    for lesson_id, lesson_title, module_title, score, max_score in rows:
        current = stats.get(lesson_id)
        if current is None:
            stats[lesson_id] = _TopicStats(lesson_title, module_title, score, max_score, 1)
        else:
            current.attempts += 1
            # Сравниваем дроби перекрёстно, чтобы не терять точность на округлении.
            if score * current.best_max > current.best_score * max_score:
                current.best_score = score
                current.best_max = max_score

    weak = [
        WeakTopicRead(
            lesson_id=lesson_id,
            lesson_title=item.lesson_title,
            module_title=item.module_title,
            best_percent=item.best_percent,
            attempts=item.attempts,
        )
        for lesson_id, item in stats.items()
        if item.is_weak
    ]
    weak.sort(key=lambda topic: (topic.best_percent, topic.lesson_id))
    return weak
