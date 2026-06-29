const LOGO_URL = "/static/logo.svg";

const state = {
  conversationId: null,
  conversations: [],
  isLoading: false,
  pendingDeleteId: null,
};

const els = {
  sidebar: document.getElementById("sidebar"),
  sidebarOverlay: document.getElementById("sidebarOverlay"),
  chatsToggleBtn: document.getElementById("chatsToggleBtn"),
  chatList: document.getElementById("chatList"),
  newChatBtn: document.getElementById("newChatBtn"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  chatTitle: document.getElementById("chatTitle"),
  chatArea: document.getElementById("chatArea"),
  welcomeScreen: document.getElementById("welcomeScreen"),
  messages: document.getElementById("messages"),
  questionInput: document.getElementById("questionInput"),
  sendBtn: document.getElementById("sendBtn"),
  deleteModal: document.getElementById("deleteModal"),
  cancelDelete: document.getElementById("cancelDelete"),
  confirmDelete: document.getElementById("confirmDelete"),
  kbCard: document.getElementById("kbCard"),
  kbTitle: document.getElementById("kbTitle"),
  kbMeta: document.getElementById("kbMeta"),
};

const careLabels = {
  urgent: "Urgent care",
  soon: "See doctor soon",
  self_care: "Self-care guidance",
  info: "Health info",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function showToast(message) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function formatTime(iso) {
  const date = iso ? new Date(iso) : new Date();
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatInline(text) {
  return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

function formatAnswer(text) {
  const blocks = (text || "").split(/\n\n+/).filter(Boolean);
  if (!blocks.length) return "";

  return blocks
    .map((block) => {
      const lines = block.split("\n").filter((line) => line.trim());
      const bulletLines = lines.filter((line) => /^[-*]\s/.test(line.trim()));

      if (bulletLines.length === lines.length) {
        const items = bulletLines.map((line) => line.trim().replace(/^[-*]\s*/, ""));
        return `<ul>${items.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ul>`;
      }

      const html = lines
        .map((line) => {
          if (/^[-*]\s/.test(line.trim())) {
            return `<li>${formatInline(line.trim().replace(/^[-*]\s*/, ""))}</li>`;
          }
          return `<p>${formatInline(line)}</p>`;
        })
        .join("");

      return html.includes("<li>") ? html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>") : html;
    })
    .join("");
}

function autoResizeInput() {
  const input = els.questionInput;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 170)}px`;
  els.sendBtn.disabled = !input.value.trim() || state.isLoading;
}

function scrollToBottom() {
  els.chatArea.scrollTop = els.chatArea.scrollHeight;
}

function toggleWelcome(show) {
  els.welcomeScreen.style.display = show ? "block" : "none";
  els.messages.style.display = show ? "none" : "flex";
  els.clearChatBtn.disabled = show && !state.conversationId;
}

function openSidebar() {
  els.sidebar.classList.add("open");
  els.sidebarOverlay.classList.add("open");
}

function closeSidebar() {
  els.sidebar.classList.remove("open");
  els.sidebarOverlay.classList.remove("open");
}

function showDeleteModal(id) {
  state.pendingDeleteId = id;
  els.deleteModal.classList.add("show");
}

function hideDeleteModal() {
  state.pendingDeleteId = null;
  els.deleteModal.classList.remove("show");
}

async function loadKbStatus() {
  try {
    const res = await fetch("/api/kb-status");
    const data = await res.json();
    els.kbTitle.textContent = data.ready ? "Knowledge Base Ready" : "Knowledge Base Missing";
    els.kbMeta.textContent = `${data.source_count || 0} sources, ${data.chunk_count || 0} chunks`;
    els.kbCard.classList.toggle("offline", !data.ready);
  } catch {
    els.kbTitle.textContent = "Knowledge Base";
    els.kbMeta.textContent = "Status unavailable";
    els.kbCard.classList.add("offline");
  }
}

async function loadConversations() {
  try {
    const res = await fetch("/api/conversations");
    state.conversations = await res.json();
    renderChatList();
  } catch {
    els.chatList.innerHTML = `<div class="empty-state">Could not load chats</div>`;
  }
}

function renderChatList() {
  if (!state.conversations.length) {
    els.chatList.innerHTML = `<div class="empty-state">No chats yet</div>`;
    return;
  }

  els.chatList.innerHTML = state.conversations
    .map(
      (chat) => `
        <div class="chat-item ${chat.id === state.conversationId ? "active" : ""}" data-id="${chat.id}">
          <span>${escapeHtml(chat.title)}</span>
          <button type="button" data-delete="${chat.id}" title="Delete chat">x</button>
        </div>
      `
    )
    .join("");

  els.chatList.querySelectorAll(".chat-item").forEach((item) => {
    item.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      loadConversation(item.dataset.id);
      closeSidebar();
    });
  });

  els.chatList.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      showDeleteModal(button.dataset.delete);
    });
  });
}

async function loadConversation(id) {
  try {
    const res = await fetch(`/api/conversations/${id}`);
    if (!res.ok) return;
    const data = await res.json();

    state.conversationId = id;
    els.chatTitle.textContent = data.title || "MediSense AI";
    els.messages.innerHTML = "";
    toggleWelcome(false);

    data.messages.forEach((message) => {
      appendMessage(message.role, message.content, {}, false, message.created_at);
    });

    renderChatList();
    scrollToBottom();
  } catch {
    showToast("Failed to load chat");
  }
}

async function deleteConversation(id) {
  try {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    state.conversations = state.conversations.filter((chat) => chat.id !== id);

    if (state.conversationId === id) {
      state.conversationId = null;
      els.messages.innerHTML = "";
      els.chatTitle.textContent = "MediSense AI";
      toggleWelcome(true);
    }

    renderChatList();
    showToast("Chat deleted");
  } catch {
    showToast("Could not delete chat");
  }
}

function startNewChat() {
  state.conversationId = null;
  els.messages.innerHTML = "";
  els.chatTitle.textContent = "MediSense AI";
  els.questionInput.value = "";
  autoResizeInput();
  toggleWelcome(true);
  renderChatList();
  closeSidebar();
  els.questionInput.focus();
}

function avatarHtml(role) {
  if (role === "assistant") {
    return `<img src="${LOGO_URL}" alt="" class="avatar-logo" />`;
  }
  return `<span>U</span>`;
}

function appendMessage(role, content, meta = {}, animate = true, timestamp = null) {
  toggleWelcome(false);

  const message = document.createElement("div");
  message.className = `message ${role}`;
  if (!animate) message.style.animation = "none";

  const careLevel = meta.care_level || "info";
  const badge =
    role === "assistant"
      ? `<div class="care-badge ${careLevel}">${careLabels[careLevel] || "Health info"}</div>`
      : "";

  const sources =
    role === "assistant" && meta.sources && meta.sources.length
      ? `<div class="source-note">Matched: ${meta.sources.map(escapeHtml).join(", ")}</div>`
      : "";

  const actions =
    role === "assistant"
      ? `<div class="message-actions"><button class="copy-btn" type="button">Copy</button></div>`
      : "";

  message.innerHTML = `
    <div class="message-avatar">${avatarHtml(role)}</div>
    <div class="message-body">
      ${badge}
      <div class="message-bubble">${role === "assistant" ? formatAnswer(content) : `<p>${escapeHtml(content)}</p>`}</div>
      ${sources}
      ${actions}
      <div class="message-time">${formatTime(timestamp)}</div>
    </div>
  `;

  message.querySelector(".copy-btn")?.addEventListener("click", () => {
    navigator.clipboard.writeText(content).then(() => showToast("Copied"));
  });

  els.messages.appendChild(message);
  scrollToBottom();
  return message;
}

function showTypingIndicator() {
  const loader = document.createElement("div");
  loader.className = "message assistant";
  loader.id = "typingIndicator";
  loader.innerHTML = `
    <div class="message-avatar">${avatarHtml("assistant")}</div>
    <div class="message-body">
      <div class="message-bubble loading">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  els.messages.appendChild(loader);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById("typingIndicator")?.remove();
}

async function sendMessage(text) {
  const question = (text || els.questionInput.value).trim();
  if (!question || state.isLoading) return;

  state.isLoading = true;
  els.questionInput.value = "";
  autoResizeInput();

  appendMessage("user", question);
  showTypingIndicator();

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        conversation_id: state.conversationId,
      }),
    });

    const data = await res.json();
    removeTypingIndicator();

    if (data.conversation_id) {
      state.conversationId = data.conversation_id;
    }

    appendMessage("assistant", data.answer, {
      care_level: data.care_level,
      sources: data.sources,
    });

    await loadConversations();
    const active = state.conversations.find((chat) => chat.id === state.conversationId);
    if (active) els.chatTitle.textContent = active.title;
  } catch {
    removeTypingIndicator();
    appendMessage("assistant", "Sorry, I could not connect right now. Please try again.", {
      care_level: "info",
    });
  } finally {
    state.isLoading = false;
    autoResizeInput();
    els.questionInput.focus();
  }
}

els.questionInput.addEventListener("input", autoResizeInput);
els.questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

els.sendBtn.addEventListener("click", () => sendMessage());
els.newChatBtn.addEventListener("click", startNewChat);
els.chatsToggleBtn.addEventListener("click", openSidebar);
els.sidebarOverlay.addEventListener("click", closeSidebar);
els.cancelDelete.addEventListener("click", hideDeleteModal);
els.clearChatBtn.addEventListener("click", () => {
  if (state.conversationId) showDeleteModal(state.conversationId);
});
els.confirmDelete.addEventListener("click", async () => {
  const id = state.pendingDeleteId;
  hideDeleteModal();
  if (id) await deleteConversation(id);
});
els.deleteModal.addEventListener("click", (event) => {
  if (event.target === els.deleteModal) hideDeleteModal();
});

document.querySelectorAll(".suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.dataset.prompt));
});

loadKbStatus();
loadConversations();
toggleWelcome(true);
autoResizeInput();
els.questionInput.focus();
