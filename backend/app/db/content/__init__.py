"""Контент курса по неделям. Каждая неделя — отдельный файл."""

from app.db.content import week1, week2, week3, week4, week5, week6, week7, week8

WEEKS = {
    1: week1.LESSONS,
    2: week2.LESSONS,
    3: week3.LESSONS,
    4: week4.LESSONS,
    5: week5.LESSONS,
    6: week6.LESSONS,
    7: week7.LESSONS,
    8: week8.LESSONS,
}
