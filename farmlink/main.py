"""FarmLink — FastAPI backend for the farmer-to-consumer marketplace.

Full stack (web demo of the hackathon idea):
  - Products: list, search, filter, add (farmer), update stock, delete
  - Orders:   checkout from cart, live status tracking
  - AI:       product descriptions, price suggestions, assistant chat
  - i18n:     UI in English / मराठी / हिंदी, AI replies in the chosen language

Security posture (mirrors the fake-news detector):
  - Pydantic validation with length caps and blank rejection
  - Safe error messages — no stack traces, keys, or internal paths
  - In-memory rate limiting on public endpoints (reuses backend.rate_limit)
  - Secrets only from environment variables (.env), never returned to clients
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from backend.rate_limit import RateLimiter, create_rate_limiter
from farmlink import ai as ai_service
from farmlink.store import Store, StoreError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="FarmLink API",
    description="Direct farmer-to-consumer marketplace with AI assistant and i18n",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

store = Store()
app.state.rate_limiter: RateLimiter = create_rate_limiter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="Other", max_length=40)
    price: float = Field(gt=0, le=1_000_000)
    quantity: float = Field(gt=0, le=1_000_000)
    unit: str = Field(default="kg", max_length=20)
    farmer: str = Field(default="Farmer", max_length=80)
    description: str = Field(default="", max_length=2000)

    @field_validator("name", "category", "unit", "farmer")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value


class ProductUpdate(BaseModel):
    price: float | None = Field(default=None, gt=0, le=1_000_000)
    quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=2000)


class CartItem(BaseModel):
    product_id: int
    quantity: float = Field(gt=0, le=10_000)


class OrderIn(BaseModel):
    buyer: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=1, max_length=20)
    address: str = Field(min_length=1, max_length=500)
    items: list[CartItem] = Field(min_length=1, max_length=50)
    payment_method: Literal["upi", "card", "cod"] = "upi"

    @field_validator("buyer", "phone", "address")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value


class StatusIn(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class LangIn(BaseModel):
    lang: str = Field(default="en", max_length=10)


class DescribeIn(LangIn):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="Other", max_length=40)
    price: float = Field(gt=0, le=1_000_000)
    unit: str = Field(default="kg", max_length=20)
    farmer: str = Field(default="Farmer", max_length=80)


class PriceIn(LangIn):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="Other", max_length=40)


class AssistantIn(LangIn):
    message: str = Field(min_length=1, max_length=2000)


class TranslateIn(LangIn):
    text: str = Field(min_length=1, max_length=2000)


# ---------------------------------------------------------------------------
# Security: safe error handling
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Sanitized 422 — field/message only, never the raw input value."""
    errors: list[dict[str, str]] = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err.get("loc", []) if part != "body")
        errors.append(
            {
                "field": location or "body",
                "message": str(err.get("msg", "Invalid value")),
            }
        )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


def rate_limit_dependency(request: Request) -> None:
    limiter: RateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again shortly.",
        )


# ---------------------------------------------------------------------------
# Routes — page
# ---------------------------------------------------------------------------


@app.get("/")
def root() -> dict:
    return {
        "message": "FarmLink — Direct Farmer-to-Consumer Marketplace",
        "status": "running",
        "version": "1.0.0",
        "ui": "/ui",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "farmlink-api"}


@app.get("/ui", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    try:
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: farmlink/static/index.html not found</h1>",
            status_code=404,
        )


# ---------------------------------------------------------------------------
# Routes — products
# ---------------------------------------------------------------------------


@app.get("/api/products")
def list_products(search: str = "", category: str = "") -> dict:
    return {
        "products": store.list_products(search=search, category=category),
        "count": len(store.list_products(search=search, category=category)),
    }


@app.get("/api/categories")
def list_categories() -> dict:
    categories = sorted(
        {p.get("category", "Other") for p in store.list_products()}
    )
    return {"categories": categories}


@app.post("/api/products", status_code=201)
def add_product(data: ProductIn, _: None = Depends(rate_limit_dependency)) -> dict:
    try:
        product = store.add_product(
            name=data.name,
            category=data.category,
            price=data.price,
            quantity=data.quantity,
            unit=data.unit,
            farmer=data.farmer,
            description=data.description,
        )
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"product": product}


@app.put("/api/products/{product_id}")
def update_product(product_id: int, data: ProductUpdate) -> dict:
    updated = store.update_product(
        product_id,
        **{k: v for k, v in data.model_dump().items() if v is not None},
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"product": updated}


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int) -> dict:
    if not store.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"deleted": product_id}


# ---------------------------------------------------------------------------
# Routes — orders
# ---------------------------------------------------------------------------


@app.get("/api/orders")
def list_orders(buyer: str = "", farmer: str = "") -> dict:
    return {"orders": store.list_orders(buyer=buyer, farmer=farmer)}


@app.post("/api/orders", status_code=201)
def create_order(data: OrderIn, _: None = Depends(rate_limit_dependency)) -> dict:
    try:
        order = store.create_order(
            buyer=data.buyer,
            phone=data.phone,
            address=data.address,
            items=[item.model_dump() for item in data.items],
            payment_method=data.payment_method,
        )
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"order": order}


@app.post("/api/orders/{order_id}/pay")
def mark_order_paid(order_id: int) -> dict:
    """Record payment receipt — used for cash-on-delivery orders."""
    try:
        order = store.mark_order_paid(order_id)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return {"order": order}


@app.post("/api/orders/{order_id}/status")
def set_order_status(order_id: int, data: StatusIn) -> dict:
    try:
        order = store.set_order_status(order_id, data.status)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return {"order": order}


# ---------------------------------------------------------------------------
# Routes — AI
# ---------------------------------------------------------------------------


@app.post("/api/ai/describe")
def ai_describe(data: DescribeIn, _: None = Depends(rate_limit_dependency)) -> dict:
    return ai_service.describe_product(
        name=data.name,
        category=data.category,
        price=data.price,
        unit=data.unit,
        farmer=data.farmer,
        lang=data.lang,
        provider=ai_service.get_provider(),
    )


@app.post("/api/ai/price")
def ai_price(data: PriceIn, _: None = Depends(rate_limit_dependency)) -> dict:
    return ai_service.suggest_price(
        name=data.name,
        category=data.category,
        lang=data.lang,
        provider=ai_service.get_provider(),
    )


@app.post("/api/ai/assistant")
def ai_assistant(data: AssistantIn, _: None = Depends(rate_limit_dependency)) -> dict:
    summary = _build_store_summary()
    return ai_service.assistant_reply(
        message=data.message,
        lang=data.lang,
        store_summary=summary,
        provider=ai_service.get_provider(),
    )


@app.post("/api/translate")
def translate(data: TranslateIn, _: None = Depends(rate_limit_dependency)) -> dict:
    return ai_service.translate_text(
        text=data.text,
        target_lang=data.lang,
        provider=ai_service.get_provider(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_store_summary() -> str:
    """A compact, grounded summary of the store for the AI assistant."""
    products = store.list_products()[:12]
    if not products:
        return "The marketplace currently has no products listed."
    lines = [
        f"- {p['name']} ({p.get('category', 'Other')}): ₹{p['price']:g} per "
        f"{p.get('unit', 'kg')}, {p['quantity']:g} available, farmer: {p.get('farmer')}"
        for p in products
    ]
    return "Available products:\n" + "\n".join(lines)
