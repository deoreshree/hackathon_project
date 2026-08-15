const chatArea = document.getElementById("chat-area");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const loadingIndicator = document.getElementById("loading-indicator");
const errorBanner = document.getElementById("error-banner");

let sessionId = null;

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
}

function setLoading(isLoading) {
  loadingIndicator.classList.toggle("hidden", !isLoading);
  sendButton.disabled = isLoading;
  messageInput.disabled = isLoading;
}

function appendMessage(role, html) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  wrapper.innerHTML = `
    <div class="message-label">${role === "user" ? "You" : "Assistant"}</div>
    ${html}
  `;
  chatArea.appendChild(wrapper);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function renderEvidenceList(items) {
  if (!items.length) {
    return "<p>None found.</p>";
  }
  return `<ul>${items
    .map(
      (item) =>
        `<li><strong>${escapeHtml(item.source)}</strong>: ${escapeHtml(item.text)}</li>`
    )
    .join("")}</ul>`;
}

function renderSources(sources) {
  if (!sources.length) {
    return "<p>No sources available.</p>";
  }
  return `<ul>${sources
    .map((source) => {
      const label = escapeHtml(source.title || source.url);
      const url = escapeHtml(source.url);
      return `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a></li>`;
    })
    .join("")}</ul>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderAssistantResponse(data) {
  return `
    <div class="verdict">${escapeHtml(data.verdict)}</div>
    <div>${escapeHtml(data.answer)}</div>
    <div class="meta">Confidence: ${Number(data.confidence).toFixed(2)}${
      data.is_follow_up ? " · Follow-up response" : ""
    }</div>
    <div class="section">
      <h4>Supporting Evidence</h4>
      ${renderEvidenceList(data.supporting_evidence || [])}
    </div>
    <div class="section">
      <h4>Contradicting Evidence</h4>
      ${renderEvidenceList(data.contradicting_evidence || [])}
    </div>
    <div class="section">
      <h4>Sources</h4>
      ${renderSources(data.sources || [])}
    </div>
  `;
}

async function sendMessage(message) {
  clearError();
  setLoading(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const detail = data && data.detail ? data.detail : "The backend returned an error.";
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    if (!data || !data.verdict || !data.answer) {
      throw new Error("Invalid response from backend.");
    }

    sessionId = data.session_id;
    appendMessage("assistant", renderAssistantResponse(data));
  } catch (error) {
    showError(error.message || "Unable to reach the fact-checking backend.");
  } finally {
    setLoading(false);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    showError("Please enter a claim or question.");
    return;
  }

  appendMessage("user", `<div>${escapeHtml(message)}</div>`);
  messageInput.value = "";
  await sendMessage(message);
});
