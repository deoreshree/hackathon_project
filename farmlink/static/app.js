/* FarmLink — interactive marketplace SPA.
 * Vanilla JS. Features: search + category filter, cart & checkout,
 * farmer listings, order status tracking, AI assistant chat,
 * and a full English / मराठी / हिंदी UI with persistence.
 */
"use strict";

const I18N = {
  en: {
    tagline: "Direct from farm to you",
    buyer: "Buyer", farmer: "Farmer",
    market: "Market", sell: "Sell", orders: "Orders", assistant: "AI Assistant",
    search_ph: "Search products…",
    add_cart: "Add to cart", in_stock: "in stock", sold_by: "Sold by",
    no_products: "No products found.",
    list_product: "List a product",
    f_name: "Product name", f_category: "Category", f_price: "Price (₹)",
    f_qty: "Quantity", f_unit: "Unit", f_farmer: "Your name", f_desc: "Description",
    ai_describe: "✨ AI describe", ai_price: "✨ AI suggest price", list_btn: "List product",
    my_listings: "My listings", edit_stock: "Edit stock", del: "Delete", save: "Save",
    no_listings: "You haven't listed any products yet.",
    no_orders: "No orders yet.",
    checkout: "Checkout", checkout_name: "Your name", f_phone: "Phone", f_address: "Delivery address",
    cancel: "Cancel", place_order: "Place order", total: "Total",
    order_placed: "Order placed successfully! 🎉",
    cart_empty: "Your cart is empty.",
    order_by: "Order", placed: "Placed", picked: "Picked", in_transit: "In transit", delivered: "Delivered",
    advance: "Next status", buyer_lbl: "Buyer", items: "items",
    chat_ph: "Ask about products, selling, or your order…", send: "Send",
    assistant_hello: "Hi! I'm FarmLink's assistant. Ask me about what's available, how to sell, or how to track your order. 🌾",
    typing: "FarmLink is thinking…",
    try_again: "Try again", view_sources: "View", adding: "Adding…",
    empty_cart: "Your cart is empty — add products from the Market.",
    need_farmer_name: "Enter your name first (Your name field).",
    desc_generated: "AI description added", price_generated: "AI price suggestion: ₹",
    toast_error: "Something went wrong. Please try again.",
    search_all: "All",
    confirm_delete: "Delete this product?",
    status_updated: "Status updated",
    pay_method: "Payment method",
    pay_upi: "UPI", pay_upi_sub: "GPay · PhonePe · Paytm",
    pay_card: "Card", pay_card_sub: "Credit / debit",
    pay_cod: "Cash on delivery", pay_cod_sub: "Pay when it arrives",
    paid: "Paid", unpaid: "Pending", mark_paid: "₹ Payment received",
    payment_received: "Payment recorded ✅", pay_online: "Paid online",
    eta: "Expected delivery", delivered_on: "Delivered",
    lang_saved: "Language: ",
  },
  mr: {
    tagline: "शेतातून थेट तुमच्यापर्यंत",
    buyer: "खरेदीदार", farmer: "शेतकरी",
    market: "बाजार", sell: "विक्री", orders: "ऑर्डर्स", assistant: "AI सहाय्यक",
    search_ph: "उत्पादने शोधा…",
    add_cart: "कार्टमध्ये घाला", in_stock: "स्टॉकमध्ये", sold_by: "विक्रेता",
    no_products: "उत्पादने सापडली नाहीत.",
    list_product: "उत्पादन सूचीबद्ध करा",
    f_name: "उत्पादनाचे नाव", f_category: "श्रेणी", f_price: "किंमत (₹)",
    f_qty: "प्रमाण", f_unit: "एकक", f_farmer: "तुमचे नाव", f_desc: "वर्णन",
    ai_describe: "✨ AI वर्णन", ai_price: "✨ AI किंमत सुचवा", list_btn: "उत्पादन सूचीबद्ध करा",
    my_listings: "माझी सूची", edit_stock: "स्टॉक बदला", del: "हटवा", save: "जतन करा",
    no_listings: "तुम्ही अजून उत्पादने सूचीबद्ध केलेली नाहीत.",
    no_orders: "अजून ऑर्डर्स नाहीत.",
    checkout: "चेकआउट", checkout_name: "तुमचे नाव", f_phone: "फोन", f_address: "डिलिव्हरी पत्ता",
    cancel: "रद्द करा", place_order: "ऑर्डर द्या", total: "एकूण",
    order_placed: "ऑर्डर यशस्वीरित्या दिली! 🎉",
    cart_empty: "तुमची कार्ट रिकामी आहे.",
    order_by: "ऑर्डर", placed: "दिली", picked: "उचलली", in_transit: "मार्गात", delivered: "पोहोचली",
    advance: "पुढील स्थिती", buyer_lbl: "खरेदीदार", items: "वस्तू",
    chat_ph: "उत्पादने, विक्री किंवा ऑर्डरबद्दल विचारा…", send: "पाठवा",
    assistant_hello: "नमस्कार! मी FarmLink चा सहाय्यक आहे. काय उपलब्ध आहे, कसे विकायचे, किंवा ऑर्डर कशी ट्रॅक करायची हे विचारा. 🌾",
    typing: "FarmLink विचार करत आहे…",
    try_again: "पुन्हा प्रयत्न करा", view_sources: "पहा", adding: "जोडत आहे…",
    empty_cart: "तुमची कार्ट रिकामी आहे — बाजारातून उत्पादने घाला.",
    need_farmer_name: "आधी तुमचे नाव भरा (तुमचे नाव फील्ड).",
    desc_generated: "AI वर्णन जोडले", price_generated: "AI किंमत सूचना: ₹",
    toast_error: "काहीतरी चूक झाली. कृपया पुन्हा प्रयत्न करा.",
    search_all: "सर्व",
    confirm_delete: "हे उत्पादन हटवायचे?",
    status_updated: "स्थिती अपडेट केली",
    pay_method: "पेमेंट पद्धत",
    pay_upi: "UPI", pay_upi_sub: "GPay · PhonePe · Paytm",
    pay_card: "कार्ड", pay_card_sub: "क्रेडिट / डेबिट",
    pay_cod: "डिलिव्हरीवर रोख", pay_cod_sub: "पोहोचल्यावर पैसे द्या",
    paid: "पैसे भरले", unpaid: "बाकी आहे", mark_paid: "₹ पैसे मिळाले",
    payment_received: "पेमेंट नोंदवले ✅", pay_online: "ऑनलाइन भरले",
    eta: "अपेक्षित डिलिव्हरी", delivered_on: "पोहोचली",
    lang_saved: "भाषा: ",
  },
  hi: {
    tagline: "सीधे खेत से आप तक",
    buyer: "खरीदार", farmer: "किसान",
    market: "मार्केट", sell: "बेचें", orders: "ऑर्डर", assistant: "AI सहायक",
    search_ph: "उत्पाद खोजें…",
    add_cart: "कार्ट में डालें", in_stock: "स्टॉक में", sold_by: "विक्रेता",
    no_products: "कोई उत्पाद नहीं मिला।",
    list_product: "उत्पाद सूचीबद्ध करें",
    f_name: "उत्पाद का नाम", f_category: "श्रेणी", f_price: "कीमत (₹)",
    f_qty: "मात्रा", f_unit: "इकाई", f_farmer: "आपका नाम", f_desc: "विवरण",
    ai_describe: "✨ AI विवरण", ai_price: "✨ AI कीमत सुझाएँ", list_btn: "उत्पाद सूचीबद्ध करें",
    my_listings: "मेरी सूची", edit_stock: "स्टॉक बदलें", del: "हटाएँ", save: "सहेजें",
    no_listings: "आपने अभी तक कोई उत्पाद सूचीबद्ध नहीं किया।",
    no_orders: "अभी कोई ऑर्डर नहीं।",
    checkout: "चेकआउट", checkout_name: "आपका नाम", f_phone: "फ़ोन", f_address: "डिलीवरी पता",
    cancel: "रद्द करें", place_order: "ऑर्डर दें", total: "कुल",
    order_placed: "ऑर्डर सफलतापूर्वक दिया गया! 🎉",
    cart_empty: "आपकी कार्ट खाली है।",
    order_by: "ऑर्डर", placed: "दिया गया", picked: "उठाया गया", in_transit: "रास्ते में", delivered: "पहुँच गया",
    advance: "अगली स्थिति", buyer_lbl: "खरीदार", items: "वस्तुएँ",
    chat_ph: "उत्पाद, बेचने या अपने ऑर्डर के बारे में पूछें…", send: "भेजें",
    assistant_hello: "नमस्ते! मैं FarmLink का सहायक हूँ। पूछें कि क्या उपलब्ध है, कैसे बेचें, या अपना ऑर्डर कैसे ट्रैक करें। 🌾",
    typing: "FarmLink सोच रहा है…",
    try_again: "फिर से कोशिश करें", view_sources: "देखें", adding: "जोड़ रहे हैं…",
    empty_cart: "आपकी कार्ट खाली है — मार्केट से उत्पाद जोड़ें।",
    need_farmer_name: "पहले अपना नाम भरें (आपका नाम फ़ील्ड)।",
    desc_generated: "AI विवरण जोड़ा गया", price_generated: "AI कीमत सुझाव: ₹",
    toast_error: "कुछ गलत हो गया। कृपया फिर से कोशिश करें।",
    search_all: "सभी",
    confirm_delete: "यह उत्पाद हटाएँ?",
    status_updated: "स्थिति अपडेट की गई",
    pay_method: "भुगतान विधि",
    pay_upi: "UPI", pay_upi_sub: "GPay · PhonePe · Paytm",
    pay_card: "कार्ड", pay_card_sub: "क्रेडिट / डेबिट",
    pay_cod: "डिलीवरी पर नकद", pay_cod_sub: "पहुँचने पर भुगतान करें",
    paid: "भुगतान हुआ", unpaid: "बकाया", mark_paid: "₹ भुगतान मिला",
    payment_received: "भुगतान दर्ज किया गया ✅", pay_online: "ऑनलाइन भुगतान",
    eta: "अपेक्षित डिलीवरी", delivered_on: "डिलीवर हुआ",
    lang_saved: "भाषा: ",
  },
};

const CATEGORY_EMOJI = {
  Vegetables: "🥬", Fruits: "🍎", Grains: "🌾",
  "Dairy & Honey": "🥛", Spices: "🌶️", Other: "📦",
};

const state = {
  lang: localStorage.getItem("farmlink_lang") || "en",
  role: localStorage.getItem("farmlink_role") || "buyer",
  products: [],
  categories: [],
  cart: {}, // product_id -> qty
  myListings: [],
  myOrders: [],
  farmerName: localStorage.getItem("farmlink_farmer") || "",
  buyerName: localStorage.getItem("farmlink_buyer") || "",
  search: "",
  category: "",
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (html !== undefined) node.innerHTML = html;
  return node;
};
const t = (key) => I18N[state.lang][key] || I18N.en[key] || key;
const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.00$/, ""));

/* ------------------------------------------------------------------ */
/* API helpers                                                         */
/* ------------------------------------------------------------------ */

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = {};
  try { body = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.message).join("; ")
      : body.detail || t("toast_error");
    throw new Error(detail);
  }
  return body;
}

function toast(message, isError = false) {
  const node = $("#toast");
  node.textContent = message;
  node.className = `toast show ${isError ? "error" : ""}`;
  clearTimeout(node._timer);
  node._timer = setTimeout(() => { node.className = "toast"; }, 3200);
}

/* ------------------------------------------------------------------ */
/* Rendering                                                           */
/* ------------------------------------------------------------------ */

function applyI18n() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((n) => { n.placeholder = t(n.dataset.i18nPh); });
  document.querySelectorAll(".lang-btn").forEach((b) => b.classList.toggle("active", b.dataset.lang === state.lang));
  document.querySelectorAll(".role-btn").forEach((b) => b.classList.toggle("active", b.dataset.role === state.role));
  document.title = state.lang === "en" ? "FarmLink — Farmer-to-Consumer Marketplace"
    : state.lang === "mr" ? "FarmLink — शेतकरी-ते-ग्राहक बाजार" : "FarmLink — किसान-से-उपभोक्ता मार्केटप्लेस";
}

function renderCategories() {
  const wrap = $("#category-chips");
  wrap.innerHTML = "";
  const all = el("button", `chip ${state.category === "" ? "active" : ""}`, t("search_all"));
  all.onclick = () => { state.category = ""; renderCategories(); renderProducts(); };
  wrap.appendChild(all);
  state.categories.forEach((cat) => {
    const chip = el("button", `chip ${state.category === cat ? "active" : ""}`,
      `${CATEGORY_EMOJI[cat] || "📦"} ${cat}`);
    chip.onclick = () => { state.category = cat; renderCategories(); renderProducts(); };
    wrap.appendChild(chip);
  });
}

function renderProducts() {
  const grid = $("#product-grid");
  const empty = $("#market-empty");
  grid.innerHTML = "";
  const filtered = state.products.filter((p) => {
    const q = state.search.toLowerCase();
    const inSearch = !q || p.name.toLowerCase().includes(q) || (p.description || "").toLowerCase().includes(q);
    const inCat = !state.category || p.category === state.category;
    return inSearch && inCat;
  });
  empty.classList.toggle("hidden", filtered.length > 0);

  filtered.forEach((p) => {
    const card = el("div", "product-card");
    const qtyInCart = state.cart[p.id] || 0;
    const out = p.quantity <= 0;
    card.innerHTML = `
      <div class="product-emoji">${CATEGORY_EMOJI[p.category] || "📦"}</div>
      <div class="product-name">${escapeHtml(p.name)}</div>
      <div class="product-cat">${escapeHtml(p.category)}</div>
      <div class="product-desc">${escapeHtml(p.description || "")}</div>
      <div class="product-price">₹${fmt(p.price)} <span class="unit">/ ${escapeHtml(p.unit)}</span></div>
      <div class="product-meta">${t("in_stock")}: ${fmt(p.quantity)} ${escapeHtml(p.unit)} · ${t("sold_by")} ${escapeHtml(p.farmer)}</div>
    `;
    if (state.role === "buyer" && !out) {
      const btn = el("button", "btn primary add-btn", qtyInCart > 0 ? `${t("add_cart")} (${qtyInCart})` : t("add_cart"));
      btn.onclick = () => addToCart(p.id);
      card.appendChild(btn);
    } else if (state.role === "buyer" && out) {
      card.appendChild(el("div", "sold-out", "SOLD OUT"));
    }
    grid.appendChild(card);
  });
}

function renderCartFab() {
  const count = Object.values(state.cart).reduce((a, b) => a + b, 0);
  $("#cart-count").textContent = count;
  $("#cart-fab").classList.toggle("hidden", count === 0);
}

function addToCart(productId) {
  state.cart[productId] = (state.cart[productId] || 0) + 1;
  renderCartFab();
  renderProducts();
  toast(`🛒 +1`);
}

function renderSellFormState() {
  $("#sell-form").querySelector('[name="farmer"]').value = state.farmerName;
}

function renderMyListings() {
  const wrap = $("#my-listings");
  wrap.innerHTML = "";
  const mine = state.products.filter((p) => p.farmer === state.farmerName);
  if (mine.length === 0) {
    wrap.appendChild(el("p", "muted", t("no_listings")));
    return;
  }
  const table = el("table", "table");
  table.innerHTML = `
    <thead><tr>
      <th>${t("f_name")}</th><th>${t("f_price")}</th><th>${t("f_qty")}</th><th>${t("f_unit")}</th><th></th>
    </tr></thead><tbody></tbody>`;
  const tbody = table.querySelector("tbody");
  mine.forEach((p) => {
    const row = el("tr");
    row.innerHTML = `
      <td class="name-cell">${escapeHtml(p.name)}</td>
      <td><input type="number" class="price-input" min="0.01" step="0.01" value="${p.price}" /></td>
      <td><input type="number" class="qty-input" min="0.01" step="0.01" value="${fmt(p.quantity)}" /></td>
      <td>${escapeHtml(p.unit)}</td>
      <td class="row-actions">
        <button class="btn small save-btn">${t("save")}</button>
        <button class="btn small danger del-btn">${t("del")}</button>
      </td>`;
    row.querySelector(".save-btn").onclick = async () => {
      try {
        await api(`/api/products/${p.id}`, {
          method: "PUT",
          body: JSON.stringify({
            price: parseFloat(row.querySelector(".price-input").value),
            quantity: parseFloat(row.querySelector(".qty-input").value),
          }),
        });
        toast(t("status_updated"));
        await refreshProducts();
      } catch (err) { toast(err.message, true); }
    };
    row.querySelector(".del-btn").onclick = async () => {
      if (!confirm(t("confirm_delete"))) return;
      try {
        await api(`/api/products/${p.id}`, { method: "DELETE" });
        await refreshProducts();
      } catch (err) { toast(err.message, true); }
    };
    tbody.appendChild(row);
  });
  wrap.appendChild(table);
}

const STATUS_STEPS = ["placed", "picked", "in_transit", "delivered"];
const STATUS_KEYS = { placed: "placed", picked: "picked", in_transit: "in_transit", delivered: "delivered" };
const PAY_EMOJI = { upi: "📱", card: "💳", cod: "💵" };

function fmtTime(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function historyAt(order, status) {
  const entry = (order.status_history || []).find((h) => h.status === status);
  return entry ? entry.at : null;
}

function renderOrders() {
  const list = $("#orders-list");
  const empty = $("#orders-empty");
  list.innerHTML = "";
  const orders = state.role === "farmer" ? state.allOrders : state.myOrders;
  empty.classList.toggle("hidden", orders.length > 0);

  orders.forEach((o) => {
    const card = el("div", "card order-card");
    const stepIdx = STATUS_STEPS.indexOf(o.status);
    const isPaid = o.payment_status === "paid";
    const payKey = o.payment_method || "upi";
    const paidTxt = isPaid ? (payKey === "cod" ? t("paid") : t("pay_online")) : t("unpaid");
    const steps = STATUS_STEPS.map((s, i) => {
      const at = historyAt(o, s);
      const when = at ? fmtTime(at) : (i === STATUS_STEPS.length - 1 ? fmtTime(o.delivery_eta) : "");
      return `<div class="step ${i <= stepIdx ? "done" : ""}">
        ${t(STATUS_KEYS[s])}
        ${when ? `<span class="step-time">${when}</span>` : ""}
      </div>`;
    });
    card.innerHTML = `
      <div class="order-head">
        <strong>${t("order_by")} #${o.id}</strong>
        <span class="order-buyer">${t("buyer_lbl")}: ${escapeHtml(o.buyer)}</span>
      </div>
      <div class="order-badges">
        <span class="badge pay-badge ${isPaid ? "ok" : "warn"}">${PAY_EMOJI[payKey] || "💳"} ${payKey.toUpperCase()} · ${escapeHtml(paidTxt)}</span>
        ${o.status === "delivered"
          ? `<span class="badge ok">✅ ${escapeHtml(t("delivered_on"))}</span>`
          : `<span class="badge eta">🚚 ${escapeHtml(t("eta"))}: ${fmtTime(o.delivery_eta)}</span>`}
      </div>
      <ul class="order-items">
        ${o.items.map((it) => `<li>${escapeHtml(it.name)} × ${fmt(it.quantity)} ${escapeHtml(it.unit)} — ₹${fmt(it.price * it.quantity)}</li>`).join("")}
      </ul>
      <div class="order-total">${t("total")}: <strong>₹${fmt(o.total)}</strong></div>
      <div class="stepper">${steps.join("")}</div>
      ${o.address ? `<div class="muted">📍 ${escapeHtml(o.address)} · ${escapeHtml(o.phone)}</div>` : ""}
    `;
    // Farmer: record COD payment once received.
    if (state.role === "farmer" && !isPaid && payKey === "cod") {
      const payBtn = el("button", "btn small ok-btn", t("mark_paid"));
      payBtn.onclick = async () => {
        try {
          await api(`/api/orders/${o.id}/pay`, { method: "POST" });
          toast(t("payment_received"));
          await refreshAll();
        } catch (err) { toast(err.message, true); }
      };
      card.appendChild(payBtn);
    }
    if (state.role === "farmer" && stepIdx < STATUS_STEPS.length - 1) {
      const btn = el("button", "btn primary", t("advance") + " →");
      btn.onclick = async () => {
        try {
          await api(`/api/orders/${o.id}/status`, {
            method: "POST",
            body: JSON.stringify({ status: STATUS_STEPS[stepIdx + 1] }),
          });
          toast(t("status_updated"));
          await refreshAll();
        } catch (err) { toast(err.message, true); }
      };
      card.appendChild(btn);
    }
    list.appendChild(card);
  });
}

function renderCheckoutModal() {
  const box = $("#cart-items");
  box.innerHTML = "";
  let total = 0;
  Object.entries(state.cart).forEach(([id, qty]) => {
    const p = state.products.find((x) => String(x.id) === id);
    if (!p) return;
    total += p.price * qty;
    const row = el("div", "cart-row");
    row.innerHTML = `
      <span>${CATEGORY_EMOJI[p.category] || ""} ${escapeHtml(p.name)} × ${fmt(qty)} ${escapeHtml(p.unit)}</span>
      <span>₹${fmt(p.price * qty)}</span>`;
    box.appendChild(row);
  });
  box.appendChild(el("div", "cart-total", `${t("total")}: <strong>₹${fmt(total)}</strong>`));
}

function renderChat() {
  const log = $("#chat-log");
  const quick = $("#chat-quick");
  log.innerHTML = "";
  if (state.chat.length === 0) {
    log.appendChild(el("div", "msg bot", escapeHtml(t("assistant_hello"))));
  }
  state.chat.forEach((m) => {
    log.appendChild(el("div", `msg ${m.role}`, escapeHtml(m.text)));
  });
  const chips = ["🛒 What's available?", "🌱 How do I sell?", "🚚 Track my order", "💰 Best price for tomatoes"];
  quick.innerHTML = "";
  chips.forEach((label) => {
    const chip = el("button", "chip", label);
    chip.onclick = () => sendChat(label.replace(/^\S+\s/, ""));
    quick.appendChild(chip);
  });
  log.scrollTop = log.scrollHeight;
}

/* ------------------------------------------------------------------ */
/* Data loading                                                        */
/* ------------------------------------------------------------------ */

async function refreshProducts() {
  const data = await api("/api/products");
  state.products = data.products;
  const cats = await api("/api/categories");
  state.categories = cats.categories;
  renderCategories();
  renderProducts();
  renderMyListings();
}

async function refreshOrders() {
  const buyer = state.role === "buyer" ? state.buyerName : "";
  state.myOrders = (await api(`/api/orders?buyer=${encodeURIComponent(buyer)}`)).orders;
  state.allOrders = (await api("/api/orders")).orders;
  renderOrders();
}

async function refreshAll() {
  await refreshProducts();
  await refreshOrders();
}

/* ------------------------------------------------------------------ */
/* Actions                                                             */
/* ------------------------------------------------------------------ */

async function handleSellSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form).entries());
  data.price = parseFloat(data.price);
  data.quantity = parseFloat(data.quantity);
  state.farmerName = data.farmer;
  localStorage.setItem("farmlink_farmer", data.farmer);
  try {
    await api("/api/products", { method: "POST", body: JSON.stringify(data) });
    form.reset();
    $("#sell-form [name=farmer]").value = state.farmerName;
    toast("✅ " + t("list_btn"));
    await refreshProducts();
  } catch (err) { toast(err.message, true); }
}

async function handleCheckout(e) {
  e.preventDefault();
  const form = e.target;
  const buyer = form.buyer.value.trim();
  const items = Object.entries(state.cart).map(([product_id, quantity]) => ({ product_id: Number(product_id), quantity }));
  const paymentMethod = (form.elements.payment_method && form.elements.payment_method.value) || "upi";
  try {
    const res = await api("/api/orders", {
      method: "POST",
      body: JSON.stringify({ buyer, phone: form.phone.value.trim(), address: form.address.value.trim(), items, payment_method: paymentMethod }),
    });
    state.buyerName = buyer;
    localStorage.setItem("farmlink_buyer", buyer);
    state.cart = {};
    renderCartFab();
    closeModal();
    toast(t("order_placed"));
    form.reset();
    await refreshAll();
  } catch (err) { toast(err.message, true); }
}

async function sendChat(text) {
  const message = (text || $("#chat-input").value).trim();
  if (!message) return;
  $("#chat-input").value = "";
  state.chat.push({ role: "user", text: message });
  renderChat();
  const typing = el("div", "msg bot typing-dot", t("typing"));
  $("#chat-log").appendChild(typing);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
  try {
    const res = await api("/api/ai/assistant", {
      method: "POST",
      body: JSON.stringify({ message, lang: state.lang }),
    });
    typing.remove();
    state.chat.push({ role: "bot", text: res.reply });
  } catch (err) {
    typing.remove();
    state.chat.push({ role: "bot", text: err.message });
  }
  renderChat();
}

/* ------------------------------------------------------------------ */
/* Tabs / modal / language                                             */
/* ------------------------------------------------------------------ */

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  if (name === "sell") { renderSellFormState(); renderMyListings(); }
  if (name === "orders") refreshOrders();
  if (name === "assistant") renderChat();
}

function openModal() {
  if (Object.keys(state.cart).length === 0) { toast(t("empty_cart")); return; }
  renderCheckoutModal();
  $("#checkout-modal").classList.remove("hidden");
}

function closeModal() {
  $("#checkout-modal").classList.add("hidden");
}

function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("farmlink_lang", lang);
  applyI18n();
  refreshAll();
  renderChat();
  renderCartFab();
}

function setRole(role) {
  state.role = role;
  localStorage.setItem("farmlink_role", role);
  applyI18n();
  if (role === "farmer") renderSellFormState();
  refreshAll();
  if ($("#tab-sell").classList.contains("active")) switchTab("sell");
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */

function registerServiceWorker() {
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => { /* offline-first is a bonus */ });
  }
}

function init() {
  state.chat = [];
  applyI18n();
  registerServiceWorker();

  document.querySelectorAll(".lang-btn").forEach((b) =>
    b.addEventListener("click", () => setLang(b.dataset.lang)));
  document.querySelectorAll(".role-btn").forEach((b) =>
    b.addEventListener("click", () => setRole(b.dataset.role)));
  document.querySelectorAll(".tab").forEach((b) =>
    b.addEventListener("click", () => switchTab(b.dataset.tab)));

  $("#search-input").addEventListener("input", (e) => {
    state.search = e.target.value;
    renderProducts();
  });

  $("#sell-form").addEventListener("submit", handleSellSubmit);
  $("#checkout-form").addEventListener("submit", handleCheckout);
  $("#checkout-cancel").onclick = closeModal;
  $("#cart-fab").onclick = openModal;
  $("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat(); });

  $("#ai-describe").onclick = async () => {
    const form = $("#sell-form");
    const name = form.name.value.trim();
    const category = form.category.value.trim() || "Other";
    const price = parseFloat(form.price.value);
    const unit = form.unit.value.trim() || "kg";
    const farmer = form.farmer.value.trim() || state.farmerName;
    if (!name || !price) { toast(t("need_farmer_name")); return; }
    try {
      const res = await api("/api/ai/describe", {
        method: "POST",
        body: JSON.stringify({ name, category, price, unit, farmer, lang: state.lang }),
      });
      form.description.value = res.description;
      toast(t("desc_generated") + (res.ai ? " ✨" : ""));
    } catch (err) { toast(err.message, true); }
  };

  $("#ai-price").onclick = async () => {
    const form = $("#sell-form");
    const name = form.name.value.trim();
    const category = form.category.value.trim() || "Other";
    if (!name) { toast(t("need_farmer_name")); return; }
    try {
      const res = await api("/api/ai/price", {
        method: "POST",
        body: JSON.stringify({ name, category, lang: state.lang }),
      });
      form.price.value = res.price;
      toast(t("price_generated") + fmt(res.price) + (res.ai ? " ✨" : ""));
    } catch (err) { toast(err.message, true); }
  };

  // ESC closes the checkout modal
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  refreshAll()
    .then(() => { if (state.role === "farmer") renderSellFormState(); })
    .catch((err) => toast(err.message, true));
  renderChat();
}

document.addEventListener("DOMContentLoaded", init);
