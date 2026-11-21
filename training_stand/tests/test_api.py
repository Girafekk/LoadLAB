from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app, reset_database


def client() -> TestClient:
    reset_database()
    test_client = TestClient(app)
    test_client.headers.update({"Origin": "http://testserver"})
    return test_client


def login(test_client: TestClient, email: str = "student1@example.com") -> str:
    response = test_client.post(
        "/api/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_health_and_products():
    with client() as test_client:
        assert test_client.get("/api/health").json()["status"] == "ok"
        products = test_client.get("/api/products").json()
        assert len(products) == 12
        found = test_client.get("/api/products", params={"q": "наушники"}).json()
        assert len(found) == 1
        assert test_client.get(f"/api/products/{products[0]['id']}").status_code == 200
        assert test_client.get("/api/products/9999").status_code == 404


def test_cart_and_order_flow():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}

        assert test_client.get("/api/cart").status_code == 401
        cart = test_client.post(
            "/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=headers
        )
        assert cart.status_code == 200
        assert cart.json()["items"][0]["quantity"] == 2

        updated = test_client.patch(
            "/api/cart/items/1", json={"quantity": 3}, headers=headers
        )
        assert updated.json()["items"][0]["quantity"] == 3

        order = test_client.post("/api/orders", headers=headers)
        assert order.status_code == 201
        body = order.json()
        assert body["total_cents"] == 5490000 * 3
        assert body["items"][0]["quantity"] == 3

        assert test_client.get("/api/cart", headers=headers).json()["items"] == []
        assert len(test_client.get("/api/orders", headers=headers).json()) == 3

        test_client.post("/api/cart/items", json={"product_id": 2}, headers=headers)
        emptied = test_client.delete("/api/cart/items/2", headers=headers)
        assert emptied.json()["items"] == []


def test_order_requires_cart_and_auth():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        assert test_client.post("/api/orders", headers=headers).status_code == 422
        assert test_client.post("/api/orders").status_code == 401
        assert test_client.post(
            "/api/login", json={"email": "student1@example.com", "password": "bad"}
        ).status_code == 401


def test_parallel_orders_create_exactly_one_order():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        test_client.post("/api/cart/items", json={"product_id": 4}, headers=headers)
        before = len(test_client.get("/api/orders", headers=headers).json())

        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = list(
                pool.map(
                    lambda _: test_client.post("/api/orders", headers=headers).status_code,
                    range(5),
                )
            )

        assert statuses.count(201) == 1
        assert statuses.count(422) == 4
        assert len(test_client.get("/api/orders", headers=headers).json()) == before + 1


def test_logout_clears_cookie_and_handles_bad_header():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        assert test_client.post("/api/logout", headers=headers).status_code == 204
        assert test_client.get("/api/orders", headers=headers).status_code == 401

        assert test_client.post(
            "/api/logout", headers={"Authorization": "garbage"}
        ).status_code == 204
        assert test_client.post(
            "/api/logout", headers={"Authorization": "Bearer"}
        ).status_code == 204

        response = test_client.post(
            "/ui/login",
            data={"email": "student1@example.com", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert test_client.get("/api/cart").status_code == 200
        assert test_client.post("/ui/logout", follow_redirects=False).status_code == 303
        assert test_client.get("/api/cart").status_code == 401
        assert "Сначала войдите" in test_client.get("/ui/cart").text


def test_logout_with_bearer_and_cookie_revokes_both():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        test_client.post(
            "/ui/login",
            data={"email": "student2@example.com", "password": "password123"},
            follow_redirects=False,
        )
        assert test_client.get("/api/cart").status_code == 200
        assert test_client.get("/api/cart", headers=headers).status_code == 200

        assert test_client.post("/api/logout", headers=headers).status_code == 204
        assert test_client.get("/api/cart").status_code == 401
        assert test_client.get("/api/cart", headers=headers).status_code == 401


def test_cyrillic_search_category_and_invalid_ui_product():
    with client() as test_client:
        assert len(test_client.get("/api/products", params={"q": "монитор"}).json()) == 1
        assert len(test_client.get("/api/products", params={"q": "Монитор"}).json()) == 1
        assert (
            len(
                test_client.get(
                    "/api/products", params={"category": "электроника"}
                ).json()
            )
            == 4
        )
        assert (
            len(
                test_client.get(
                    "/api/products", params={"category": "Электроника"}
                ).json()
            )
            == 4
        )

        test_client.post(
            "/ui/login",
            data={"email": "student1@example.com", "password": "password123"},
            follow_redirects=False,
        )
        test_client.post("/ui/cart/add", data={"product_id": 9999})
        assert test_client.get("/api/cart").json()["items"] == []


def test_stock_is_checked():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        assert (
            test_client.post(
                "/api/cart/items",
                json={"product_id": 8, "quantity": 100},
                headers=headers,
            ).status_code
            == 422
        )


def test_reset_restores_seed_data():
    with client() as test_client:
        token = login(test_client)
        headers = {"Authorization": f"Bearer {token}"}
        test_client.post("/api/cart/items", json={"product_id": 1}, headers=headers)

        assert test_client.post("/api/admin/reset").status_code == 403
        assert (
            test_client.post(
                "/api/admin/reset", headers={"X-Reset-Token": "test-reset"}
            ).status_code
            == 204
        )
        # Старый токен и корзина исчезли вместе с базой.
        assert test_client.get("/api/cart", headers=headers).status_code == 401
        assert len(test_client.get("/api/products").json()) == 12


def test_ui_pages_render():
    with client() as test_client:
        page = test_client.get("/")
        assert page.status_code == 200
        assert "Учебный магазин" in page.text
        response = test_client.post(
            "/ui/login",
            data={"email": "student1@example.com", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "stand_token" in response.cookies
