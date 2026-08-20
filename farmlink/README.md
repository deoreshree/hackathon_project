# FarmLink — Direct Farmer-to-Consumer Marketplace

> **Problem statement:** Farmers often depend on middlemen to sell their products,
> which reduces their profits, while consumers may pay higher prices. FarmLink is a
> full-stack marketplace that connects farmers directly with consumers and local
> businesses — farmers list products and manage quantity/price; buyers search,
> place orders, make payments, and track deliveries.

## What's built

| Problem-statement requirement | Where |
|---|---|
| Farmers list products | `Sell` tab — list, edit price/quantity, delete |
| Buyers search products | `Market` tab — live search + category filters |
| Place orders | Cart → checkout → order created, stock decremented |
| **Make payments** | Checkout: **UPI / Card / Cash on Delivery** (mock gateway). COD orders stay *Pending* until the farmer records receipt |
| **Track deliveries** | Every order shows a live timeline (`Placed → Picked → In transit → Delivered`) **with timestamps**, an ETA badge, and a payment-status badge |
| Android marketplace | Responsive **PWA** — installable on the Android home screen (manifest + service worker); the FastAPI backend is the API a native Android app would call |

Extras that fit the hackathon: **AI assistant** (answers in English / मराठी / हिंदी,
grounded in the actual store inventory), **AI product descriptions & price
suggestions** for farmers, full **EN / मराठी / हिंदी** UI, and secure API behavior
(validation, safe errors, rate limiting).

## Run it

```bash
# from the project root (uses the existing venv)
.\.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt
uvicorn farmlink.main:app --reload --port 8010
```

Open **http://127.0.0.1:8010/ui** (marketplace), **/docs** (API), **/health** (uptime).
LLM keys from `.env` are used automatically when present; without them the AI
features fall back to offline rules in the same languages.

## Demo script (2 minutes)

1. **Buyer** — search "tomato", add to cart, checkout with **Cash on Delivery**, place order.
2. **Orders** — see the badge `COD · Pending`, the ETA, and the timestamped timeline.
3. Switch to **Farmer** — advance the order (`Picked`, `In transit`); try `Delivered`
   before payment → blocked with a safe message. Click **₹ Payment received**, then deliver.
4. Try a UPI order → badge shows `Paid online` immediately, no payment step needed.
5. Switch to **मराठी / हिंदी** — the whole UI and the AI assistant switch language.
6. On a phone/tablet, **Add to Home screen** — FarmLink opens as a standalone app.

## API surface (all JSON, rate-limited)

```
GET  /api/products?search=&category=     list/search products
GET  /api/categories                     category chips
POST /api/products                       farmer lists a product
PUT  /api/products/{id}                  edit price / quantity
DELETE /api/products/{id}                remove listing
POST /api/orders                         checkout {buyer, phone, address, items, payment_method}
POST /api/orders/{id}/pay                record COD payment receipt
POST /api/orders/{id}/status             advance delivery status (timestamps recorded)
POST /api/ai/describe                    AI product description (lang: en|mr|hi)
POST /api/ai/price                       AI price suggestion
POST /api/ai/assistant                   AI assistant chat (grounded in inventory)
POST /api/translate                      translate a phrase
```

## Design notes

- **No database dependency** — products/orders persist to `farmlink/data/store.json`
  (gitignored; auto-seeded with 8 demo products on first run). Reset anytime by
  deleting that file.
- **Payments are mock** — UPI/card mark an order paid instantly; COD gates
  `Delivered` on recorded receipt. Swap in a real gateway (Razorpay/Stripe) at the
  single `create_order` call site.
- **Security posture mirrors the main app** — Pydantic validation with length caps,
  sanitized 422/500 responses (no stack traces or keys), per-IP rate limiting,
  secrets only from `.env`.

## Tests

```bash
pytest tests/test_farmlink.py -q     # 50 tests, fully offline
```

Covers the full order lifecycle, stock decrements, payment states, the
deliver-before-payment guard, status-history timestamps, i18n fallbacks, and the
security behaviors.
