const state = {
  snapshot: null,
  activeJobId: null,
  pollTimer: null,
  safeQueue: [],
};

const elements = {
  steps: document.querySelector("#pipeline-steps"),
  consoleOutput: document.querySelector("#console-output code"),
  consoleStatus: document.querySelector("#console-status"),
  consoleTitle: document.querySelector("#console-title"),
  consoleDuration: document.querySelector("#console-duration"),
  artifactOutput: document.querySelector("#artifact-output code"),
  artifactTitle: document.querySelector("#artifact-title"),
  artifactType: document.querySelector("#artifact-type"),
  artifactSize: document.querySelector("#artifact-size"),
  toast: document.querySelector("#toast"),
  safeDemo: document.querySelector("#start-safe-demo"),
};

const SAFE_SEQUENCE = [
  "process-data",
  "quality-check",
  "fixed-keywords",
  "preview-keywords",
  "validate-results",
  "langgraph-demo",
  "tests",
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  return `${seconds.toFixed(2)} s`;
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, 3600);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

function updateStats(stats) {
  document.querySelector("#stat-products").textContent = stats.products ?? "—";
  document.querySelector("#stat-methods").textContent = stats.methods ?? "—";
  document.querySelector("#stat-experiments").textContent = stats.experiments ?? "—";
  document.querySelector("#stat-accuracy").textContent =
    stats.accuracy === null || stats.accuracy === undefined
      ? "—"
      : `${(stats.accuracy * 100).toFixed(2)}%`;
}

function artifactButtons(paths) {
  if (!paths.length) return "";
  return `
    <div class="artifact-links">
      ${paths
        .map(
          (path) => `
            <button class="artifact-link" type="button" data-artifact="${escapeHtml(path)}"
              title="${escapeHtml(path)}">${escapeHtml(path.split("/").at(-1))}</button>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderSteps(steps) {
  let currentGroup = "";
  elements.steps.innerHTML = steps
    .map((step) => {
      const group =
        step.group !== currentGroup
          ? `<div class="group-label">${escapeHtml(step.group)}</div>`
          : "";
      currentGroup = step.group;
      const missing = step.missing.length
        ? `<span class="missing-note">Needs: ${escapeHtml(step.missing.join(", "))}</span>`
        : "";
      return `
        ${group}
        <article class="step-card" id="step-${escapeHtml(step.id)}">
          <span class="step-number">${escapeHtml(step.number)}</span>
          <div>
            <div class="step-title-row">
              <span class="step-title">${escapeHtml(step.title)}</span>
              ${step.live ? '<span class="badge">Live API</span>' : ""}
              ${step.optional ? '<span class="badge">Optional</span>' : ""}
            </div>
            <p class="step-description">${escapeHtml(step.description)}</p>
            <code class="step-command" title="${escapeHtml(step.command)}">${escapeHtml(step.command)}</code>
            ${missing}
            ${artifactButtons(step.artifacts)}
          </div>
          <button
            class="step-button ${step.live ? "live" : ""}"
            type="button"
            data-run="${escapeHtml(step.id)}"
            ${step.runnable && !state.activeJobId ? "" : "disabled"}
          >${step.live ? "Run live" : "Run"}</button>
        </article>
      `;
    })
    .join("");

  document.querySelectorAll("[data-run]").forEach((button) => {
    button.addEventListener("click", () => runStep(button.dataset.run));
  });
  document.querySelectorAll("[data-artifact]").forEach((button) => {
    button.addEventListener("click", () => openArtifact(button.dataset.artifact));
  });
}

async function refreshDashboard() {
  state.snapshot = await requestJson("/api/dashboard");
  updateStats(state.snapshot.stats);
  renderSteps(state.snapshot.steps);
}

function selectTab(name) {
  document.querySelectorAll(".panel-tab").forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".panel-content").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${name}-panel`);
  });
}

async function runStep(stepId, fromQueue = false) {
  if (state.activeJobId) {
    showToast("Wait for the active step to finish.");
    return;
  }
  const step = state.snapshot.steps.find((item) => item.id === stepId);
  if (!step || !step.runnable) {
    showToast("This step is waiting for a required input.");
    return;
  }

  let confirmLive = false;
  if (step.live) {
    confirmLive = window.confirm(
      "This step uses live search/API providers and may open Chrome or consume provider quota. Continue?",
    );
    if (!confirmLive) return;
  }

  try {
    const job = await requestJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step_id: stepId, confirm_live: confirmLive }),
    });
    state.activeJobId = job.id;
    elements.consoleTitle.textContent = step.title;
    elements.consoleOutput.textContent = "Starting…";
    elements.consoleDuration.textContent = "—";
    updateConsoleStatus("running");
    selectTab("console");
    markRunningStep(stepId);
    await refreshDashboard();
    pollJob(job.id, fromQueue);
  } catch (error) {
    showToast(error.message);
    if (fromQueue) state.safeQueue = [];
  }
}

function markRunningStep(stepId) {
  document.querySelectorAll(".step-card").forEach((card) => {
    card.classList.toggle("running", card.id === `step-${stepId}`);
  });
}

function updateConsoleStatus(status) {
  elements.consoleStatus.className = `console-status ${status}`;
  elements.consoleStatus.textContent =
    status === "completed" ? "Passed" : status[0].toUpperCase() + status.slice(1);
}

async function pollJob(jobId, fromQueue) {
  window.clearTimeout(state.pollTimer);
  try {
    const job = await requestJson(`/api/job?id=${encodeURIComponent(jobId)}`);
    elements.consoleOutput.textContent = job.log || "Waiting for output…";
    elements.consoleOutput.parentElement.scrollTop =
      elements.consoleOutput.parentElement.scrollHeight;
    elements.consoleDuration.textContent = formatDuration(job.duration_seconds);
    updateConsoleStatus(job.status);

    if (job.status === "running") {
      state.pollTimer = window.setTimeout(() => pollJob(jobId, fromQueue), 650);
      return;
    }

    state.activeJobId = null;
    document.querySelectorAll(".step-card").forEach((card) => {
      card.classList.remove("running");
      if (card.id === `step-${job.step_id}`) {
        card.classList.toggle("failed", job.status === "failed");
      }
    });
    await refreshDashboard();

    if (job.status === "failed") {
      showToast(`${job.title} failed. See the console output.`);
      state.safeQueue = [];
      return;
    }
    showToast(`${job.title} completed.`);
    if (job.artifacts.length) {
      await openArtifact(job.artifacts[0]);
    }
    if (fromQueue) runNextSafeStep();
  } catch (error) {
    state.activeJobId = null;
    state.safeQueue = [];
    showToast(error.message);
  }
}

async function openArtifact(path) {
  try {
    const artifact = await requestJson(`/api/artifact?path=${encodeURIComponent(path)}`);
    elements.artifactTitle.textContent = artifact.path;
    elements.artifactType.textContent = artifact.path.split(".").at(-1).toUpperCase();
    elements.artifactSize.textContent = formatSize(artifact.size);
    elements.artifactOutput.textContent = artifact.content;
    selectTab("artifact");
  } catch (error) {
    showToast(error.message);
  }
}

function runNextSafeStep() {
  while (state.safeQueue.length) {
    const next = state.safeQueue.shift();
    const step = state.snapshot.steps.find((item) => item.id === next);
    if (step?.runnable) {
      runStep(next, true);
      return;
    }
  }
  elements.safeDemo.disabled = false;
  elements.safeDemo.firstChild.textContent = "Run safe demo sequence ";
  showToast("Safe demo sequence completed.");
}

elements.safeDemo.addEventListener("click", () => {
  if (state.activeJobId) {
    showToast("Wait for the active step to finish.");
    return;
  }
  state.safeQueue = [...SAFE_SEQUENCE];
  elements.safeDemo.disabled = true;
  elements.safeDemo.firstChild.textContent = "Running safe sequence ";
  runNextSafeStep();
});

document.querySelectorAll(".panel-tab").forEach((button) => {
  button.addEventListener("click", () => selectTab(button.dataset.tab));
});

refreshDashboard().catch((error) => {
  elements.steps.innerHTML = `<div class="loading-card">${escapeHtml(error.message)}</div>`;
  showToast("The dashboard could not load project state.");
});
