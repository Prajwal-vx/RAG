const $ = (id) => document.getElementById(id);
const messages = $("messages");
const documentsEl = $("documents");
const statusEl = $("status");
const fileInput = $("fileInput");
const uploadMessage = $("uploadMessage");
const chatForm = $("chatForm");
const questionInput = $("question");
const sendButton = $("sendButton");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[c]);
}

function addMessage(role, text, sources = []) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  message.appendChild(bubble);

  if (Array.isArray(sources) && sources.length > 0) {
    const sourcesContainer = document.createElement("div");
    sourcesContainer.className = "sources";
    
    sources.forEach(s => {
      const sourceEl = document.createElement("div");
      sourceEl.className = "source";
      
      const title = document.createElement("strong");
      title.textContent = s.filename || "Untitled";
      
      const preview = document.createElement("div");
      preview.textContent = s.preview || "";
      
      sourceEl.appendChild(title);
      sourceEl.appendChild(document.createElement("br"));
      sourceEl.appendChild(preview);
      sourcesContainer.appendChild(sourceEl);
    });
    
    message.appendChild(sourcesContainer);
  }

  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
}

async function refreshDocuments() {
  try {
    const response = await fetch("/api/documents");
    if (!response.ok) throw new Error("Failed to fetch documents");
    const docs = await response.json();
    
    documentsEl.innerHTML = "";
    if (!docs.length) {
      documentsEl.innerHTML = `<small>No documents indexed yet.</small>`;
      return;
    }

    docs.forEach(doc => {
      const docEl = document.createElement("div");
      docEl.className = "doc";

      const row = document.createElement("div");
      row.className = "doc-row";

      const title = document.createElement("strong");
      title.textContent = doc.filename;

      const delBtn = document.createElement("button");
      delBtn.className = "delete";
      delBtn.textContent = "Delete";
      delBtn.dataset.id = doc.document_id;

      row.appendChild(title);
      row.appendChild(delBtn);

      const info = document.createElement("small");
      info.textContent = `${doc.chunks} indexed chunks`;

      docEl.appendChild(row);
      docEl.appendChild(info);
      documentsEl.appendChild(docEl);
    });
  } catch (error) {
    documentsEl.innerHTML = `<small class="error">Error loading documents.</small>`;
  }
}

// Event Delegation for Delete Actions
documentsEl.addEventListener("click", async (event) => {
  const btn = event.target.closest(".delete");
  if (!btn || !btn.dataset.id) return;

  btn.disabled = true;
  try {
    const response = await fetch(`/api/documents/${encodeURIComponent(btn.dataset.id)}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed");
    await refreshDocuments();
  } catch (error) {
    alert(`Could not delete document: ${error.message}`);
    btn.disabled = false;
  }
});

fileInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  uploadMessage.textContent = `Indexing ${file.name}...`;
  fileInput.disabled = true;

  const form = new FormData();
  form.append("file", file);

  try {
    const response = await fetch("/api/documents/upload", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Upload failed");
    uploadMessage.textContent = `${data.filename} indexed: ${data.chunks} chunks`;
    await refreshDocuments();
  } catch (error) {
    uploadMessage.textContent = `Error: ${error.message}`;
  } finally {
    fileInput.disabled = false;
    event.target.value = "";
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";
  sendButton.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    addMessage("assistant", data.answer, data.sources);
  } catch (error) {
    addMessage("assistant", `Error: ${error.message}`);
  } finally {
    sendButton.disabled = false;
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