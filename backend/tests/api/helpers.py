"""Общие помощники тестов API."""

from fastapi.testclient import TestClient

PASSWORD = "correct-horse-42"
COOKIE_NAME = "loadlab_session"


def register(client: TestClient, email: str = "student@example.com", password: str = PASSWORD):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def login(client: TestClient, email: str = "student@example.com", password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})
