"""FarmLink AI helpers — descriptions, price suggestions, assistant chat.

Uses the project's existing LLM provider (OpenAI / Groq) when an API key is
configured, and falls back to deterministic, offline templates in English,
Marathi and Hindi otherwise. Never raises on LLM failure — the app stays
usable offline (same philosophy as the fake-news detector's explainer).
"""

from __future__ import annotations

import logging
from typing import Any

from rag.explainer import LLMProvider, create_llm_provider

logger = logging.getLogger(__name__)

LANGUAGES = ("en", "mr", "hi")
LANGUAGE_NAMES = {
    "en": "English",
    "mr": "मराठी",
    "hi": "हिंदी",
}

# ---------------------------------------------------------------------------
# Category knowledge (offline fallbacks)
# ---------------------------------------------------------------------------

CATEGORY_BASE_PRICE: dict[str, float] = {
    "vegetables": 40,
    "fruits": 150,
    "grains": 80,
    "dairy & honey": 90,
    "spices": 120,
    "other": 60,
}

DESCRIPTION_TEMPLATES: dict[str, str] = {
    "en": "Fresh {name} from {farmer}'s farm. High quality, farm-direct, "
          "priced at {price} per {unit}. Order today and get it straight from the source.",
    "mr": "{farmer} च्या शेतातील ताजे {name}. उत्तम दर्जा, शेतातून थेट, "
          "प्रति {unit} किंमत ₹{price}. आजच ऑर्डर करा आणि थेट स्रोताकडून मिळवा.",
    "hi": "{farmer} के खेत का ताज़ा {name}। उच्च गुणवत्ता, सीधे खेत से, "
          "प्रति {unit} कीमत ₹{price}। आज ही ऑर्डर करें और सीधे स्रोत से पाएँ।",
}

ASSISTANT_FALLBACKS: dict[str, str] = {
    "en": ("I can help you buy fresh farm produce or sell your own harvest. "
           "Ask me things like: 'What vegetables are available?', "
           "'How do I list a product?', or 'Where is my order?'"),
    "mr": ("मी ताजे शेतमाल खरेदी करण्यात किंवा तुमचा स्वतःचा पिक विकण्यात मदत करू शकतो. "
           "मला असे विचारा: 'कोणत्या भाज्या उपलब्ध आहेत?', 'मी उत्पादन कसे सूचीबद्ध करू?', "
           "किंवा 'माझी ऑर्डर कुठे आहे?'"),
    "hi": ("मैं ताज़ी उपज खरीदने या अपनी फ़सल बेचने में आपकी मदद कर सकता हूँ। "
           "मुझसे ऐसे पूछें: 'कौन सी सब्ज़ियाँ उपलब्ध हैं?', 'मैं उत्पाद कैसे सूचीबद्ध करूँ?', "
           "या 'मेरा ऑर्डर कहाँ है?'"),
}

CATEGORY_ANSWERS: dict[str, dict[str, str]] = {
    "vegetables": {
        "en": "We have fresh vegetables like tomatoes, onions and spinach — "
              "check the Market tab and add them to your cart.",
        "mr": "आमच्याकडे टोमॅटो, कांदा आणि पालकसारख्या ताज्या भाज्या आहेत — "
              "मार्केट टॅबमध्ये पहा आणि कार्टमध्ये घाला.",
        "hi": "हमारे पास टमाटर, प्याज़ और पालक जैसी ताज़ी सब्ज़ियाँ हैं — "
              "मार्केट टैब देखें और कार्ट में डालें।",
    },
    "fruits": {
        "en": "Fruits like Alphonso mangoes are available fresh from orchards. "
              "Browse the Market tab to order.",
        "mr": "बागांमधून ताजे आंबे (अल्फान्सो) उपलब्ध आहेत. ऑर्डर करण्यासाठी मार्केट टॅब पहा.",
        "hi": "बगीचों से ताज़े आम (अल्फांसो) उपलब्ध हैं। ऑर्डर के लिए मार्केट टैब देखें।",
    },
}

SELL_ANSWERS: dict[str, dict[str, str]] = {
    "en": "To sell: switch to the Sell tab, fill in the product name, category, "
          "price and quantity, then press 'List product'. You can manage stock anytime.",
    "mr": "विक्रीसाठी: सेल टॅबवर जा, उत्पादनाचे नाव, श्रेणी, किंमत आणि प्रमाण भरा, "
          "मग 'List product' दाबा. तुम्ही कधीही स्टॉक व्यवस्थापित करू शकता.",
    "hi": "बेचने के लिए: सेल टैब पर जाएँ, उत्पाद का नाम, श्रेणी, कीमत और मात्रा भरें, "
          "फिर 'List product' दबाएँ। आप कभी भी स्टॉक प्रबंधित कर सकते हैं।",
}

ORDER_ANSWERS: dict[str, dict[str, str]] = {
    "en": "Your orders are listed in the Orders tab with a live status: "
          "placed → picked → in transit → delivered.",
    "mr": "तुमच्या ऑर्डर्स ऑर्डर्स टॅबमध्ये लाइव स्थितीसह आहेत: "
          "placed → picked → in transit → delivered.",
    "hi": "आपके ऑर्डर ऑर्डर्स टैब में लाइव स्थिति के साथ हैं: "
          "placed → picked → in transit → delivered।",
}


def _safe_lang(lang: str) -> str:
    lang = (lang or "en").strip().lower()
    return lang if lang in LANGUAGES else "en"


def _llm_available(provider: LLMProvider | None) -> bool:
    return provider is not None and type(provider).__name__ != "NoOpLLMProvider"


def _try_llm(
    provider: LLMProvider | None,
    system: str,
    user: str,
    *,
    max_tokens: int = 200,
) -> str | None:
    """One best-effort LLM call. Returns None on any failure."""
    if provider is None or not _llm_available(provider):
        return None
    try:
        text = provider.complete(system_prompt=system, user_prompt=user, max_tokens=max_tokens)
        return text.strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM call failed (%s); using offline fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def describe_product(
    *,
    name: str,
    category: str,
    price: float,
    unit: str,
    farmer: str,
    lang: str = "en",
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Generate a product description in the requested language."""
    lang = _safe_lang(lang)
    system = (
        "You write short, honest product descriptions for a farm marketplace. "
        "Never invent claims about the product. Reply with 1-2 sentences only."
    )
    user = (
        f"Write a short marketplace description for '{name}' "
        f"(category: {category}, price: {price} per {unit}, sold by {farmer}). "
        f"Respond in {LANGUAGE_NAMES[lang]}."
    )
    text = _try_llm(provider, system, user)
    if text:
        return {"description": text, "ai": True, "lang": lang}
    template = DESCRIPTION_TEMPLATES[lang]
    return {
        "description": template.format(name=name, farmer=farmer, price=price, unit=unit),
        "ai": False,
        "lang": lang,
    }


def suggest_price(
    *,
    name: str,
    category: str,
    lang: str = "en",
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Suggest a market price for a product (LLM first, category base fallback)."""
    lang = _safe_lang(lang)
    system = (
        "You are a farm market pricing expert in India. Given a product and "
        "category, reply with a single integer: a fair market price in rupees "
        "per kg. Reply with ONLY the number, nothing else."
    )
    user = f"Product: {name}. Category: {category}."
    text = _try_llm(provider, system, user)
    if text:
        try:
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                price = float(digits[:5])
                return {"price": price, "ai": True, "lang": lang}
        except ValueError:
            pass
    base = CATEGORY_BASE_PRICE.get(category.strip().lower(), CATEGORY_BASE_PRICE["other"])
    price = base
    return {"price": price, "ai": False, "lang": lang}


def assistant_reply(
    *,
    message: str,
    lang: str = "en",
    store_summary: str,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Answer a buyer/farmer question. LLM first, rule-based fallback."""
    lang = _safe_lang(lang)
    msg = (message or "").strip().lower()

    system = (
        "You are FarmLink, a friendly assistant for a farmer-to-consumer "
        "marketplace. Answer using ONLY the marketplace facts provided. "
        "Do not invent prices or products. Be concise (2-3 sentences). "
        f"Always reply in {LANGUAGE_NAMES[lang]}."
    )
    user = f"Marketplace data:\n{store_summary}\n\nUser question: {message}"
    text = _try_llm(provider, system, user, max_tokens=150)
    if text:
        return {"reply": text, "ai": True, "lang": lang}

    # Offline fallback — keyword matching on the translated message.
    if any(k in msg for k in ("sell", "list", "विक", "बेच", "सूचीबद्ध")):
        return {"reply": SELL_ANSWERS[lang], "ai": False, "lang": lang}
    if any(k in msg for k in ("order", "track", "ऑर्डर", "आदेश", "कुठे", "कहाँ")):
        return {"reply": ORDER_ANSWERS[lang], "ai": False, "lang": lang}
    if any(k in msg for k in ("vegetable", "भाज्या", "सब्जी", "tomato", "टोमॅटो")):
        return {"reply": CATEGORY_ANSWERS["vegetables"][lang], "ai": False, "lang": lang}
    if any(k in msg for k in ("fruit", "mango", "फळ", "आंबा", "आम")):
        return {"reply": CATEGORY_ANSWERS["fruits"][lang], "ai": False, "lang": lang}
    if any(k in msg for k in ("price", "किंमत", "कीमत", "cost", "खर्च")):
        return {
            "reply": f"{store_summary.strip()}",
            "ai": False,
            "lang": lang,
        }
    return {"reply": ASSISTANT_FALLBACKS[lang], "ai": False, "lang": lang}


def translate_text(
    *,
    text: str,
    target_lang: str,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Translate free text into the target language (LLM first, dictionary fallback)."""
    lang = _safe_lang(target_lang)
    if not text.strip() or lang == "en":
        return {"text": text.strip(), "ai": False, "lang": lang}
    system = (
        f"You are a translator. Translate the user's text into {LANGUAGE_NAMES[lang]}. "
        "Keep product names in English when appropriate. Reply with the translation only."
    )
    translated = _try_llm(provider, system, text)
    if translated:
        return {"text": translated, "ai": True, "lang": lang}
    # Offline fallback: word-level dictionary for common farm terms.
    words: dict[str, str] = {
        "tomatoes": "टोमॅटो", "onions": "कांदा", "mangoes": "आंबे",
        "milk": "दूध", "eggs": "अंडी", "honey": "मध", "rice": "तांदूळ",
    }
    if lang == "hi":
        words = {
            "tomatoes": "टमाटर", "onions": "प्याज़", "mangoes": "आम",
            "milk": "दूध", "eggs": "अंडे", "honey": "शहद", "rice": "चावल",
        }
    out = text
    for en, tr in words.items():
        out = out.replace(en, tr)
    return {"text": out, "ai": False, "lang": lang}


# ---------------------------------------------------------------------------
# Module-level provider cache
# ---------------------------------------------------------------------------

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider | None:
    """Get the shared LLM provider (created once, None if not configured)."""
    global _provider
    if _provider is None:
        try:
            candidate = create_llm_provider()
        except Exception:  # noqa: BLE001
            candidate = None
        if candidate is not None and type(candidate).__name__ != "NoOpLLMProvider":
            _provider = candidate
    return _provider
