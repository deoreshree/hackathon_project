/* AI Fake News Detector — interactive chat client.
   Vanilla JS, no frameworks. All rendered content is HTML-escaped. */

const chatArea = document.getElementById("chat-area");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const loadingIndicator = document.getElementById("loading-indicator");
const errorBanner = document.getElementById("error-banner");
const retryRow = document.getElementById("retry-row");
const retryButton = document.getElementById("retry-button");
const charCount = document.getElementById("char-count");
const themeToggle = document.getElementById("theme-toggle");
const newChatButton = document.getElementById("new-chat-button");

const STORAGE_KEY_SESSION = "factcheck.sessionId";
const STORAGE_KEY_CHAT = "factcheck.chatHtml";
const STORAGE_KEY_THEME = "factcheck.theme";
const MAX_LENGTH = 5000;

let sessionId = null;
let lastMessage = "";

const FOLLOW_UP_CHIPS = ["Why?", "What evidence?", "Show sources"];

/* ------------------------------------------------------------------ */
/* Small helpers                                                       */
/* ------------------------------------------------------------------ */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
  retryRow.classList.add("hidden");
}

function setLoading(isLoading) {
  loadingIndicator.classList.toggle("hidden", !isLoading);
  sendButton.disabled = isLoading;
  messageInput.disabled = isLoading;
}

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeEmptyState() {
  const empty = chatArea.querySelector(".empty-state");
  if (empty) empty.remove();
}

function appendMessage(role, html) {
  removeEmptyState();
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  wrapper.innerHTML = `
    <div class="message-label">${role === "user" ? "You" : "Assistant"}</div>
    ${html}
  `;
  chatArea.appendChild(wrapper);
  scrollToBottom();
  persistChat();
}

/* ------------------------------------------------------------------ */
/* Rendering                                                           */
/* ------------------------------------------------------------------ */

function verdictClass(verdict) {
  switch (String(verdict).toUpperCase()) {
    case "SUPPORTED":
      return "verdict-supported";
    case "CONTRADICTED":
      return "verdict-contradicted";
    case "MIXED":
      return "verdict-mixed";
    default:
      return "verdict-unverified";
  }
}

function verdictLabel(verdict) {
  const labels = {
    SUPPORTED: "Supported by evidence",
    CONTRADICTED: "Contradicted by evidence",
    MIXED: "Mixed evidence",
    UNVERIFIED: "Insufficient evidence",
  };
  return labels[String(verdict).toUpperCase()] || String(verdict);
}

function renderEvidenceSection(title, items, { open = false } = {}) {
  if (!items.length) return "";
  const list = items
    .map(
      (item) => `
        <li>
          <strong>${escapeHtml(item.source)}</strong>: ${escapeHtml(item.text)}
          ${
            item.url
              ? `<a class="evidence-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">View source ↗</a>`
              : ""
          }
        </li>`
    )
    .join("");
  return `
    <details class="evidence-section" ${open ? "open" : ""}>
      <summary>${escapeHtml(title)} (${items.length})</summary>
      <ul>${list}</ul>
    </details>
  `;
}

function renderSources(sources) {
  if (!sources.length) {
    return "<p class='muted-text'>No sources available.</p>";
  }
  return `<ul>${sources
    .map((source) => {
      const label = escapeHtml(source.title || source.url);
      const url = escapeHtml(source.url);
      return `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a></li>`;
    })
    .join("")}</ul>`;
}

function renderConfidence(data) {
  const confidence = Number(data.confidence) || 0;
  const percent = Math.round(Math.min(1, Math.max(0, confidence)) * 100);
  const badge = verdictClass(data.verdict);
  return `
    <div class="confidence" title="Confidence ${percent}%">
      <div class="confidence-label">Confidence ${percent}%</div>
      <div class="confidence-track">
        <div class="confidence-fill ${badge}" style="width: ${percent}%"></div>
      </div>
    </div>
  `;
}

function renderAssistantResponse(data) {
  const badge = verdictClass(data.verdict);
  const chips = data.is_follow_up
    ? ""
    : `<div class="quick-replies">
        ${FOLLOW_UP_CHIPS.map(
          (chip) => `<button type="button" class="quick-reply-chip" data-message="${escapeHtml(chip)}">${escapeHtml(chip)}</button>`
        ).join("")}
      </div>`;
  return `
    <div class="verdict ${badge}" title="${escapeHtml(verdictLabel(data.verdict))}">${escapeHtml(
    verdictLabel(data.verdict)
  )}</div>
    ${renderConfidence(data)}
    <div class="answer">${escapeHtml(data.answer)}</div>
    <div class="meta">${
      data.is_follow_up
        ? "Follow-up response — based on the previous claim's evidence."
        : "Claim analysed against retrieved web evidence."
    }</div>
    ${renderEvidenceSection("Supporting Evidence", data.supporting_evidence || [], { open: true })}
    ${renderEvidenceSection("Contradicting Evidence", data.contradicting_evidence || [])}
    ${renderEvidenceSection("Neutral Evidence", data.neutral_evidence || [])}
    <details class="evidence-section sources-section">
      <summary>Sources (${(data.sources || []).length})</summary>
      ${renderSources(data.sources || [])}
    </details>
    ${chips}
  `;
}

function renderErrorDetail(detail) {
  if (!detail) return "The backend returned an error.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item.message || "Invalid value").join("; ");
  }
  return JSON.stringify(detail);
}

/* ------------------------------------------------------------------ */
/* Persistence                                                         */
/* ------------------------------------------------------------------ */

function persistChat() {
  try {
    localStorage.setItem(STORAGE_KEY_CHAT, chatArea.innerHTML);
    if (sessionId) localStorage.setItem(STORAGE_KEY_SESSION, sessionId);
  } catch (_) {
    /* storage may be unavailable — the chat still works in-memory */
  }
}

function restoreChat() {
  try {
    const savedChat = localStorage.getItem(STORAGE_KEY_CHAT);
    if (savedChat) {
      chatArea.innerHTML = savedChat;
      scrollToBottom();
    }
    sessionId = localStorage.getItem(STORAGE_KEY_SESSION);
  } catch (_) {
    /* ignore */
  }
}

function clearStorage() {
  try {
    localStorage.removeItem(STORAGE_KEY_CHAT);
    localStorage.removeItem(STORAGE_KEY_SESSION);
  } catch (_) {
    /* ignore */
  }
}

/* ------------------------------------------------------------------ */
/* Theme                                                               */
/* ------------------------------------------------------------------ */

function applyTheme(theme) {
  document.body.classList.toggle("dark", theme === "dark");
  themeToggle.textContent = theme === "dark" ? "☀ Light" : "🌙 Dark";
}

function initTheme() {
  let theme = null;
  try {
    theme = localStorage.getItem(STORAGE_KEY_THEME);
  } catch (_) {
    /* ignore */
  }
  applyTheme(theme === "dark" ? "dark" : "light");
}

themeToggle.addEventListener("click", () => {
  const next = document.body.classList.contains("dark") ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(STORAGE_KEY_THEME, next);
  } catch (_) {
    /* ignore */
  }
});

/* ------------------------------------------------------------------ */
/* Sending messages                                                    */
/* ------------------------------------------------------------------ */

async function sendMessage(message) {
  lastMessage = message;
  clearError();
  setLoading(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(renderErrorDetail(data && data.detail));
    }
    if (!data || !data.verdict || !data.answer) {
      throw new Error("Invalid response from backend.");
    }

    sessionId = data.session_id;
    appendMessage("assistant", renderAssistantResponse(data));
  } catch (error) {
    showError(error.message || "Unable to reach the fact-checking backend.");
    retryRow.classList.remove("hidden");
  } finally {
    setLoading(false);
  }
}

function submitCurrentInput() {
  const message = messageInput.value.trim();
  if (!message) {
    showError("Please enter a claim or question.");
    return;
  }
  appendMessage("user", `<div class="user-text">${escapeHtml(message)}</div>`);
  messageInput.value = "";
  updateCharCount();
  sendMessage(message);
}

/* ------------------------------------------------------------------ */
/* New chat                                                            */
/* ------------------------------------------------------------------ */

function newChat() {
  sessionId = null;
  chatArea.innerHTML = `<div class="empty-state">
    <p>Ask a claim to fact-check, or pick an example below.</p>
  </div>`;
  clearError();
  messageInput.value = "";
  updateCharCount();
  clearStorage();
  messageInput.focus();
}

newChatButton.addEventListener("click", newChat);

/* ------------------------------------------------------------------ */
/* Event wiring                                                        */
/* ------------------------------------------------------------------ */

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitCurrentInput();
});

messageInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    submitCurrentInput();
  }
});

function updateCharCount() {
  charCount.textContent = `${messageInput.value.length} / ${MAX_LENGTH}`;
}

messageInput.addEventListener("input", updateCharCount);

document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    messageInput.value = chip.dataset.claim || "";
    updateCharCount();
    chatForm.requestSubmit();
  });
});

retryButton.addEventListener("click", () => {
  if (lastMessage) sendMessage(lastMessage);
});

// Event delegation: quick-reply and retry chips inside the chat area.
chatArea.addEventListener("click", (event) => {
  const chip = event.target.closest(".quick-reply-chip");
  if (chip && chip.dataset.message) {
    appendMessage("user", `<div class="user-text">${escapeHtml(chip.dataset.message)}</div>`);
    sendMessage(chip.dataset.message);
    return;
  }
});

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */

initTheme();
restoreChat();
if (!chatArea.querySelector(".message")) {
  chatArea.innerHTML = `<div class="empty-state">
    <p>Ask a claim to fact-check, or pick an example below.</p>
  </div>`;
}
updateCharCount();
