const form = document.querySelector("#download-form");
const submitButton = document.querySelector("#submit-button");
const emptyState = document.querySelector("#empty-state");
const taskCard = document.querySelector("#task-card");
const resultCard = document.querySelector("#result-card");
const errorCard = document.querySelector("#error-card");

const taskIdNode = document.querySelector("#task-id");
const taskStatusNode = document.querySelector("#task-status");
const taskMessageNode = document.querySelector("#task-message");
const taskProgressNode = document.querySelector("#task-progress");
const progressBarNode = document.querySelector("#progress-bar");

const resultFileNameNode = document.querySelector("#result-file-name");
const resultFileSizeNode = document.querySelector("#result-file-size");
const resultFilePathNode = document.querySelector("#result-file-path");
const resultSourceUrlNode = document.querySelector("#result-source-url");
const resultDownloadLinkNode = document.querySelector("#result-download-link");

const errorCodeNode = document.querySelector("#error-code");
const errorMessageNode = document.querySelector("#error-message");

let currentTaskId = null;
let pollTimer = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = {
    url: formData.get("url"),
  };

  const platformHint = formData.get("platform_hint");
  const outputFormat = formData.get("output_format");

  if (platformHint) {
    payload.platform_hint = platformHint;
  }

  if (outputFormat) {
    payload.output_format = outputFormat;
  }

  setSubmitting(true);
  resetStatusCard();

  try {
    const response = await fetch("/api/v1/tasks/downloads", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Task creation failed.");
    }

    currentTaskId = data.task_id;
    showTaskCard();
    updateTaskSummary({
      task_id: currentTaskId,
      status: data.status,
      progress_percent: 0,
      message: data.message,
    });

    startPolling();
  } catch (error) {
    showTaskCard();
    showError("REQUEST_FAILED", error.message);
    updateTaskSummary({
      task_id: "-",
      status: "FAILURE",
      progress_percent: 0,
      message: "The API could not accept the task request.",
    });
  } finally {
    setSubmitting(false);
  }
});

function setSubmitting(isSubmitting) {
  submitButton.disabled = isSubmitting;
  submitButton.textContent = isSubmitting
    ? "Submitting..."
    : "Start Download Task";
}

function startPolling() {
  stopPolling();
  pollTask();
  pollTimer = window.setInterval(pollTask, 2500);
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function pollTask() {
  if (!currentTaskId) {
    return;
  }

  try {
    const response = await fetch(`/api/v1/tasks/${currentTaskId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Task status retrieval failed.");
    }

    updateTaskSummary(data);

    if (data.result) {
      renderResult(data.result);
    }

    if (data.error_code || data.error_message) {
      showError(data.error_code || "TASK_ERROR", data.error_message || data.message);
    }

    if (data.status === "SUCCESS") {
      stopPolling();
      hideError();
    }

    if (data.status === "FAILURE") {
      stopPolling();
      showError(data.error_code || "DOWNLOAD_FAILED", data.error_message || data.message);
    }
  } catch (error) {
    stopPolling();
    showError("POLLING_FAILED", error.message);
    updateTaskSummary({
      task_id: currentTaskId,
      status: "FAILURE",
      progress_percent: 0,
      message: "Polling stopped because the UI could not reach the API.",
    });
  }
}

function resetStatusCard() {
  resultCard.classList.add("hidden");
  errorCard.classList.add("hidden");
  resultDownloadLinkNode.classList.add("hidden");
  resultDownloadLinkNode.href = "#";
  progressBarNode.style.width = "0%";
  taskProgressNode.textContent = "0%";
}

function showTaskCard() {
  emptyState.classList.add("hidden");
  taskCard.classList.remove("hidden");
}

function updateTaskSummary(data) {
  const normalizedStatus = (data.status || "PENDING").toUpperCase();
  const progress = Number(data.progress_percent || 0);

  taskIdNode.textContent = data.task_id || "-";
  taskStatusNode.textContent = normalizedStatus;
  taskStatusNode.className = `status-badge ${statusClassName(normalizedStatus)}`;
  taskMessageNode.textContent = data.message || "Task state updated.";
  taskProgressNode.textContent = `${progress}%`;
  progressBarNode.style.width = `${Math.max(0, Math.min(progress, 100))}%`;
}

function renderResult(result) {
  resultCard.classList.remove("hidden");
  resultFileNameNode.textContent = result.file_name || "-";
  resultFileSizeNode.textContent = formatBytes(result.file_size_bytes);
  resultFilePathNode.textContent = result.file_path || "-";
  resultSourceUrlNode.textContent = result.source_url || "-";

  if (result.download_url) {
    resultDownloadLinkNode.classList.remove("hidden");
    resultDownloadLinkNode.href = result.download_url;
  } else {
    resultDownloadLinkNode.classList.add("hidden");
    resultDownloadLinkNode.href = "#";
  }
}

function showError(code, message) {
  errorCard.classList.remove("hidden");
  errorCodeNode.textContent = code || "-";
  errorMessageNode.textContent = message || "-";
}

function hideError() {
  errorCard.classList.add("hidden");
}

function statusClassName(status) {
  if (status === "SUCCESS") {
    return "status-success";
  }

  if (status === "FAILURE") {
    return "status-failure";
  }

  if (status === "STARTED") {
    return "status-started";
  }

  if (status === "PROGRESS") {
    return "status-progress";
  }

  return "status-pending";
}

function formatBytes(value) {
  const size = Number(value);

  if (!Number.isFinite(size) || size <= 0) {
    return "-";
  }

  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  const normalized = size / 1024 ** exponent;
  return `${normalized.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}
