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
      const row = document.createElement("div");
      row.className = "conversation-row";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "conversation" + (conversation.id === currentConversation ? " active" : "");
      button.textContent = conversation.title;
      button.title = conversation.title;
      button.addEventListener("click", () => openConversation(conversation.id));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "conversation-delete";
      remove.textContent = "×";
      remove.title = "Usuń rozmowę";
      remove.setAttribute("aria-label", "Usuń rozmowę: " + conversation.title);
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        if (!window.confirm("Usunąć tę rozmowę wraz z całą historią?")) return;
        remove.disabled = true;
        try {
          await api("/api/conversations/" + encodeURIComponent(conversation.id), {method: "DELETE"});
          if (currentConversation === conversation.id) await newChat();
          else await refreshConversations();
        } catch (error) {
          remove.disabled = false;
          alert("Nie udało się usunąć rozmowy: " + error.message);
        }
      });
      row.append(button, remove);
      $("conversationList").append(row);
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

async function refreshTasks() {
  const list = $("taskList");
  if (!list) return;
  try {
    const data = await api("/api/tasks?limit=100");
    list.replaceChildren();
    if (!data.tasks.length) {
      list.textContent = "Brak zapisanych zadań.";
      return;
    }
    data.tasks.forEach((task) => {
      const row = document.createElement("div");
      row.className = "task-item";
      const details = document.createElement("div");
      details.className = "task-details";
      const title = document.createElement("strong");
      title.textContent = task.title;
      const status = document.createElement("small");
      status.textContent = task.status;
      const description = document.createElement("p");
      description.textContent = task.description;
      details.append(title, status, description);
      row.append(details);
      if (task.status === "pending") {
        const run = document.createElement("button");
        run.type = "button";
        run.textContent = "Uruchom";
        run.addEventListener("click", async () => {
          run.disabled = true;
          run.textContent = "Pracuje…";
          try {
            await api("/api/tasks/" + encodeURIComponent(task.id) + "/execute", {method: "POST"});
          } catch (error) {
            alert("Nie udało się wykonać zadania: " + error.message);
          } finally {
            await refreshTasks();
          }
        });
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "task-cancel";
        cancel.textContent = "Anuluj";
        cancel.addEventListener("click", async () => {
          try {
            await api("/api/tasks/" + encodeURIComponent(task.id) + "/cancel", {method: "POST"});
            await refreshTasks();
          } catch (error) { alert(error.message); }
        });
        row.append(run, cancel);
      } else if (task.result || task.error) {
        const output = document.createElement("p");
        output.className = "task-output";
        output.textContent = task.error || task.result;
        details.append(output);
      }
      list.append(row);
    });
  } catch (error) {
    list.textContent = "Nie można pobrać zadań: " + error.message;
  }
}

$("taskForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("taskInput");
  const description = input.value.trim();
  if (!description) return;
  const submit = event.submitter;
  if (submit) submit.disabled = true;
  try {
    await api("/api/tasks", {method: "POST", body: JSON.stringify({description})});
    input.value = "";
    await refreshTasks();
  } catch (error) {
    alert("Nie udało się zapisać zadania: " + error.message);
  } finally {
    if (submit) submit.disabled = false;
  }
});

async function diagnostics() {
  const [health, modelData, capabilityData] = await Promise.allSettled([api("/api/health"), api("/api/models"), api("/api/capabilities")]);
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
  if (capabilityData.status === "fulfilled") {
    rows.push(["Narzędzia", capabilityData.value.tools.join(", ")]);
    rows.push(["Pamięć", capabilityData.value.memory.retrieval]);
    rows.push(["Sandbox", capabilityData.value.sandbox.os_isolation ? "izolacja OS" : "brak izolacji OS"]);
    rows.push(["Zdalny dostęp", capabilityData.value.remote_access ? "włączony" : "wyłączony"]);
  } else rows.push(["Funkcje", "nie można pobrać listy"]);
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
$("settingsButton").addEventListener("click", () => { $("settingsDialog").showModal(); diagnostics(); refreshMemory(); refreshTasks(); });
$("closeSettings").addEventListener("click", () => $("settingsDialog").close());
document.querySelectorAll(".suggestion").forEach(button => button.addEventListener("click", () => {
  $("promptInput").value = button.dataset.prompt;
  $("promptInput").focus();
}));
refreshConversations();
diagnostics();
