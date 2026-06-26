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
  suggestions: document.getElementById("suggestions"),
  deleteModal: document.getElementById("deleteModal"),
  cancelDelete: document.getElementById("cancelDelete"),
  confirmDelete: document.getElementById("confirmDelete"),
};

const DELETE_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>`;

function showToast(msg) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function formatTime(iso) {
  const d = iso ? new Date(iso) : new Date();
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function applyInlineFormatting(text) {
  return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

function formatAnswer(text) {
  const blocks = text.split(/\n\n+/);
  const htmlParts = [];

  for (const block of blocks) {
    const lines = block.split("\n").filter((l) => l.trim());
    if (!lines.length) continue;

    const bulletLines = lines.filter((l) => /^[-•*]\s/.test(l.trim()));
    const textLines = lines.filter((l) => !/^[-•*]\s/.test(l.trim()));

    if (bulletLines.length && bulletLines.length === lines.length) {
      const items = bulletLines.map((l) => l.trim().replace(/^[-•*]\s*/, ""));
      htmlParts.push(
        `<ul class="answer-list">${items.map((i) => `<li>${applyInlineFormatting(i)}</li>`).join("")}</ul>`
      );
    } else if (bulletLines.length) {
      if (textLines.length) {
        htmlParts.push(`<p class="answer-p">${applyInlineFormatting(textLines.join(" "))}</p>`);
      }
      const items = bulletLines.map((l) => l.trim().replace(/^[-•*]\s*/, ""));
      htmlParts.push(
        `<ul class="answer-list">${items.map((i) => `<li>${applyInlineFormatting(i)}</li>`).join("")}</ul>`
      );
    } else {
      htmlParts.push(`<p class="answer-p">${applyInlineFormatting(lines.join(" "))}</p>`);
    }
  }

  if (!htmlParts.length) {
    return `<div class="formatted-answer"><p class="answer-p">${applyInlineFormatting(text).replace(/\n/g, "<br>")}</p></div>`;
  }

  return `<div class="formatted-answer">${htmlParts.join("")}</div>`;
}

function autoResizeInput() {
  const el = els.questionInput;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 180) + "px";
  els.sendBtn.disabled = !el.value.trim() || state.isLoading;
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

async function loadConversations() {
  try {
    const res = await fetch("/api/conversations");
    state.conversations = await res.json();
    renderChatList();
  } catch {
    els.chatList.innerHTML = `<div class="empty-chats">Could not load chats</div>`;
  }
}

function renderChatList() {
  if (!state.conversations.length) {
    els.chatList.innerHTML = `<div class="empty-chats">No chats yet — start a new one!</div>`;
    return;
  }

  els.chatList.innerHTML = state.conversations
    .map(
      (c) => `
    <div class="chat-item ${c.id === state.conversationId ? "active" : ""}" data-id="${c.id}">
      <span class="chat-item-text">${escapeHtml(c.title)}</span>
      <button class="chat-item-delete" data-delete="${c.id}" title="Delete chat">
        ${DELETE_ICON} Delete
      </button>
    </div>`
    )
    .join("");

  els.chatList.querySelectorAll(".chat-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      if (e.target.closest(".chat-item-delete")) return;
      loadConversation(item.dataset.id);
      closeSidebar();
    });
  });

  els.chatList.querySelectorAll(".chat-item-delete").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      showDeleteModal(btn.dataset.delete);
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
    els.clearChatBtn.disabled = false;

    els.messages.innerHTML = "";
    toggleWelcome(false);

    data.messages.forEach((msg) => appendMessage(msg.role, msg.content, false, msg.created_at));
    renderChatList();
    scrollToBottom();
  } catch {
    showToast("Failed to load chat");
  }
}

async function deleteConversation(id) {
  try {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    state.conversations = state.conversations.filter((c) => c.id !== id);

    if (state.conversationId === id) {
      state.conversationId = null;
      els.messages.innerHTML = "";
      els.chatTitle.textContent = "MediSense AI";
      toggleWelcome(true);
    }

    renderChatList();
    showToast("Chat deleted successfully");
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

function botAvatarHtml() {
  return `<img src="${LOGO_URL}" alt="MediSense" class="avatar-logo" />`;
}

function appendMessage(role, content, animate = true, timestamp = null) {
  toggleWelcome(false);

  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (!animate) div.style.animation = "none";

  const avatar = role === "user" ? "👤" : botAvatarHtml();
  const formatted =
    role === "assistant"
      ? formatAnswer(content)
      : `<div class="formatted-answer"><p class="answer-p">${escapeHtml(content).replace(/\n/g, "<br>")}</p></div>`;

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      <div class="message-bubble">${formatted}</div>
      <div class="message-actions">
        <button class="msg-action-btn copy-btn">📋 Copy Response</button>
      </div>
      <div class="message-time">${formatTime(timestamp)}</div>
    </div>`;

  if (role === "user") {
    div.querySelector(".message-actions").remove();
  }

  div.querySelector(".copy-btn")?.addEventListener("click", () => {
    navigator.clipboard.writeText(content).then(() => showToast("Copied to clipboard!"));
  });

  els.messages.appendChild(div);
  scrollToBottom();
  return div;
}

function showTypingIndicator() {
  const div = document.createElement("div");
  div.className = "message assistant";
  div.id = "typingIndicator";
  div.innerHTML = `
    <div class="message-avatar">${botAvatarHtml()}</div>
    <div class="message-body">
      <div class="message-bubble">
        <div class="typing-row">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <span style="color:var(--text-muted);font-size:1rem;">Thinking...</span>
        </div>
      </div>
    </div>`;
  els.messages.appendChild(div);
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
  els.sendBtn.disabled = true;

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
      els.clearChatBtn.disabled = false;
    }

    appendMessage("assistant", data.answer);
    await loadConversations();

    if (state.conversationId) {
      const conv = state.conversations.find((c) => c.id === state.conversationId);
      if (conv) els.chatTitle.textContent = conv.title;
    }
  } catch {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "Sorry, I couldn't connect right now. Please check your internet and try again."
    );
  } finally {
    state.isLoading = false;
    autoResizeInput();
    els.questionInput.focus();
  }
}

els.questionInput.addEventListener("input", autoResizeInput);

els.questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

els.sendBtn.addEventListener("click", () => sendMessage());
els.newChatBtn.addEventListener("click", startNewChat);

els.clearChatBtn.addEventListener("click", () => {
  if (state.conversationId) {
    showDeleteModal(state.conversationId);
  } else {
    startNewChat();
  }
});

els.chatsToggleBtn.addEventListener("click", openSidebar);
els.sidebarOverlay.addEventListener("click", closeSidebar);

els.cancelDelete.addEventListener("click", hideDeleteModal);

els.confirmDelete.addEventListener("click", async () => {
  const id = state.pendingDeleteId;
  hideDeleteModal();
  if (id) await deleteConversation(id);
});

els.deleteModal.addEventListener("click", (e) => {
  if (e.target === els.deleteModal) hideDeleteModal();
});

els.suggestions.querySelectorAll(".suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.dataset.prompt));
});

loadConversations();
toggleWelcome(true);
els.questionInput.focus();
