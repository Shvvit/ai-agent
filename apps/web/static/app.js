const $ = (id) => document.getElementById(id);
let currentConversation = null;
let busy = false;

function addMessage(role, content, extra = {}) {
  $("welcome").hidden = true;
  const item = document.createElement("article");
  item.className = "message " + role;
  const icon = document.createElement("div");
  icon.className = "role-icon";
  icon.textContent = role === "user" ? "P" : "✳";
  const body = document.createElement("div");
  body.className = "message-body";
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "Ty" : "Własne AI";
  const text = document.createElement("div");
  text.className = "message-content";
  text.textContent = content;
  body.append(label, text);
  item.append(icon, body);
  $("messages").append(item);
  $("chatArea").scrollTop = $("chatArea").scrollHeight;
  return text;
}

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || ("HTTP " + response.status));
  return data;
}

async function refreshConversations() {
  try {
    const data = await api("/api/conversations");
    $("conversationList").replaceChildren();
    data.conversations.forEach((conversation) => {
      const button = document.createElement("button");
      button.className = "conversation" + (conversation.id === currentConversation ? " active" : "");
      button.textContent = conversation.title;
      button.title = conversation.title;
      button.addEventListener("click", () => openConversation(conversation.id));
      $("conversationList").append(button);
    });
  } catch (error) { console.error(error); }
}

async function openConversation(id) {
  try {
    const data = await api("/api/conversations/" + encodeURIComponent(id) + "/messages");
    currentConversation = id;
    $("messages").replaceChildren();
    $("welcome").hidden = data.messages.length > 0;
    data.messages.forEach((message) => addMessage(message.role, message.content));
    $("currentTitle").textContent = "Rozmowa";
    await refreshConversations();
  } catch (error) { alert(error.message); }
}

async function newChat() {
  currentConversation = null;
  $("messages").replaceChildren();
  $("welcome").hidden = false;
  $("currentTitle").textContent = "Nowa rozmowa";
  await refreshConversations();
  $("promptInput").focus();
}

async function sendMessage(message) {
  if (busy || !message.trim()) return;
  busy = true;
  $("sendButton").disabled = true;
  addMessage("user", message);
  const placeholder = addMessage("assistant", "Łączę się z modelem…");
  placeholder.classList.add("typing");
  try {
    const data = await api("/api/chat", {method: "POST", body: JSON.stringify({
      message, conversation_id: currentConversation, model: $("modelSelect").value || null
    })});
    currentConversation = data.conversation_id;
    placeholder.classList.remove("typing");
    placeholder.textContent = data.answer;
    $("modelChip").textContent = data.model;
    $("currentTitle").textContent = "Rozmowa";
    await refreshConversations();
  } catch (error) {
    placeholder.classList.remove("typing");
    placeholder.textContent = "Nie udało się wykonać żądania: " + error.message;
  } finally {
    busy = false;
    $("sendButton").disabled = false;
    $("promptInput").focus();
    $("chatArea").scrollTop = $("chatArea").scrollHeight;
  }
}

async function refreshMemory() {
  const list = $("memoryList");
  if (!list) return;
  try {
    const data = await api("/api/memory");
    list.replaceChildren();
    if (!data.memories.length) {
      list.textContent = "Brak zapisanych informacji.";
      return;
    }
    data.memories.forEach((memory) => {
      const row = document.createElement("div");
      row.className = "memory-item";
      const content = document.createElement("span");
      content.textContent = memory.content;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Usuń";
      remove.setAttribute("aria-label", "Usuń zapamiętaną informację");
      remove.addEventListener("click", async () => {
        try {
          await api("/api/memory/" + memory.id, {method: "DELETE"});
          await refreshMemory();
        } catch (error) { alert(error.message); }
      });
      row.append(content, remove);
      list.append(row);
    });
  } catch (error) {
    list.textContent = "Nie można pobrać pamięci: " + error.message;
  }
}

$("clearMemory").addEventListener("click", async () => {
  if (!window.confirm("Usunąć wszystkie zapisane informacje?")) return;
  try {
    await api("/api/memory", {method: "DELETE"});
    await refreshMemory();
  } catch (error) { alert(error.message); }
});

$("memoryForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("memoryInput");
  const content = input.value.trim();
  if (!content) return;
  try {
    await api("/api/memory", {method: "POST", body: JSON.stringify({content})});
    input.value = "";
    await refreshMemory();
  } catch (error) { alert(error.message); }
});

async function diagnostics() {
  const [health, modelData] = await Promise.allSettled([api("/api/health"), api("/api/models")]);
  const online = health.status === "fulfilled" && health.value.ollama === "online";
  $("statusDot").className = "status-dot " + (online ? "online" : "offline");
  $("statusText").textContent = online ? "Ollama połączona" : "Ollama niedostępna";
  const rows = [];
  if (health.status === "fulfilled") {
    rows.push(["API", health.value.status]);
    rows.push(["Ollama", health.value.ollama]);
    rows.push(["Domyślny model", health.value.model]);
    rows.push(["Workspace", health.value.workspace]);
  } else rows.push(["API", "brak odpowiedzi"]);
  if (modelData.status === "fulfilled") {
    const models = modelData.value.models;
    $("modelSelect").replaceChildren(new Option("Domyślny model", ""));
    models.forEach((model) => $("modelSelect").add(new Option(model.name, model.name)));
    rows.push(["Dostępne modele", models.map(m => m.name).join(", ") || "brak"]);
  } else rows.push(["Modele", "nie można pobrać listy"]);
  const diagnostics = $("diagnostics");
  diagnostics.replaceChildren();
  rows.forEach(([label, value]) => {
    const line = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = label + ": ";
    line.append(strong, document.createTextNode(String(value)));
    diagnostics.append(line);
  });
  $("modelChip").textContent = health.status === "fulfilled" ? health.value.model : "Ollama";
}

$("chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = $("promptInput");
  const value = input.value.trim();
  if (!value) return;
  input.value = "";
  input.style.height = "auto";
  sendMessage(value);
});
$("promptInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("chatForm").requestSubmit();
  }
});
$("promptInput").addEventListener("input", (event) => {
  event.target.style.height = "auto";
  event.target.style.height = Math.min(event.target.scrollHeight, 180) + "px";
});
$("newChat").addEventListener("click", newChat);
$("menuButton").addEventListener("click", () => $("sidebar").classList.toggle("open"));
$("settingsButton").addEventListener("click", () => { $("settingsDialog").showModal(); diagnostics(); refreshMemory(); });
$("closeSettings").addEventListener("click", () => $("settingsDialog").close());
document.querySelectorAll(".suggestion").forEach(button => button.addEventListener("click", () => {
  $("promptInput").value = button.dataset.prompt;
  $("promptInput").focus();
}));
refreshConversations();
diagnostics();
