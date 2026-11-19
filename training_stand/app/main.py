"""Учебный стенд LoadLab: интернет-магазин для практики нагрузочного тестирования."""

from __future__ import annotations

import hashlib
import html
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

DB_PATH = Path(os.environ.get("STAND_DB_PATH", "stand.db"))
RESET_TOKEN = os.environ.get("STAND_RESET_TOKEN", "loadlab-reset")
TOKEN_TTL = timedelta(hours=12)

USERS = (
    ("student1@example.com", "password123"),
    ("student2@example.com", "password123"),
    ("student3@example.com", "password123"),
)

PRODUCTS = (
    ("Ноутбук Lenovo IdeaPad", "Учебный ноутбук для дома и офиса", 5490000, "Электроника", 12),
    ("Смартфон Pixel 8", "Компактный смартфон с хорошей камерой", 4290000, "Электроника", 20),
    ("Наушники Sony WH-1000XM5", "Беспроводные наушники с шумоподавлением", 2790000, "Электроника", 15),
    ("Клавиатура Logitech MX Keys", "Беспроводная клавиатура для работы", 890000, "Аксессуары", 35),
    ("Мышь Logitech MX Master 3S", "Эргономичная мышь", 790000, "Аксессуары", 40),
    ("Монитор Dell 27 4K", "Монитор для работы с текстом и кодом", 3190000, "Электроника", 8),
    ("Кресло ErgoChair", "Офисное кресло с поддержкой спины", 2490000, "Мебель", 10),
    ("Стол Sit-Stand", "Регулируемый стол для работы стоя", 3790000, "Мебель", 6),
    ("Рюкзак Urban 20", "Рюкзак для ноутбука 15 дюймов", 590000, "Аксессуары", 50),
    ("Кофемолка Barista", "Ручная кофемолка для дома", 349000, "Дом", 25),
    ("Термокружка Steel", "Термокружка 500 мл", 189000, "Дом", 60),
    ("Лампа настольная Flex", "Лампа с регулировкой яркости", 259000, "Дом", 30),
)


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"stand::{password}".encode()).hexdigest()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def db(immediate: bool = False):
    connection = _connect()
    if immediate:
        # Сериализуем чтение корзины и создание заказа: иначе два запроса
        # успевают прочитать одну корзину и создать два заказа.
        connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            PRIMARY KEY (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_cents INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_cents INTEGER NOT NULL,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )


def reset_database() -> None:
    """Создаёт схему и тестовые данные заново."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    with db() as connection:
        _create_schema(connection)
        for email, password in USERS:
            connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                (email, _hash_password(password)),
            )
        connection.executemany(
            "INSERT INTO products(name, description, price_cents, category, stock)"
            " VALUES (?, ?, ?, ?, ?)",
            PRODUCTS,
        )
        # Несколько заказов, чтобы в отчётах были данные.
        user_id = connection.execute(
            "SELECT id FROM users WHERE email = ?", ("student1@example.com",)
        ).fetchone()["id"]
        for product_id, quantity in ((1, 1), (5, 2)):
            product = connection.execute(
                "SELECT price_cents FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            order = connection.execute(
                "INSERT INTO orders(user_id, total_cents, created_at)"
                " VALUES (?, ?, ?)",
                (
                    user_id,
                    product["price_cents"] * quantity,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.execute(
                "INSERT INTO order_items(order_id, product_id, quantity, price_cents)"
                " VALUES (?, ?, ?, ?)",
                (order.lastrowid, product_id, quantity, product["price_cents"]),
            )


def ensure_database() -> None:
    if not DB_PATH.exists():
        reset_database()
    else:
        with db() as connection:
            _create_schema(connection)


def _now() -> datetime:
    return datetime.now(UTC)


def _user_from_token(connection: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    row = connection.execute(
        "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
        (token,),
    ).fetchone()
    if row is None:
        return None
    expires = connection.execute(
        "SELECT expires_at FROM tokens WHERE token = ?", (token,)
    ).fetchone()
    if expires is None or datetime.fromisoformat(expires["expires_at"]) < _now():
        connection.execute("DELETE FROM tokens WHERE token = ?", (token,))
        return None
    return row


def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> sqlite3.Row:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token is None:
        token = request.cookies.get("stand_token")
    with db() as connection:
        user = _user_from_token(connection, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется вход")
    return user


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class TokenResponse(BaseModel):
    token: str
    user: dict[str, object]


class ProductRead(BaseModel):
    id: int
    name: str
    description: str
    price_cents: int
    category: str
    stock: int


class CartRead(BaseModel):
    items: list[dict[str, object]]
    total_cents: int


class OrderRead(BaseModel):
    id: int
    status: str
    total_cents: int
    created_at: str
    items: list[dict[str, object]]


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — Учебный магазин</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f6f8; color: #1a1a1a; }}
    header {{ background: #1f2937; color: white; padding: 12px 20px; }}
    header a {{ color: #c7d2fe; margin-right: 16px; text-decoration: none; }}
    main {{ max-width: 900px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: white; border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin-bottom: 12px; }}
    .row {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    .muted {{ color: #666; font-size: 14px; }}
    input, button {{ font: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid #bbb; }}
    button {{ background: #1f2937; color: white; border: 0; cursor: pointer; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ padding: 6px; border-bottom: 1px solid #eee; text-align: left; }}
  </style>
</head>
<body>
<header>
  <strong>Учебный магазин LoadLab</strong>
  <a href="/">Товары</a>
  <a href="/ui/cart">Корзина</a>
  <a href="/ui/orders">Заказы</a>
  <a href="/api/docs">API</a>
</header>
<main>{body}</main>
</body>
</html>""",
        headers={"Cache-Control": "no-store"},
    )


def _place_order(connection: sqlite3.Connection, user_id: int) -> int:
    """Создаёт заказ из корзины в уже открытой транзакции."""
    items = connection.execute(
        """
        SELECT p.id, p.price_cents, p.stock, c.quantity
        FROM cart_items c JOIN products p ON p.id = c.product_id
        WHERE c.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    if not items:
        raise HTTPException(status_code=422, detail="Корзина пуста")
    for item in items:
        if int(item["quantity"]) > int(item["stock"]):
            raise HTTPException(
                status_code=422,
                detail=f"Товара {item['id']} на складе меньше, чем в корзине",
            )
    total = sum(int(item["price_cents"]) * int(item["quantity"]) for item in items)
    order = connection.execute(
        "INSERT INTO orders(user_id, total_cents, created_at) VALUES (?, ?, ?)",
        (user_id, total, _now().isoformat()),
    )
    for item in items:
        connection.execute(
            "INSERT INTO order_items(order_id, product_id, quantity, price_cents)"
            " VALUES (?, ?, ?, ?)",
            (order.lastrowid, item["id"], item["quantity"], item["price_cents"]),
        )
        connection.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item["quantity"], item["id"]),
        )
    connection.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    return int(order.lastrowid)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        ensure_database()
        yield

    app = FastAPI(
        title="LoadLab Training Shop",
        version="1.0.0",
        description="Учебный интернет-магазин для нагрузочного тестирования.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        with db() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "training-shop"}

    @app.post("/api/login", response_model=TokenResponse)
    def login(data: LoginRequest) -> TokenResponse:
        with db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ?", (data.email.lower(),)
            ).fetchone()
            if user is None or user["password_hash"] != _hash_password(data.password):
                raise HTTPException(status_code=401, detail="Неверная почта или пароль")
            token = secrets.token_urlsafe(24)
            connection.execute(
                "INSERT INTO tokens(token, user_id, expires_at) VALUES (?, ?, ?)",
                (
                    token,
                    user["id"],
                    (_now() + TOKEN_TTL).isoformat(),
                ),
            )
        return TokenResponse(
            token=token,
            user={"id": user["id"], "email": user["email"]},
        )

    @app.post("/api/logout", status_code=204)
    def logout(
        request: Request,
        response: Response,
        authorization: str | None = Header(default=None),
    ) -> None:
        token = None
        if authorization:
            parts = authorization.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1].strip()
        if not token:
            token = request.cookies.get("stand_token")
        if token:
            with db() as connection:
                connection.execute("DELETE FROM tokens WHERE token = ?", (token,))
        response.delete_cookie("stand_token")

    @app.get("/api/products", response_model=list[ProductRead])
    def products(
        q: str | None = Query(default=None, max_length=100),
        category: str | None = Query(default=None, max_length=50),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> list[ProductRead]:
        # SQLite LIKE не умеет регистронезависимый поиск по кириллице,
        # поэтому для 12 учебных товаров фильтруем в Python.
        with db() as connection:
            rows = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
        filtered = []
        for row in rows:
            if q:
                needle = q.casefold()
                if needle not in row["name"].casefold() and needle not in row["description"].casefold():
                    continue
            if category and category.casefold() != row["category"].casefold():
                continue
            filtered.append(row)
        return [ProductRead(**dict(row)) for row in filtered[offset : offset + limit]]

    @app.get("/api/products/{product_id}", response_model=ProductRead)
    def product(product_id: int) -> ProductRead:
        with db() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return ProductRead(**dict(row))

    @app.get("/api/cart", response_model=CartRead)
    def cart(user: sqlite3.Row = Depends(current_user)) -> CartRead:
        with db() as connection:
            rows = connection.execute(
                """
                SELECT p.id AS product_id, p.name, p.price_cents, c.quantity
                FROM cart_items c JOIN products p ON p.id = c.product_id
                WHERE c.user_id = ? ORDER BY p.id
                """,
                (user["id"],),
            ).fetchall()
        items = [dict(row) for row in rows]
        total = sum(int(item["price_cents"]) * int(item["quantity"]) for item in items)
        return CartRead(items=items, total_cents=total)

    @app.post("/api/cart/items", response_model=CartRead)
    def add_to_cart(
        data: CartItemRequest, user: sqlite3.Row = Depends(current_user)
    ) -> CartRead:
        with db(immediate=True) as connection:
            product = connection.execute(
                "SELECT id, stock FROM products WHERE id = ?", (data.product_id,)
            ).fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Товар не найден")
            current = connection.execute(
                "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
                (user["id"], data.product_id),
            ).fetchone()
            quantity = (int(current["quantity"]) if current else 0) + data.quantity
            if quantity > int(product["stock"]):
                raise HTTPException(status_code=422, detail="На складе меньше товара")
            connection.execute(
                """
                INSERT INTO cart_items(user_id, product_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(user_id, product_id)
                DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (user["id"], data.product_id, data.quantity),
            )
        return cart(user)

    @app.patch("/api/cart/items/{product_id}", response_model=CartRead)
    def update_cart(
        product_id: int,
        data: CartItemUpdate,
        user: sqlite3.Row = Depends(current_user),
    ) -> CartRead:
        with db(immediate=True) as connection:
            product = connection.execute(
                "SELECT stock FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Товар не найден")
            if data.quantity > int(product["stock"]):
                raise HTTPException(status_code=422, detail="На складе меньше товара")
            result = connection.execute(
                "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
                (data.quantity, user["id"], product_id),
            )
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Товара нет в корзине")
        return cart(user)

    @app.delete("/api/cart/items/{product_id}", response_model=CartRead)
    def delete_cart_item(
        product_id: int, user: sqlite3.Row = Depends(current_user)
    ) -> CartRead:
        with db() as connection:
            connection.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
                (user["id"], product_id),
            )
        return cart(user)

    @app.post("/api/orders", response_model=OrderRead, status_code=201)
    def create_order(user: sqlite3.Row = Depends(current_user)) -> OrderRead:
        with db(immediate=True) as connection:
            order_id = _place_order(connection, int(user["id"]))
            return _order(connection, order_id, int(user["id"]))

    def _order(connection: sqlite3.Connection | None, order_id: int, user_id: int) -> OrderRead:
        if connection is None:
            with db() as opened:
                return _order(opened, order_id, user_id)
        order = connection.execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)
        ).fetchone()
        if order is None:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        items = connection.execute(
            "SELECT product_id, quantity, price_cents FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        return OrderRead(
            id=order["id"],
            status=order["status"],
            total_cents=order["total_cents"],
            created_at=order["created_at"],
            items=[dict(item) for item in items],
        )

    @app.get("/api/orders", response_model=list[OrderRead])
    def list_orders(user: sqlite3.Row = Depends(current_user)) -> list[OrderRead]:
        with db() as connection:
            ids = connection.execute(
                "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC", (user["id"],)
            ).fetchall()
            return [_order(connection, int(row["id"]), int(user["id"])) for row in ids]

    @app.get("/api/orders/{order_id}", response_model=OrderRead)
    def read_order(order_id: int, user: sqlite3.Row = Depends(current_user)) -> OrderRead:
        return _order(None, order_id, int(user["id"]))

    @app.post("/api/admin/reset", status_code=204)
    def reset(x_reset_token: str | None = Header(default=None)) -> None:
        if x_reset_token != RESET_TOKEN:
            raise HTTPException(status_code=403, detail="Неверный токен сброса")
        reset_database()

    # --- Простой HTML-интерфейс для ручной проверки ------------------------------

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, q: str | None = None) -> HTMLResponse:
        with db() as connection:
            all_rows = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
        needle = (q or "").casefold()
        rows = [
            row
            for row in all_rows
            if not needle
            or needle in row["name"].casefold()
            or needle in row["description"].casefold()
        ]
        cards = "".join(
            f"""<div class="card">
              <h3>{html.escape(row['name'])}</h3>
              <p class="muted">{html.escape(row['description'])}</p>
              <p>{row['price_cents'] // 100} ₽ · остаток {row['stock']}</p>
              <form method="post" action="/ui/cart/add">
                <input type="hidden" name="product_id" value="{row['id']}">
                <button>В корзину</button>
              </form>
            </div>"""
            for row in rows
        )
        user = None
        with db() as connection:
            user = _user_from_token(connection, request.cookies.get("stand_token"))
        login_block = (
            f"""<p>Вы вошли как {html.escape(user['email'])}</p>
            <form method="post" action="/ui/logout"><button>Выйти</button></form>"""
            if user
            else """<form method="post" action="/ui/login" class="row">
              <input name="email" placeholder="student1@example.com" required>
              <input name="password" type="password" placeholder="password123" required>
              <button>Войти</button>
            </form>"""
        )
        return _page(
            "Товары",
            f"""{login_block}
            <form method="get" action="/" class="row" style="margin:16px 0">
              <input name="q" value="{html.escape(q or '')}" placeholder="Поиск">
              <button>Найти</button>
            </form>
            {cards}""",
        )

    @app.post("/ui/login")
    def ui_login(email: str = Form(...), password: str = Form(...)) -> RedirectResponse:
        with db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
            if user is None or user["password_hash"] != _hash_password(password):
                return RedirectResponse("/", status_code=303)
            token = secrets.token_urlsafe(24)
            connection.execute(
                "INSERT INTO tokens(token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user["id"], (_now() + TOKEN_TTL).isoformat()),
            )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("stand_token", token, httponly=True, samesite="lax")
        return response

    @app.post("/ui/logout")
    def ui_logout(request: Request) -> RedirectResponse:
        token = request.cookies.get("stand_token")
        if token:
            with db() as connection:
                connection.execute("DELETE FROM tokens WHERE token = ?", (token,))
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("stand_token")
        return response

    @app.post("/ui/cart/add")
    def ui_add(request: Request, product_id: int = Form(...)) -> RedirectResponse:
        token = request.cookies.get("stand_token")
        with db(immediate=True) as connection:
            user = _user_from_token(connection, token)
            if user is not None:
                product = connection.execute(
                    "SELECT stock FROM products WHERE id = ?", (product_id,)
                ).fetchone()
                current = connection.execute(
                    "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
                    (user["id"], product_id),
                ).fetchone()
                quantity = int(current["quantity"]) + 1 if current else 1
                if product is not None and quantity <= int(product["stock"]):
                    connection.execute(
                        """
                        INSERT INTO cart_items(user_id, product_id, quantity)
                        VALUES (?, ?, 1)
                        ON CONFLICT(user_id, product_id)
                        DO UPDATE SET quantity = quantity + 1
                        """,
                        (user["id"], product_id),
                    )
        return RedirectResponse("/ui/cart", status_code=303)

    @app.get("/ui/cart", response_class=HTMLResponse)
    def ui_cart(request: Request) -> HTMLResponse:
        with db() as connection:
            user = _user_from_token(connection, request.cookies.get("stand_token"))
            if user is None:
                return _page("Корзина", "<p>Сначала войдите на главной странице.</p>")
            rows = connection.execute(
                """
                SELECT p.id, p.name, p.price_cents, c.quantity
                FROM cart_items c JOIN products p ON p.id = c.product_id
                WHERE c.user_id = ? ORDER BY p.id
                """,
                (user["id"],),
            ).fetchall()
        rows_html = "".join(
            f"<tr><td>{html.escape(row['name'])}</td><td>{row['quantity']}</td>"
            f"<td>{row['price_cents'] * row['quantity'] // 100} ₽</td></tr>"
            for row in rows
        )
        total = sum(int(row["price_cents"]) * int(row["quantity"]) for row in rows)
        return _page(
            "Корзина",
            f"""<table><tr><th>Товар</th><th>Кол-во</th><th>Сумма</th></tr>
            {rows_html}</table>
            <p><strong>Итого: {total // 100} ₽</strong></p>
            <form method="post" action="/ui/orders"><button>Оформить заказ</button></form>""",
        )

    @app.post("/ui/orders")
    def ui_order(request: Request) -> RedirectResponse:
        token = request.cookies.get("stand_token")
        try:
            with db(immediate=True) as connection:
                user = _user_from_token(connection, token)
                if user is None:
                    return RedirectResponse("/", status_code=303)
                _place_order(connection, int(user["id"]))
        except HTTPException:
            return RedirectResponse("/ui/cart", status_code=303)
        return RedirectResponse("/ui/orders", status_code=303)

    @app.get("/ui/orders", response_class=HTMLResponse)
    def ui_orders(request: Request) -> HTMLResponse:
        with db() as connection:
            user = _user_from_token(connection, request.cookies.get("stand_token"))
            if user is None:
                return _page("Заказы", "<p>Сначала войдите на главной странице.</p>")
            orders = connection.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user["id"],)
            ).fetchall()
        rows = "".join(
            f"<li>Заказ №{order['id']} — {order['total_cents'] // 100} ₽</li>"
            for order in orders
        )
        return _page("Заказы", f"<ul>{rows or '<li>Заказов пока нет</li>'}</ul>")

    return app


app = create_app()
