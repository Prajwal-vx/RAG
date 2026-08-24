const $ = (id) => document.getElementById(id);
const messages = $("messages");
const documentsEl = $("documents");
const statusEl = $("status");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[c]);
}

function addMessage(role, text, sources = []) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  let html = `<div class="bubble">${escapeHtml(text)}</div>`;
  if (sources.length) {
    html += `<div class="sources">${sources.map(s => `
      <div class="source">
        <strong>${escapeHtml(s.filename)}</strong><br>
        ${escapeHtml(s.preview)}
      </div>
    `).join("")}</div>`;
  }
  message.innerHTML = html;
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
}

async function refreshDocuments() {
  const response = await fetch("/api/documents");
  const docs = await response.json();
  documentsEl.innerHTML = docs.length ? docs.map(doc => `
    <div class="doc">
      <div class="doc-row">
        <strong>${escapeHtml(doc.filename)}</strong>
        <button class="delete" data-id="${doc.document_id}">Delete</button>
      </div>
      <small>${doc.chunks} indexed chunks</small>
    </div>
  `).join("") : `<small>No documents indexed yet.</small>`;

  document.querySelectorAll(".delete").forEach(btn => {
    btn.onclick = async () => {
      await fetch(`/api/documents/${btn.dataset.id}`, { method: "DELETE" });
      refreshDocuments();
    };
  });
}

$("fileInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  $("uploadMessage").textContent = `Indexing ${file.name}...`;
  const form = new FormData();
  form.append("file", file);

  try {
    const response = await fetch("/api/documents/upload", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Upload failed");
    $("uploadMessage").textContent = `${data.filename} indexed: ${data.chunks} chunks`;
    await refreshDocuments();
  } catch (error) {
    $("uploadMessage").textContent = `Error: ${error.message}`;
  } finally {
    event.target.value = "";
  }
});

$("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;

  addMessage("user", question);
  $("question").value = "";
  $("sendButton").disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({question})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    addMessage("assistant", data.answer, data.sources);
  } catch (error) {
    addMessage("assistant", `Error: ${error.message}`);
  } finally {
    $("sendButton").disabled = false;
  }
});

(async () => {
  try {
    const data = await (await fetch("/api/health")).json();
    statusEl.textContent = `System online • ${data.provider}`;
  } catch {
    statusEl.textContent = "System offline";
  }
  refreshDocuments();
})();
