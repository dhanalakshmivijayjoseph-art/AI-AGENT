/* script.js - HETA AI frontend. Talks to the Flask API; never sees the API key. */

// If the page is opened as a file, call the Flask server directly. Otherwise use the same address.
const API = location.protocol === "file:" ? "http://127.0.0.1:5000" : "";

const $ = (id) => document.getElementById(id);
const messagesEl = $("messages"), welcomeEl = $("welcome"), inputEl = $("input"), sendBtn = $("sendBtn");
const chatListEl = $("chatList"), titleEl = $("chatTitle"), sidebar = $("sidebar"), backdrop = $("backdrop");

let currentId = null;   // id of the open conversation (null = brand-new chat)
let busy = false;       // true while waiting for the AI

/* ---------- helpers ---------- */
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" }, ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function esc(s) {  // stop HTML in messages from running as code
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* Turn the AI's text into HTML: code blocks, `inline code`, **bold**, paragraphs */
function render(text) {
  const parts = text.split(/```/);
  return parts.map((part, i) => {
    if (i % 2 === 1) {  // inside a code fence
      const nl = part.indexOf("\n");
      const lang = nl > -1 ? part.slice(0, nl).trim() : "";
      const code = nl > -1 ? part.slice(nl + 1) : part;
      return `<div class="codebox"><div class="codebar"><span>${esc(lang || "code")}</span>` +
             `<button data-copy-code>Copy code</button></div><pre><code>${esc(code.replace(/\n$/, ""))}</code></pre></div>`;
    }
    return part.split(/\n{2,}/).filter((p) => p.trim()).map((p) =>
      "<p>" + esc(p.trim()).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>") + "</p>"
    ).join("");
  }).join("");
}

function scrollDown() { messagesEl.scrollTop = messagesEl.scrollHeight; }

function showWelcome(show) { welcomeEl.style.display = show ? "block" : "none"; }

/* ---------- drawing messages ---------- */
function addMessage(role, text, isError = false) {
  showWelcome(false);
  const row = document.createElement("div");
  row.className = `msg ${role === "user" ? "user" : "ai"}${isError ? " error" : ""}`;
  row.dataset.raw = text;
  const bubble = role === "user" ? esc(text) : render(text);
  row.innerHTML = `<div class="avatar">${role === "user" ? "You" : "H"}</div><div><div class="bubble">${bubble}</div></div>`;
  if (role !== "user" && !isError) {
    const actions = document.createElement("div");
    actions.className = "actions";
    actions.innerHTML = `<button data-copy>Copy</button><button data-regen>Regenerate</button>`;
    row.lastElementChild.appendChild(actions);
  }
  messagesEl.appendChild(row);
  scrollDown();
  return row;
}

function addTyping() {
  const row = document.createElement("div");
  row.className = "msg ai"; row.id = "typingRow";
  row.innerHTML = `<div class="avatar">H</div><div class="bubble"><div class="typing"><i></i><i></i><i></i></div></div>`;
  messagesEl.appendChild(row); scrollDown();
}
const removeTyping = () => { const t = $("typingRow"); if (t) t.remove(); };

function resetMessages() {
  messagesEl.querySelectorAll(".msg").forEach((m) => m.remove());
  showWelcome(true);
}

/* ---------- sidebar / history ---------- */
async function loadConversations() {
  try {
    const list = await api("/api/conversations");
    chatListEl.innerHTML = list.length ? "" : '<div class="empty-list">No chats yet.</div>';
    list.forEach((c) => {
      const item = document.createElement("div");
      item.className = "chat-item" + (c.id === currentId ? " active" : "");
      item.innerHTML = `<span></span><button data-rename title="Rename">Rename</button><button data-del title="Delete">Delete</button>`;
      item.querySelector("span").textContent = c.title;
      item.onclick = (e) => {
        if (e.target.dataset.rename !== undefined) return renameChat(c);
        if (e.target.dataset.del !== undefined) return deleteChat(c.id);
        openChat(c.id, c.title);
      };
      chatListEl.appendChild(item);
    });
  } catch (e) { chatListEl.innerHTML = `<div class="empty-list">Cannot reach the server. Is Flask running?</div>`; }
}

async function openChat(id, title) {
  currentId = id; titleEl.textContent = title || "HETA AI";
  resetMessages(); closeSidebar();
  try {
    const msgs = await api(`/api/history?conversation_id=${id}`);
    msgs.forEach((m) => addMessage(m.role, m.message));
  } catch (e) { addMessage("assistant", e.message, true); }
  loadConversations();
}

async function renameChat(c) {
  const t = prompt("New chat title:", c.title);
  if (!t || !t.trim()) return;
  await api(`/api/conversations/${c.id}`, { method: "PATCH", body: JSON.stringify({ title: t }) });
  if (c.id === currentId) titleEl.textContent = t;
  loadConversations();
}

async function deleteChat(id) {
  if (!confirm("Delete this chat?")) return;
  await api(`/api/conversations/${id}`, { method: "DELETE" });
  if (id === currentId) newChat();
  loadConversations();
}

function newChat() {
  currentId = null; titleEl.textContent = "HETA AI";
  resetMessages(); closeSidebar(); loadConversations(); inputEl.focus();
}

/* ---------- sending messages ---------- */
async function send(text, regenerate = false) {
  if (busy) return;
  if (!regenerate) {
    text = text.trim();
    if (!text) return;
    addMessage("user", text);
    inputEl.value = ""; autoGrow();
  }
  busy = true; sendBtn.disabled = true; addTyping();
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: currentId, message: text, regenerate }),
    });
    currentId = data.conversation_id;
    removeTyping(); addMessage("assistant", data.reply);
    loadConversations();
    if (titleEl.textContent === "HETA AI") titleEl.textContent = (await api("/api/conversations")).find((c) => c.id === currentId)?.title || "HETA AI";
  } catch (e) {
    removeTyping(); addMessage("assistant", e.message, true);
  }
  busy = false; sendBtn.disabled = false; inputEl.focus();
}

/* ---------- events ---------- */
sendBtn.onclick = () => send(inputEl.value);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(inputEl.value); }
});
function autoGrow() { inputEl.style.height = "auto"; inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px"; }
inputEl.addEventListener("input", autoGrow);

document.querySelectorAll(".card").forEach((c) => (c.onclick = () => send(c.dataset.prompt)));
$("newChatBtn").onclick = newChat;

$("clearBtn").onclick = async () => {
  if (!currentId) return resetMessages();
  if (!confirm("Clear all messages in this chat?")) return;
  await api(`/api/conversations/${currentId}/clear`, { method: "POST" });
  resetMessages();
};

// Copy and Regenerate buttons (one listener handles all messages)
messagesEl.addEventListener("click", async (e) => {
  const t = e.target;
  if (t.dataset.copy !== undefined) {
    await navigator.clipboard.writeText(t.closest(".msg").dataset.raw);
    t.textContent = "Copied!"; setTimeout(() => (t.textContent = "Copy"), 1200);
  } else if (t.dataset.copyCode !== undefined) {
    await navigator.clipboard.writeText(t.closest(".codebox").querySelector("code").textContent);
    t.textContent = "Copied!"; setTimeout(() => (t.textContent = "Copy code"), 1200);
  } else if (t.dataset.regen !== undefined) {
    // only the last AI message can be regenerated
    const all = [...messagesEl.querySelectorAll(".msg.ai")];
    const row = t.closest(".msg");
    if (row !== all[all.length - 1]) return alert("You can only regenerate the latest answer.");
    row.remove(); send("", true);
  }
});

/* ---------- theme + mobile menu ---------- */
function setTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem("heta-theme", t); } catch (e) {} }
$("themeBtn").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
try { setTheme(localStorage.getItem("heta-theme") || "dark"); } catch (e) {}

const closeSidebar = () => { sidebar.classList.remove("open"); backdrop.classList.remove("show"); };
$("menuBtn").onclick = () => { sidebar.classList.add("open"); backdrop.classList.add("show"); };
backdrop.onclick = closeSidebar;

loadConversations();
