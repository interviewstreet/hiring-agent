/**
 * Hiring Agent — Frontend Application Logic
 * Handles drag-and-drop, file upload, settings, and terminal output streaming.
 */

(function () {
  "use strict";

  // --- DOM References ---
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const dropzonePanel = document.getElementById("dropzone-panel");
  const fileSelectedEl = document.getElementById("file-selected");
  const fileNameEl = document.getElementById("file-name");
  const fileSizeEl = document.getElementById("file-size");
  const removeBtn = document.getElementById("remove-file");
  const runBtn = document.getElementById("run-btn");
  const terminalPanel = document.getElementById("terminal-panel");
  const terminalOutput = document.getElementById("terminal-output");
  const terminalTitle = document.getElementById("terminal-title");
  const cursorLine = document.getElementById("cursor-line");
  const clearBtn = document.getElementById("clear-btn");
  const progressFill = document.getElementById("progress-fill");
  const terminalActions = document.getElementById("terminal-actions");
  const downloadReportBtn = document.getElementById("download-report-btn");

  // History DOM
  const historyBtn = document.getElementById("history-btn");
  const historySidebar = document.getElementById("history-sidebar");
  const closeHistoryBtn = document.getElementById("close-history");
  const historyList = document.getElementById("history-list");

  // Settings DOM
  const settingsBtn = document.getElementById("settings-btn");
  const settingsOverlay = document.getElementById("settings-overlay");
  const settingsClose = document.getElementById("settings-close");
  const modelSelect = document.getElementById("model-select");
  const apiKeyInput = document.getElementById("api-key-input");
  const toggleKeyVis = document.getElementById("toggle-key-vis");
  const currentKeyVal = document.getElementById("current-key-val");
  const settingsSave = document.getElementById("settings-save");
  const saveStatus = document.getElementById("save-status");
  const headerModelSelect = document.getElementById("header-model-select");
  const copyReportBtn = document.getElementById("copy-report-btn");

  // --- State ---
  let selectedFile = null;
  let isRunning = false;
  let eventSource = null;
  let currentReportContent = "";

  // --- Helpers ---
  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function scrollTerminal() {
    const body = document.querySelector(".terminal-body");
    body.scrollTop = body.scrollHeight;
  }

  function formatModelLabel(modelId) {
    // "gemini-2.5-flash" -> "Gemini 2.5 Flash"
    return modelId
      .replace("gemini-", "Gemini ")
      .replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .replace("Lite", "Lite")
      .replace("Pro", "Pro");
  }

  // --- Settings ---
  const AVAILABLE_MODELS = [
    // Cloud Models
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
  ];

  function getStoredKey() {
    return localStorage.getItem("gemini_api_key") || "";
  }

  function getStoredModel() {
    return localStorage.getItem("gemini_model") || "gemini-2.5-flash";
  }

  function loadSettings() {
    const currentModel = getStoredModel();
    const currentKey = getStoredKey();

    // Populate model dropdown
    modelSelect.innerHTML = "";
    AVAILABLE_MODELS.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = formatModelLabel(m);
      if (m === currentModel) opt.selected = true;
      modelSelect.appendChild(opt);
    });

    // Show current key masked
    if (currentKey) {
      if (currentKey.length > 10) {
        currentKeyVal.textContent = currentKey.substring(0, 6) + "•".repeat(currentKey.length - 10) + currentKey.slice(-4);
      } else {
        currentKeyVal.textContent = "•".repeat(currentKey.length);
      }
    } else {
      currentKeyVal.textContent = "Not set";
    }

    // Populate header model dropdown
    headerModelSelect.innerHTML = "";
    AVAILABLE_MODELS.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = formatModelLabel(m);
      if (m === currentModel) opt.selected = true;
      headerModelSelect.appendChild(opt);
    });
  }

  // Handle header select change
  headerModelSelect.addEventListener("change", (e) => {
    localStorage.setItem("gemini_model", e.target.value);
    loadSettings();
  });

  function openSettings() {
    loadSettings();
    apiKeyInput.value = "";
    saveStatus.classList.add("hidden");
    settingsOverlay.classList.remove("hidden");
    // Animate in
    requestAnimationFrame(() => {
      settingsOverlay.querySelector(".modal").classList.add("modal-open");
    });
  }

  function closeSettings() {
    const modal = settingsOverlay.querySelector(".modal");
    modal.classList.remove("modal-open");
    setTimeout(() => settingsOverlay.classList.add("hidden"), 200);
  }

  settingsBtn.addEventListener("click", openSettings);
  settingsClose.addEventListener("click", closeSettings);
  settingsOverlay.addEventListener("click", (e) => {
    if (e.target === settingsOverlay) closeSettings();
  });

  // Toggle API key visibility
  let keyVisible = false;
  toggleKeyVis.addEventListener("click", () => {
    keyVisible = !keyVisible;
    apiKeyInput.type = keyVisible ? "text" : "password";
    toggleKeyVis.title = keyVisible ? "Hide key" : "Show key";
  });

  // Save settings
  settingsSave.addEventListener("click", () => {
    const newModel = modelSelect.value;
    if (newModel) {
      localStorage.setItem("gemini_model", newModel);
    }

    const newKey = apiKeyInput.value.trim();
    if (newKey) {
      localStorage.setItem("gemini_api_key", newKey);
    }

    settingsSave.disabled = true;
    settingsSave.textContent = "Saving…";

    // Simulate slight delay for UI feedback
    setTimeout(() => {
      loadSettings();
      
      // Clear key input
      apiKeyInput.value = "";

      // Show saved and close
      saveStatus.textContent = "✓ Settings saved";
      saveStatus.className = "save-status save-success";
      saveStatus.classList.remove("hidden");
      
      setTimeout(() => {
        saveStatus.classList.add("hidden");
        closeSettings();
        
        settingsSave.disabled = false;
        settingsSave.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          Save Changes
        `;
      }, 600);
    }, 300);
  });

  // Keyboard shortcut: Escape closes modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!settingsOverlay.classList.contains("hidden")) {
        closeSettings();
      }
      if (!historySidebar.classList.contains("hidden")) {
        historySidebar.classList.add("hidden");
        document.body.classList.remove("sidebar-open");
      }
    }
  });

  // --- History & Download ---
  function getHistory() {
    try {
      return JSON.parse(sessionStorage.getItem("hiring_agent_history")) || [];
    } catch {
      return [];
    }
  }

  function saveToHistory(filename, content) {
    const history = getHistory();
    const item = {
      id: Date.now().toString(),
      filename: filename.replace(".pdf", ""),
      date: new Date().toLocaleString(),
      content: content
    };
    history.unshift(item);
    sessionStorage.setItem("hiring_agent_history", JSON.stringify(history));
    renderHistory();
  }

  function renderHistory() {
    const history = getHistory();
    historyList.innerHTML = "";
    if (history.length === 0) {
      historyList.innerHTML = `<p class="empty-history">No reports generated yet.</p>`;
      return;
    }

    history.forEach(item => {
      const el = document.createElement("div");
      el.className = "history-item";
      el.innerHTML = `
        <div class="history-item-title">${item.filename}</div>
        <div class="history-item-date">${item.date}</div>
        <div class="history-item-actions" style="gap: 8px;">
          <button class="history-item-btn copy-history" data-id="${item.id}" title="Copy Report">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg> Copy
          </button>
          <button class="history-item-btn download-history" data-id="${item.id}" title="Download Report">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg> Download
          </button>
        </div>
      `;
      historyList.appendChild(el);
    });

    document.querySelectorAll(".download-history").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        const histItem = getHistory().find(h => h.id === id);
        if (histItem) {
          downloadMarkdown(histItem.filename, histItem.content);
        }
      });
    });

    document.querySelectorAll(".copy-history").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        const histItem = getHistory().find(h => h.id === id);
        if (histItem) {
          navigator.clipboard.writeText(histItem.content);
          const originalHTML = btn.innerHTML;
          btn.innerHTML = `✓ Copied`;
          setTimeout(() => btn.innerHTML = originalHTML, 2000);
        }
      });
    });
  }

  historyBtn.addEventListener("click", () => {
    historySidebar.classList.remove("hidden");
    document.body.classList.add("sidebar-open");
    renderHistory();
  });

  closeHistoryBtn.addEventListener("click", () => {
    historySidebar.classList.add("hidden");
    document.body.classList.remove("sidebar-open");
  });

  function downloadMarkdown(filename, content) {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}_Report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  downloadReportBtn.addEventListener("click", () => {
    if (selectedFile && currentReportContent) {
      const filename = selectedFile.name.replace(".pdf", "");
      downloadMarkdown(filename, currentReportContent);
    }
  });

  copyReportBtn.addEventListener("click", () => {
    if (selectedFile && currentReportContent) {
      navigator.clipboard.writeText(currentReportContent);
      const originalHTML = copyReportBtn.innerHTML;
      copyReportBtn.innerHTML = `✓ Copied!`;
      setTimeout(() => copyReportBtn.innerHTML = originalHTML, 2000);
    }
  });

  // --- File Selection ---
  function selectFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please select a PDF file.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      alert("File is too large. Maximum 20MB.");
      return;
    }

    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatFileSize(file.size);

    dropzone.classList.add("hidden");
    fileSelectedEl.classList.remove("hidden");
  }

  function clearFile() {
    selectedFile = null;
    fileInput.value = "";
    dropzone.classList.remove("hidden");
    fileSelectedEl.classList.add("hidden");
  }

  // --- Drag & Drop ---
  dropzone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      selectFile(e.target.files[0]);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
      selectFile(e.dataTransfer.files[0]);
    }
  });

  // Prevent page-level drops
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("drop", (e) => e.preventDefault());

  // --- Remove File ---
  removeBtn.addEventListener("click", clearFile);

  // --- Run Evaluation ---
  runBtn.addEventListener("click", async () => {
    if (!selectedFile || isRunning) return;

    // Check if API key is set
    const currentKey = getStoredKey();
    if (!currentKey) {
      openSettings();
      alert("Please enter a Gemini API Key to run the evaluation.");
      return;
    }

    isRunning = true;
    runBtn.disabled = true;
    runBtn.classList.add("running");
    runBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10" stroke-dasharray="31" stroke-dashoffset="10">
          <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
        </circle>
      </svg>
      Running...
    `;

    // Show terminal
    terminalPanel.classList.remove("hidden");
    terminalActions.classList.add("hidden");
    terminalOutput.textContent = "";
    currentReportContent = "";
    cursorLine.classList.remove("hidden");
    terminalTitle.textContent = `hiring-agent — ${selectedFile.name}`;
    progressFill.className = "progress-fill active";

    // Scroll to terminal
    terminalPanel.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      // Upload file with local settings
      const formData = new FormData();
      formData.append("resume", selectedFile);
      formData.append("api_key", currentKey);
      formData.append("model", getStoredModel());

      const uploadResp = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      // Safe JSON parse
      let uploadData;
      let rawText = "";
      try {
        rawText = await uploadResp.text();
        uploadData = JSON.parse(rawText);
      } catch (parseErr) {
        appendOutput(`❌ Server response error: ${parseErr.message}\n`);
        appendOutput(`(HTTP ${uploadResp.status}) Raw response: "${rawText}"\n`);
        finishRun(false);
        return;
      }

      if (!uploadResp.ok) {
        appendOutput(`❌ Upload failed: ${uploadData.error || "Unknown error"}\n`);
        finishRun(false);
        return;
      }

      const job_id = uploadData.job_id;
      appendOutput("📤 Resume uploaded. Starting evaluation...\n\n");

      // Open SSE stream
      eventSource = new EventSource(`/api/stream/${job_id}`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "output") {
            appendOutput(data.text);
            currentReportContent += data.text;
          } else if (data.type === "done") {
            eventSource.close();
            eventSource = null;
            if (data.success) {
              saveToHistory(selectedFile.name, currentReportContent);
              terminalActions.classList.remove("hidden");
              finishRun(true);
            } else {
              finishRun(false);
            }
          }
        } catch (e) {
          // Ignore parse errors on SSE
        }
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        if (isRunning) {
          appendOutput("\n⚠️ Connection lost.\n");
          finishRun(false);
        }
      };
    } catch (err) {
      appendOutput(`\n❌ Error: ${err.message}\n`);
      finishRun(false);
    }
  });

  function appendOutput(text) {
    terminalOutput.textContent += text;
    scrollTerminal();
  }

  function finishRun(success) {
    isRunning = false;
    runBtn.disabled = false;
    runBtn.classList.remove("running");
    runBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      Run Evaluation
    `;

    cursorLine.classList.add("hidden");
    progressFill.className = success ? "progress-fill done" : "progress-fill";
  }

  // --- Clear / New ---
  clearBtn.addEventListener("click", () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    isRunning = false;
    terminalPanel.classList.add("hidden");
    terminalOutput.textContent = "";
    progressFill.className = "progress-fill";
    clearFile();
    runBtn.disabled = false;
    runBtn.classList.remove("running");
    runBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      Run Evaluation
    `;
  });

  // --- Init ---
  loadSettings();
})();
