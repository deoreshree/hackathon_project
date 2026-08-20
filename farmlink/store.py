"""FarmLink data store — products and orders persisted to a JSON file.

Kept deliberately simple (single JSON file, in-memory cache) so the
hackathon demo survives server restarts without a database dependency.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_STORE_PATH = Path(__file__).resolve().parent / "data" / "store.json"

ORDER_STATUSES = ("placed", "picked", "in_transit", "delivered")
PAYMENT_METHODS = ("upi", "card", "cod")
# Mock delivery ETA: 48 hours from placement (hackathon demo).
DELIVERY_ETA_SECONDS = 2 * 24 * 3600


class StoreError(Exception):
    """Raised for user-facing store errors (safe messages only)."""


def _now() -> float:
    return time.time()


class Store:
    """Thread-safe product + order store with JSON persistence."""

    def __init__(self, path: Path | str = DEFAULT_STORE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._products: list[dict[str, Any]] = []
        self._orders: list[dict[str, Any]] = []
        self._next_product_id = 1
        self._next_order_id = 1
        self._load()
        if not self._products:
            self._seed()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._products = data.get("products", [])
            self._orders = data.get("orders", [])
            self._next_product_id = data.get("next_product_id", 1)
            self._next_order_id = data.get("next_order_id", 1)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable store — start fresh rather than crash.
            self._products, self._orders = [], []

    def save(self) -> None:
        with self._lock:
            self.path.write_text(
                json.dumps(
                    {
                        "products": self._products,
                        "orders": self._orders,
                        "next_product_id": self._next_product_id,
                        "next_order_id": self._next_order_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def list_products(
        self,
        search: str = "",
        category: str = "",
    ) -> list[dict[str, Any]]:
        with self._lock:
            results = list(self._products)
        search = search.strip().lower()
        category = category.strip()
        if search:
            results = [
                p
                for p in results
                if search in p["name"].lower() or search in p.get("description", "").lower()
            ]
        if category:
            results = [p for p in results if p.get("category", "").lower() == category.lower()]
        return sorted(results, key=lambda p: p.get("created_at", 0), reverse=True)

    def get_product(self, product_id: int) -> dict[str, Any] | None:
        with self._lock:
            for p in self._products:
                if p["id"] == product_id:
                    return dict(p)
        return None

    def add_product(
        self,
        *,
        name: str,
        category: str,
        price: float,
        quantity: float,
        unit: str,
        farmer: str,
        description: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            product = {
                "id": self._next_product_id,
                "name": name.strip(),
                "category": category.strip() or "Other",
                "price": round(float(price), 2),
                "quantity": float(quantity),
                "unit": unit.strip() or "kg",
                "farmer": farmer.strip() or "Farmer",
                "description": description.strip(),
                "created_at": _now(),
            }
            self._next_product_id += 1
            self._products.append(product)
            self.save()
            return dict(product)

    def update_product(self, product_id: int, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            for p in self._products:
                if p["id"] != product_id:
                    continue
                if "price" in fields:
                    p["price"] = round(float(fields["price"]), 2)
                if "quantity" in fields:
                    p["quantity"] = float(fields["quantity"])
                if "name" in fields and fields["name"].strip():
                    p["name"] = fields["name"].strip()
                if "description" in fields:
                    p["description"] = fields["description"].strip()
                self.save()
                return dict(p)
        return None

    def delete_product(self, product_id: int) -> bool:
        with self._lock:
            before = len(self._products)
            self._products = [p for p in self._products if p["id"] != product_id]
            if len(self._products) == before:
                return False
            self.save()
            return True

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def create_order(
        self,
        *,
        buyer: str,
        phone: str,
        address: str,
        items: list[dict[str, Any]],
        payment_method: str = "upi",
    ) -> dict[str, Any]:
        """Create an order, validating stock and decrementing quantities.

        UPI / card orders are marked paid immediately (mock gateway);
        cash-on-delivery stays unpaid until the farmer confirms receipt.
        """
        with self._lock:
            if not items:
                raise StoreError("Cart is empty.")
            order_items: list[dict[str, Any]] = []
            total = 0.0
            for item in items:
                product_id = int(item["product_id"])
                qty = float(item["quantity"])
                if qty <= 0:
                    raise StoreError("Quantity must be greater than zero.")
                stored = next(
                    (p for p in self._products if p["id"] == product_id),
                    None,
                )
                if stored is None:
                    raise StoreError("A product in your cart is no longer available.")
                if stored["quantity"] < qty:
                    raise StoreError(
                        f"Only {stored['quantity']:g} {stored.get('unit', 'kg')} "
                        f"of '{stored['name']}' are available."
                    )
                stored["quantity"] -= qty
                order_items.append(
                    {
                        "product_id": product_id,
                        "name": stored["name"],
                        "price": stored["price"],
                        "quantity": qty,
                        "unit": stored.get("unit", "kg"),
                    }
                )
                total += stored["price"] * qty
            payment_method = payment_method.strip().lower()
            if payment_method not in PAYMENT_METHODS:
                raise StoreError(
                    f"Invalid payment method. Use one of: {', '.join(PAYMENT_METHODS)}."
                )
            now = _now()
            order = {
                "id": self._next_order_id,
                "buyer": buyer.strip(),
                "phone": phone.strip(),
                "address": address.strip(),
                "items": order_items,
                "total": round(total, 2),
                "status": "placed",
                "payment_method": payment_method,
                # UPI / card are considered paid instantly (mock gateway);
                # COD is settled on delivery.
                "payment_status": "paid" if payment_method != "cod" else "unpaid",
                "status_history": [{"status": "placed", "at": now}],
                "delivery_eta": now + DELIVERY_ETA_SECONDS,
                "created_at": now,
            }
            self._next_order_id += 1
            self._orders.append(order)
            self.save()
            return dict(order)

    def list_orders(self, *, buyer: str = "", farmer: str = "") -> list[dict[str, Any]]:
        with self._lock:
            results = list(self._orders)
        if buyer:
            results = [o for o in results if o["buyer"].lower() == buyer.strip().lower()]
        if farmer:
            results = [
                o
                for o in results
                if any(
                    item.get("farmer", "") == farmer
                    for item in o.get("items", [])
                )
            ]
        return sorted(results, key=lambda o: o.get("created_at", 0), reverse=True)

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with self._lock:
            for o in self._orders:
                if o["id"] == order_id:
                    return dict(o)
        return None

    def set_order_status(self, order_id: int, status: str) -> dict[str, Any] | None:
        """Advance an order to a later status, recording the timestamp.

        Delivery is only allowed once payment has been received — this mirrors
        the real-world rule that COD is settled before the goods are handed over.
        """
        status = status.strip().lower()
        if status not in ORDER_STATUSES:
            raise StoreError(
                f"Invalid status '{status}'. Use one of: {', '.join(ORDER_STATUSES)}."
            )
        with self._lock:
            for o in self._orders:
                if o["id"] != order_id:
                    continue
                current = o["status"]
                if current not in ORDER_STATUSES:
                    o["status"] = status
                elif ORDER_STATUSES.index(status) < ORDER_STATUSES.index(current):
                    raise StoreError("Order status cannot move backwards.")
                if status == "delivered" and o.get("payment_status") != "paid":
                    raise StoreError(
                        "Payment not received yet — collect payment before marking delivered."
                    )
                o["status"] = status
                o.setdefault("status_history", []).append({"status": status, "at": _now()})
                self.save()
                return dict(o)
        return None

    def mark_order_paid(self, order_id: int) -> dict[str, Any] | None:
        """Mark an order as paid (used for cash-on-delivery)."""
        with self._lock:
            for o in self._orders:
                if o["id"] != order_id:
                    continue
                if o.get("payment_status") == "paid":
                    raise StoreError("This order is already paid.")
                o["payment_status"] = "paid"
                self.save()
                return dict(o)
        return None

    # ------------------------------------------------------------------
    # Demo seed data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        seeds = [
            ("Fresh Tomatoes", "Vegetables", 40, 120, "kg", "Ramesh Patil",
             "Sun-ripened tomatoes picked fresh from the farm every morning."),
            ("Organic Onions", "Vegetables", 35, 200, "kg", "Suresh Gaikwad",
             "Pesticide-free onions, ideal for daily cooking."),
            ("Basmati Rice 5kg", "Grains", 480, 60, "bag", "Krishna Farms",
             "Aged basmati rice with a rich aroma."),
            ("Raw Honey 1L", "Dairy & Honey", 350, 30, "bottle", "Sunita Honey Farm",
             "Pure, unprocessed honey collected from native bee hives."),
            ("Fresh Cow Milk", "Dairy & Honey", 60, 100, "litre", "Gokul Dairy",
             "Farm-fresh milk delivered the same morning."),
            ("Green Spinach", "Vegetables", 25, 80, "bunch", "Ramesh Patil",
             "Leafy spinach harvested the same day."),
            ("Alphonso Mangoes", "Fruits", 900, 50, "box", "Konkan Orchards",
             "Premium Alphonso mangoes straight from Ratnagiri."),
            ("Free-Range Eggs", "Dairy & Honey", 90, 45, "dozen", "Gokul Dairy",
             "Eggs from free-range hens raised on organic feed."),
        ]
        for name, category, price, qty, unit, farmer, desc in seeds:
            self.add_product(
                name=name,
                category=category,
                price=price,
                quantity=qty,
                unit=unit,
                farmer=farmer,
                description=desc,
            )
        self.save()
