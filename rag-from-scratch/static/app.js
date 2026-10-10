// VerityRAG Client Architecture
const $ = (id) => document.getElementById(id);

let currentMode = "quick";
let lastChatResponse = null;
let lastQuestion = "";

// Elements
const chatHistory = $("chatHistory");
const docListContainer = $("docListContainer");
const docCountBadge = $("docCountBadge");
const uploadStatusMsg = $("uploadStatusMsg");
const fileUploadInput = $("fileUploadInput");
const chatInputForm = $("chatInputForm");
const questionInput = $("questionInput");
const submitQuestionBtn = $("submitQuestionBtn");
const claimsLedgerList = $("claimsLedgerList");
const sourcePassagesList = $("sourcePassagesList");
const conflictAlertBox = $("conflictAlertBox");
const conflictAlertText = $("conflictAlertText");
const conflictDuoContainer = $("conflictDuoContainer");
const gapAlertBox = $("gapAlertBox");
const gapSummary = $("gapSummary");
const diagnosticsDetails = $("diagnosticsDetails");
const studioDocCheckboxes = $("studioDocCheckboxes");
const studioQueryInput = $("studioQueryInput");
const runStudioCompareBtn = $("runStudioCompareBtn");
const studioResultsArea = $("studioResultsArea");
const studioMatrixContainer = $("studioMatrixContainer");
const studioSynthesisText = $("studioSynthesisText");
const runEnhancedBenchmarkBtn = $("runEnhancedBenchmarkBtn");
const runBaselineBenchmarkBtn = $("runBaselineBenchmarkBtn");
const evalHistoryTbody = $("evalHistoryTbody");
const saveSessionBtn = $("saveSessionBtn");
const savedSessionsList = $("savedSessionsList");
const toggleLedgerBtn = $("toggleLedgerBtn");
const closeLedgerMobileBtn = $("closeLedgerMobileBtn");
const inspectionPanel = $("inspectionPanel");

// View Switching
document.querySelectorAll(".nav-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view-container").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    const target = $(btn.dataset.view);
    if (target) {
      target.classList.add("active");
    }

    if (btn.dataset.view === "observatory-view") {
      fetchEvalHistory();
    } else if (btn.dataset.view === "history-view") {
      fetchSavedSessions();
    }
  });
});

// Mode Switching
document.querySelectorAll(".mode-pill").forEach(pill => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".mode-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    currentMode = pill.dataset.mode;
  });
});

// Mobile / Responsive Panel Toggle
if (toggleLedgerBtn && inspectionPanel) {
  toggleLedgerBtn.addEventListener("click", () => {
    inspectionPanel.classList.toggle("open");
  });
}
if (closeLedgerMobileBtn && inspectionPanel) {
  closeLedgerMobileBtn.addEventListener("click", () => {
    inspectionPanel.classList.remove("open");
  });
}

// Markdown formatter with Table, Bold, and Newlines
function formatMarkdown(content) {
  if (!content) return "";
  let clean = content
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headers
  clean = clean.replace(/^### (.*$)/gim, '<h3 style="color:var(--accent-gold); font-size:14px; margin:10px 0 6px;">$1</h3>');
  clean = clean.replace(/^## (.*$)/gim, '<h2 style="color:var(--text-primary); font-size:16px; margin:12px 0 8px;">$1</h2>');
  clean = clean.replace(/^# (.*$)/gim, '<h1 style="color:var(--text-primary); font-size:18px; margin:14px 0 10px;">$1</h1>');

  // Bold
  clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Markdown tables
  const lines = clean.split("\n");
  let inTable = false;
  let tableHtml = "";
  let resultLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith("|") && line.endsWith("|")) {
      if (line.includes("---")) continue; // separator row
      const cells = line.slice(1, -1).split("|").map(c => c.trim());
      if (!inTable) {
        inTable = true;
        tableHtml = '<table><thead><tr>' + cells.map(c => `<th>${c}</th>`).join("") + '</tr></thead><tbody>';
      } else {
        tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join("") + '</tr>';
      }
    } else {
      if (inTable) {
        tableHtml += '</tbody></table>';
        resultLines.push(tableHtml);
        inTable = false;
        tableHtml = "";
      }
      resultLines.push(line);
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table>';
    resultLines.push(tableHtml);
  }

  return resultLines.join("<br>");
}

// Add message to chat bubble
function appendChatMessage(role, title, content) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;

  const header = document.createElement("div");
  header.className = "bubble-header";
  header.textContent = title;

  const body = document.createElement("div");
  body.className = "bubble-body";
  body.innerHTML = formatMarkdown(content);

  bubble.appendChild(header);
  bubble.appendChild(body);
  chatHistory.appendChild(bubble);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Render Evidence Ledger & Conflict Radar
function renderEvidenceLedger(data) {
  claimsLedgerList.innerHTML = "";
  if (sourcePassagesList) sourcePassagesList.innerHTML = "";

  // 1. Conflict Radar
  if (data.conflict_detected && data.conflicts && data.conflicts.length > 0) {
    conflictAlertBox.style.display = "flex";
    const c = data.conflicts[0];
    conflictAlertText.textContent = `${c.topic}: ${c.analysis}`;
    conflictDuoContainer.innerHTML = `
      <div class="conflict-pane">
        <div class="conflict-doc-title">${c.doc_a_filename} (P.${c.doc_a_page})</div>
        <div style="font-size: 10px; color: var(--text-secondary); font-style: italic;">"${c.doc_a_excerpt}"</div>
      </div>
      <div class="conflict-pane">
        <div class="conflict-doc-title">${c.doc_b_filename} (P.${c.doc_b_page})</div>
        <div style="font-size: 10px; color: var(--text-secondary); font-style: italic;">"${c.doc_b_excerpt}"</div>
      </div>
    `;
  } else {
    conflictAlertBox.style.display = "none";
  }

  // 2. Knowledge Gap
  if (data.knowledge_gap && data.knowledge_gap.missing_information && data.knowledge_gap.missing_information.length > 0) {
    const gaps = data.knowledge_gap.missing_information.join(" ");
    gapAlertBox.style.display = "block";
    gapSummary.textContent = gaps;
  } else {
    gapAlertBox.style.display = "none";
  }

  // 3. Diagnostics
  if (data.diagnostics) {
    diagnosticsDetails.innerHTML = `
      <div>Method: <span style="color: var(--accent-gold);">${data.diagnostics.method}</span></div>
      <div>Semantic Hits: <span>${data.diagnostics.semantic_hits}</span> | Lexical: <span>${data.diagnostics.lexical_hits}</span></div>
      <div>Latency: <span style="color: var(--accent-emerald);">${data.diagnostics.latency_ms} ms</span></div>
      <div>Deduplicated Chunks: <span>${data.diagnostics.deduped_count}</span></div>
    `;
  }

  // 4. Source Passages
  if (sourcePassagesList && data.sources && data.sources.length > 0) {
    data.sources.forEach((s, idx) => {
      const pCard = document.createElement("div");
      pCard.className = "passage-card";
      pCard.innerHTML = `
        <div class="passage-meta">
          <span>[${idx + 1}] ${s.filename} (P.${s.page})</span>
          <span>Chunk ${s.chunk_id}</span>
        </div>
        <div style="color: var(--text-secondary); line-height: 1.4;">
          "${s.preview}"
        </div>
      `;
      sourcePassagesList.appendChild(pCard);
    });
  } else if (sourcePassagesList) {
    sourcePassagesList.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 8px;">No source chunks returned.</div>`;
  }

  // 5. Claims Ledger Items
  if (data.evidence_ledger && data.evidence_ledger.length > 0) {
    data.evidence_ledger.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "ledger-card";

      const badgeClass = item.status === "verified" ? "badge-verified" : (item.status === "partial" ? "badge-partial" : "badge-unsupported");
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
          <div class="ledger-claim">Claim ${idx + 1}: ${item.claim}</div>
          <span class="badge ${badgeClass}">${item.directness}</span>
        </div>
        <div class="ledger-source">
          <span>Source: ${item.source_filename} (P.${item.source_page})</span>
        </div>
        <div class="ledger-evidence">
          "${item.evidence}"
        </div>
      `;
      claimsLedgerList.appendChild(card);
    });
  } else {
    claimsLedgerList.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px;">No individual claims extracted.</div>`;
  }
}

// Document Management
async function refreshDocuments() {
  try {
    const res = await fetch("/api/documents");
    if (!res.ok) throw new Error("Could not fetch documents");
    const docs = await res.json();

    docListContainer.innerHTML = "";
    studioDocCheckboxes.innerHTML = "";
    docCountBadge.textContent = `${docs.length} Files`;

    if (docs.length === 0) {
      docListContainer.innerHTML = `<div style="font-size: 12px; color: var(--text-muted); text-align: center; padding: 12px;">No documents indexed yet.</div>`;
      studioDocCheckboxes.innerHTML = `<span style="color: var(--text-muted);">Upload at least two documents first.</span>`;
      return;
    }

    docs.forEach(doc => {
      const item = document.createElement("div");
      item.className = "doc-item";
      item.innerHTML = `
        <div class="doc-info">
          <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
          <span class="doc-meta">${doc.chunks} chunks • ${doc.file_hash ? doc.file_hash.substring(0, 8) : 'sha'}</span>
        </div>
        <button class="btn-icon-danger" data-id="${doc.document_id}" title="Delete Document">✕</button>
      `;
      docListContainer.appendChild(item);

      // Checkbox for Studio
      const label = document.createElement("label");
      label.style.display = "flex";
      label.style.alignItems = "center";
      label.style.gap = "6px";
      label.style.cursor = "pointer";
      label.innerHTML = `
        <input type="checkbox" value="${doc.document_id}" class="studio-doc-cb" checked />
        <span>${doc.filename}</span>
      `;
      studioDocCheckboxes.appendChild(label);
    });
  } catch (err) {
    docListContainer.innerHTML = `<div style="font-size: 12px; color: var(--accent-rose); text-align: center; padding: 12px;">Failed to load documents.</div>`;
  }
}

// Upload Listener
fileUploadInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  uploadStatusMsg.textContent = `Indexing ${file.name}...`;
  fileUploadInput.disabled = true;

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch("/api/documents/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload error");

    if (data.is_duplicate) {
      uploadStatusMsg.textContent = `File already indexed (${data.chunks} chunks).`;
    } else {
      uploadStatusMsg.textContent = `Indexed: ${data.filename} (${data.chunks} chunks)`;
    }
    await refreshDocuments();
  } catch (err) {
    uploadStatusMsg.textContent = `Error: ${err.message}`;
  } finally {
    fileUploadInput.disabled = false;
    e.target.value = "";
  }
});

// Delete listener
docListContainer.addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn-icon-danger");
  if (!btn || !btn.dataset.id) return;

  btn.disabled = true;
  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(btn.dataset.id)}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    await refreshDocuments();
  } catch (err) {
    alert(`Could not delete document: ${err.message}`);
    btn.disabled = false;
  }
});

// Enter key submit handling for textarea
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatInputForm.dispatchEvent(new Event("submit", { cancelable: true }));
  }
});

// Chat submit
chatInputForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if (!q) return;

  lastQuestion = q;
  appendChatMessage("user", "RESEARCH QUERY", q);
  questionInput.value = "";
  submitQuestionBtn.disabled = true;

  // Add placeholder
  const placeholder = document.createElement("div");
  placeholder.className = "chat-bubble assistant";
  placeholder.id = "activeSearchPlaceholder";
  placeholder.innerHTML = `
    <div class="bubble-header">RETRIEVING CONTEXT</div>
    <div class="bubble-body" style="color: var(--text-muted); font-style: italic;">
      Searching hybrid BM25 + dense vectors, running reciprocal rank fusion, and validating citations...
    </div>
  `;
  chatHistory.appendChild(placeholder);
  chatHistory.scrollTop = chatHistory.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: q,
        mode: currentMode,
        use_hybrid: true,
        use_rerank: true,
      })
    });
    const data = await res.json();
    placeholder.remove();

    if (!res.ok) throw new Error(data.detail || "Chat request failed");
    lastChatResponse = data;

    appendChatMessage("assistant", `VERITYRAG • ${currentMode.toUpperCase()}`, data.answer);
    renderEvidenceLedger(data);
  } catch (err) {
    placeholder.remove();
    appendChatMessage("assistant", "ERROR", `Error: ${err.message}`);
  } finally {
    submitQuestionBtn.disabled = false;
    questionInput.focus();
  }
});

// Save Session
saveSessionBtn.addEventListener("click", async () => {
  if (!lastChatResponse || !lastQuestion) {
    alert("Please perform a search query before saving a dossier.");
    return;
  }

  try {
    const res = await fetch("/api/research/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: lastQuestion.substring(0, 50),
        mode: currentMode,
        question: lastQuestion,
        answer: lastChatResponse.answer,
        evidence_ledger: lastChatResponse.evidence_ledger,
        sources: lastChatResponse.sources,
      })
    });
    if (!res.ok) throw new Error("Failed to save dossier");
    alert("Research Dossier saved successfully!");
  } catch (err) {
    alert(`Could not save dossier: ${err.message}`);
  }
});

// Fetch Saved Sessions
async function fetchSavedSessions() {
  try {
    const res = await fetch("/api/research/saved");
    const sessions = await res.json();
    savedSessionsList.innerHTML = "";

    if (!sessions.length) {
      savedSessionsList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">No saved dossiers found.</div>`;
      return;
    }

    sessions.forEach(s => {
      const item = document.createElement("div");
      item.style.background = "var(--bg-surface)";
      item.style.border = "1px solid var(--border-subtle)";
      item.style.borderRadius = "8px";
      item.style.padding = "16px";
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <strong style="color: var(--accent-gold); font-size: 13px;">${s.title}</strong>
          <span style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">${s.created_at ? s.created_at.substring(0, 10) : ''}</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;"><strong>Query:</strong> ${s.question}</div>
        <div style="font-size: 12px; color: var(--text-primary); line-height: 1.5; background: var(--bg-surface-elevated); padding: 10px; border-radius: 4px;">
          ${formatMarkdown(s.answer)}
        </div>
      `;
      savedSessionsList.appendChild(item);
    });
  } catch (err) {
    savedSessionsList.innerHTML = `<div style="color: var(--accent-rose);">Failed to load dossiers.</div>`;
  }
}

// Studio Compare
runStudioCompareBtn.addEventListener("click", async () => {
  const selectedCbs = Array.from(document.querySelectorAll(".studio-doc-cb:checked"));
  const docIds = selectedCbs.map(cb => cb.value);

  if (docIds.length < 2) {
    alert("Please select at least two documents for comparison.");
    return;
  }

  runStudioCompareBtn.disabled = true;
  runStudioCompareBtn.textContent = "Analyzing Cross-Document Matrix...";

  try {
    const res = await fetch("/api/research/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doc_ids: docIds,
        query: studioQueryInput.value.trim() || undefined,
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Compare failed");

    studioResultsArea.style.display = "flex";
    
    // Matrix table
    let tableHtml = `
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <thead>
          <tr style="text-align: left; border-bottom: 1px solid var(--border-subtle); color: var(--text-muted);">
            <th style="padding: 8px;">Document</th>
            <th style="padding: 8px;">Chunks</th>
            <th style="padding: 8px;">Key Verified Finding</th>
          </tr>
        </thead>
        <tbody>
    `;
    data.matrix_rows.forEach(r => {
      tableHtml += `
        <tr style="border-bottom: 1px solid var(--border-subtle);">
          <td style="padding: 8px; font-weight: 600; color: var(--accent-gold);">${r.filename}</td>
          <td style="padding: 8px; font-family: var(--font-mono);">${r.chunks_count}</td>
          <td style="padding: 8px; color: var(--text-secondary);">"${r.key_finding}"</td>
        </tr>
      `;
    });
    tableHtml += `</tbody></table>`;
    studioMatrixContainer.innerHTML = tableHtml;

    studioSynthesisText.innerHTML = formatMarkdown(data.synthesis);
  } catch (err) {
    alert(`Studio error: ${err.message}`);
  } finally {
    runStudioCompareBtn.disabled = false;
    runStudioCompareBtn.textContent = "Execute Multi-Doc Synthesis";
  }
});

// Observatory Benchmarks
async function triggerBenchmark(mode) {
  const btn = mode === "enhanced" ? runEnhancedBenchmarkBtn : runBaselineBenchmarkBtn;
  btn.disabled = true;
  btn.textContent = `Running ${mode}...`;

  try {
    const res = await fetch("/api/evaluate/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode, top_k: 5 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Benchmark run failed");

    // Update metric cards
    $("obsRecallVal").textContent = `${(data.recall_at_k * 100).toFixed(1)}%`;
    $("obsMrrVal").textContent = data.mrr.toFixed(3);
    $("obsCitationVal").textContent = `${(data.citation_precision * 100).toFixed(1)}%`;
    $("obsLatencyVal").textContent = `${data.avg_latency_ms} ms`;

    await fetchEvalHistory();
  } catch (err) {
    alert(`Benchmark failure: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = mode === "enhanced" ? "Run Enhanced Hybrid Benchmark" : "Run Baseline Semantic-Only";
  }
}

runEnhancedBenchmarkBtn.addEventListener("click", () => triggerBenchmark("enhanced"));
runBaselineBenchmarkBtn.addEventListener("click", () => triggerBenchmark("baseline"));

async function fetchEvalHistory() {
  try {
    const res = await fetch("/api/evaluate/runs");
    const runs = await res.json();
    if (!runs || !runs.length) return;

    evalHistoryTbody.innerHTML = "";
    runs.forEach(r => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.innerHTML = `
        <td style="padding: 8px; font-family: var(--font-mono); color: var(--text-muted);">${r.timestamp ? r.timestamp.substring(11, 19) : ''}</td>
        <td style="padding: 8px; font-weight: 600; color: ${r.mode === 'enhanced' ? 'var(--accent-gold)' : 'var(--text-secondary)'};">${r.mode.toUpperCase()}</td>
        <td style="padding: 8px; font-family: var(--font-mono);">${(r.recall_at_k * 100).toFixed(1)}%</td>
        <td style="padding: 8px; font-family: var(--font-mono);">${r.mrr.toFixed(3)}</td>
        <td style="padding: 8px; font-family: var(--font-mono);">${(r.citation_precision * 100).toFixed(1)}%</td>
        <td style="padding: 8px; font-family: var(--font-mono); color: var(--accent-emerald);">${r.avg_latency_ms} ms</td>
      `;
      evalHistoryTbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Could not fetch eval history", err);
  }
}

// Initial startup check
(async () => {
  try {
    const res = await fetch("/api/health");
    const health = await res.json();
    $("statusText").textContent = `Online • ${health.llm_provider.toUpperCase()} • Hybrid Search`;
  } catch {
    $("statusText").textContent = "Backend Connection Offline";
  }
  await refreshDocuments();
})();