"""FarmLink — end-to-end API tests.

All external services (LLM) are mocked/disabled: tests pin the API-key env
vars to empty so the offline fallbacks run. The store is isolated to a temp
file per test so nothing touches the demo data.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.rate_limit import RateLimiter
from farmlink import ai as ai_service
from farmlink import main as farmlink_main
from farmlink.store import Store


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A TestClient with an isolated store and offline LLM."""
    # Offline LLM: pin keys to empty (load_dotenv never overrides existing vars).
    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    ai_service._provider = None  # clear any cached provider

    # Isolated store per test.
    store = Store(tmp_path / "store.json")
    monkeypatch.setattr(farmlink_main, "store", store)
    monkeypatch.setattr(farmlink_main.app.state, "rate_limiter",
                        RateLimiter(max_requests=1000, enabled=True))

    with TestClient(farmlink_main.app) as c:
        yield c


# ---------------------------------------------------------------------------
# A. Health & pages
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_root(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert "FarmLink" in body["message"]
    assert body["ui"] == "/ui"


def test_ui_page_served(client: TestClient) -> None:
    res = client.get("/ui")
    assert res.status_code == 200
    assert "FarmLink" in res.text
    assert "app.js" in res.text


# ---------------------------------------------------------------------------
# B. Products
# ---------------------------------------------------------------------------


def test_list_products_seeded(client: TestClient) -> None:
    res = client.get("/api/products")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] > 0
    names = {p["name"] for p in body["products"]}
    assert "Fresh Tomatoes" in names


def test_search_products(client: TestClient) -> None:
    res = client.get("/api/products", params={"search": "tomato"})
    body = res.json()
    assert body["count"] >= 1
    assert all("tomato" in p["name"].lower() for p in body["products"])


def test_filter_by_category(client: TestClient) -> None:
    res = client.get("/api/products", params={"category": "Vegetables"})
    body = res.json()
    assert body["count"] >= 1
    assert all(p["category"] == "Vegetables" for p in body["products"])


def test_categories_endpoint(client: TestClient) -> None:
    res = client.get("/api/categories")
    assert res.status_code == 200
    assert "Vegetables" in res.json()["categories"]


def test_add_product(client: TestClient) -> None:
    payload = {
        "name": "Fresh Coriander",
        "category": "Vegetables",
        "price": 15,
        "quantity": 40,
        "unit": "bunch",
        "farmer": "Test Farmer",
        "description": "Fresh coriander leaves.",
    }
    res = client.post("/api/products", json=payload)
    assert res.status_code == 201
    product = res.json()["product"]
    assert product["name"] == "Fresh Coriander"
    assert product["price"] == 15.0


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": 10, "quantity": 5},           # blank name
        {"name": "x" * 81, "price": 10, "quantity": 5},     # name too long
        {"name": "Ok", "price": 0, "quantity": 5},          # non-positive price
        {"name": "Ok", "price": 10, "quantity": 0},         # non-positive quantity
        {"name": "Ok", "price": "ten", "quantity": 5},      # wrong data type
        {"name": "Ok", "price": 10, "quantity": 5, "farmer": "   "},  # blank farmer
    ],
)
def test_add_product_rejects_invalid(client: TestClient, payload: dict) -> None:
    res = client.post("/api/products", json=payload)
    assert res.status_code == 422


def test_add_product_rejects_missing_fields(client: TestClient) -> None:
    res = client.post("/api/products", json={"price": 10})
    assert res.status_code == 422


def test_update_product_stock(client: TestClient) -> None:
    product_id = client.get("/api/products").json()["products"][0]["id"]
    res = client.put(f"/api/products/{product_id}", json={"price": 55, "quantity": 10})
    assert res.status_code == 200
    product = res.json()["product"]
    assert product["price"] == 55.0
    assert product["quantity"] == 10.0


def test_update_unknown_product_404(client: TestClient) -> None:
    res = client.put("/api/products/999999", json={"price": 10})
    assert res.status_code == 404


def test_delete_product(client: TestClient) -> None:
    product_id = client.get("/api/products").json()["products"][0]["id"]
    res = client.delete(f"/api/products/{product_id}")
    assert res.status_code == 200
    assert res.json()["deleted"] == product_id
    # The product is gone from the listing.
    ids = {p["id"] for p in client.get("/api/products").json()["products"]}
    assert product_id not in ids


def test_delete_unknown_product_404(client: TestClient) -> None:
    res = client.delete("/api/products/999999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# C. Orders
# ---------------------------------------------------------------------------


def test_order_flow_decrements_stock(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    before = product["quantity"]
    res = client.post("/api/orders", json={
        "buyer": "Priya Sharma",
        "phone": "9876543210",
        "address": "Pune, Maharashtra",
        "items": [{"product_id": product["id"], "quantity": 2}],
    })
    assert res.status_code == 201
    order = res.json()["order"]
    assert order["status"] == "placed"
    assert order["total"] == round(product["price"] * 2, 2)
    assert order["items"][0]["name"] == product["name"]

    after = client.get("/api/products").json()["products"][0]["quantity"]
    assert after == before - 2


def test_order_insufficient_stock(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    res = client.post("/api/orders", json={
        "buyer": "Priya",
        "phone": "9876543210",
        "address": "Pune",
        "items": [{"product_id": product["id"], "quantity": product["quantity"] + 100}],
    })
    assert res.status_code == 400
    assert "available" in res.json()["detail"].lower()


def test_order_empty_cart_rejected(client: TestClient) -> None:
    res = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune", "items": [],
    })
    assert res.status_code == 422


def test_order_invalid_item_404(client: TestClient) -> None:
    res = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune",
        "items": [{"product_id": 999999, "quantity": 1}],
    })
    assert res.status_code == 400


def test_order_missing_buyer_422(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    res = client.post("/api/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
    })
    assert res.status_code == 422


def test_order_status_advance_and_guard(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order_id = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune",
        "items": [{"product_id": product["id"], "quantity": 1}],
    }).json()["order"]["id"]

    for status in ("picked", "in_transit", "delivered"):
        res = client.post(f"/api/orders/{order_id}/status", json={"status": status})
        assert res.status_code == 200
        assert res.json()["order"]["status"] == status

    # Moving backwards is rejected.
    res = client.post(f"/api/orders/{order_id}/status", json={"status": "placed"})
    assert res.status_code == 400


def test_order_status_unknown_order_404(client: TestClient) -> None:
    res = client.post("/api/orders/999999/status", json={"status": "picked"})
    assert res.status_code == 404


def test_order_status_invalid_value(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order_id = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune",
        "items": [{"product_id": product["id"], "quantity": 1}],
    }).json()["order"]["id"]
    res = client.post(f"/api/orders/{order_id}/status", json={"status": "exploded"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# C2. Payments & delivery tracking
# ---------------------------------------------------------------------------


def _place_order(client: TestClient, product_id: int, payment_method: str = "upi") -> dict:
    res = client.post("/api/orders", json={
        "buyer": "Priya Sharma",
        "phone": "9876543210",
        "address": "Pune, Maharashtra",
        "payment_method": payment_method,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    assert res.status_code == 201
    return res.json()["order"]


def test_order_paid_online_by_default(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"])
    assert order["payment_method"] == "upi"
    assert order["payment_status"] == "paid"


def test_order_cod_starts_unpaid(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"], payment_method="cod")
    assert order["payment_method"] == "cod"
    assert order["payment_status"] == "unpaid"


def test_order_invalid_payment_method_422(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    res = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune",
        "payment_method": "bitcoin",
        "items": [{"product_id": product["id"], "quantity": 1}],
    })
    assert res.status_code == 422


def test_order_status_history_records_timestamps(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"])
    assert order["status_history"][0] == {"status": "placed", "at": order["created_at"]}

    order_id = order["id"]
    res = client.post(f"/api/orders/{order_id}/status", json={"status": "picked"})
    assert res.status_code == 200
    history = res.json()["order"]["status_history"]
    assert [h["status"] for h in history] == ["placed", "picked"]
    assert history[-1]["at"] >= history[0]["at"]


def test_order_has_delivery_eta(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"])
    assert order["delivery_eta"] > order["created_at"]


def test_cod_cannot_be_delivered_before_payment(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"], payment_method="cod")
    order_id = order["id"]
    for status in ("picked", "in_transit"):
        res = client.post(f"/api/orders/{order_id}/status", json={"status": status})
        assert res.status_code == 200
    # Marking delivered before collecting payment is rejected with a safe message.
    res = client.post(f"/api/orders/{order_id}/status", json={"status": "delivered"})
    assert res.status_code == 400
    assert "payment" in res.json()["detail"].lower()


def test_mark_order_paid_then_deliver(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"], payment_method="cod")
    order_id = order["id"]

    # Farmer records payment received.
    res = client.post(f"/api/orders/{order_id}/pay")
    assert res.status_code == 200
    assert res.json()["order"]["payment_status"] == "paid"

    # Now delivery is allowed.
    res = client.post(f"/api/orders/{order_id}/status", json={"status": "delivered"})
    assert res.status_code == 200
    assert res.json()["order"]["status"] == "delivered"


def test_pay_already_paid_order_rejected(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    order = _place_order(client, product["id"])  # upi -> already paid
    res = client.post(f"/api/orders/{order['id']}/pay")
    assert res.status_code == 400
    assert "already paid" in res.json()["detail"].lower()


def test_pay_unknown_order_404(client: TestClient) -> None:
    res = client.post("/api/orders/999999/pay")
    assert res.status_code == 404


def test_list_orders_filter_by_buyer(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    client.post("/api/orders", json={
        "buyer": "Priya Sharma", "phone": "1", "address": "Pune",
        "items": [{"product_id": product["id"], "quantity": 1}],
    })
    res = client.get("/api/orders", params={"buyer": "Priya Sharma"})
    assert res.status_code == 200
    assert all(o["buyer"] == "Priya Sharma" for o in res.json()["orders"])


# ---------------------------------------------------------------------------
# D. AI (offline fallbacks)
# ---------------------------------------------------------------------------


def test_ai_describe_offline_marathi(client: TestClient) -> None:
    res = client.post("/api/ai/describe", json={
        "name": "Fresh Tomatoes",
        "category": "Vegetables",
        "price": 40,
        "unit": "kg",
        "farmer": "Ramesh",
        "lang": "mr",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["ai"] is False
    assert body["lang"] == "mr"
    # Marathi text contains Devanagari characters.
    assert any("\u0900" <= ch <= "\u097f" for ch in body["description"])


def test_ai_describe_offline_hindi(client: TestClient) -> None:
    res = client.post("/api/ai/describe", json={
        "name": "Onions", "category": "Vegetables", "price": 35,
        "unit": "kg", "farmer": "Suresh", "lang": "hi",
    })
    body = res.json()
    assert any("\u0900" <= ch <= "\u097f" for ch in body["description"])


def test_ai_price_offline(client: TestClient) -> None:
    res = client.post("/api/ai/price", json={"name": "Carrots", "category": "Vegetables"})
    assert res.status_code == 200
    assert res.json()["price"] > 0


def test_ai_assistant_offline_selling(client: TestClient) -> None:
    res = client.post("/api/ai/assistant", json={"message": "How do I sell my produce?", "lang": "en"})
    assert res.status_code == 200
    assert "Sell" in res.json()["reply"] or "sell" in res.json()["reply"]


def test_ai_assistant_offline_marathi(client: TestClient) -> None:
    res = client.post("/api/ai/assistant", json={"message": "ऑर्डर कुठे आहे?", "lang": "mr"})
    body = res.json()
    assert body["lang"] == "mr"
    assert "ऑर्डर" in body["reply"]


def test_ai_assistant_empty_message_422(client: TestClient) -> None:
    res = client.post("/api/ai/assistant", json={"message": "", "lang": "en"})
    assert res.status_code == 422


def test_translate_dictionary_offline(client: TestClient) -> None:
    res = client.post("/api/translate", json={"text": "fresh tomatoes", "lang": "mr"})
    assert res.status_code == 200
    assert "टोमॅटो" in res.json()["text"]


# ---------------------------------------------------------------------------
# E. Security behavior
# ---------------------------------------------------------------------------


def test_validation_error_does_not_echo_input(client: TestClient) -> None:
    payload = {"name": "secret-token-abc123", "price": -5, "quantity": 1}
    res = client.post("/api/products", json=payload)
    assert res.status_code == 422
    assert "secret-token-abc123" not in res.text


def test_error_responses_do_not_leak_keys(client: TestClient) -> None:
    product = client.get("/api/products").json()["products"][0]
    res = client.post("/api/orders", json={
        "buyer": "Priya", "phone": "1", "address": "Pune",
        "items": [{"product_id": product["id"], "quantity": 1}],
    })
    for key in ("OPENAI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY", "Bearer", "api_key"):
        assert key not in res.text


def test_cors_headers_present(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") == "*"


def test_rate_limit_returns_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(farmlink_main.app.state, "rate_limiter", RateLimiter(max_requests=3))
    for _ in range(3):
        assert client.post("/api/ai/price", json={"name": "X", "category": "Other"}).status_code == 200
    res = client.post("/api/ai/price", json={"name": "X", "category": "Other"})
    assert res.status_code == 429


def test_invalid_json_body_422(client: TestClient) -> None:
    res = client.post("/api/products", content=b"{not valid json", headers={"Content-Type": "application/json"})
    assert res.status_code == 422


def test_llm_failure_falls_back_safely(client: TestClient) -> None:
    """A failing LLM provider must not break the endpoint (offline fallback)."""
    class BrokenProvider:
        def complete(self, system_prompt: str, user_prompt: str, **kwargs: object) -> str:
            raise RuntimeError("LLM boom")

    with patch.object(ai_service, "get_provider", return_value=BrokenProvider()):
        res = client.post("/api/ai/assistant", json={"message": "hello", "lang": "en"})
    assert res.status_code == 200
    body = res.json()
    assert body["ai"] is False
    assert body["reply"]
