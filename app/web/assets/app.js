const downloadForm = document.querySelector("#download-form");
const convertForm = document.querySelector("#convert-form");
const submitButton = document.querySelector("#submit-button");
const convertSubmitButton = document.querySelector("#convert-submit-button");
const conversionTypeSelect = document.querySelector("#conversion_type");
const convertOutputFormatSelect = document.querySelector("#convert_output_format");
const convertFileInput = document.querySelector("#convert_file");

const emptyState = document.querySelector("#empty-state");
const taskCard = document.querySelector("#task-card");
const resultCard = document.querySelector("#result-card");
const errorCard = document.querySelector("#error-card");

const taskIdNode = document.querySelector("#task-id");
const taskKindNode = document.querySelector("#task-kind");
const taskStatusNode = document.querySelector("#task-status");
const taskMessageNode = document.querySelector("#task-message");
const taskProgressNode = document.querySelector("#task-progress");
const progressBarNode = document.querySelector("#progress-bar");

const resultFileNameNode = document.querySelector("#result-file-name");
const resultFileSizeNode = document.querySelector("#result-file-size");
const resultFilePathNode = document.querySelector("#result-file-path");
const resultSourceUrlNode = document.querySelector("#result-source-url");
const resultSourceFileNameNode = document.querySelector("#result-source-file-name");
const resultOutputFormatNode = document.querySelector("#result-output-format");
const resultConversionTypeNode = document.querySelector("#result-conversion-type");
const resultGeneratedFilesNode = document.querySelector("#result-generated-files");
const resultDownloadLinkNode = document.querySelector("#result-download-link");

const errorCodeNode = document.querySelector("#error-code");
const errorMessageNode = document.querySelector("#error-message");

const conversionFormatOptions = {
  image: [
    { value: "png", label: "PNG" },
    { value: "jpg", label: "JPG" },
    { value: "webp", label: "WEBP" },
  ],
  pdf: [
    { value: "png", label: "PNG" },
    { value: "jpg", label: "JPG" },
  ],
};

let currentTaskId = null;
let pollTimer = null;

if (downloadForm) {
  downloadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(downloadForm);
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

    await submitJsonTask({
      endpoint: "/api/v1/tasks/downloads",
      payload,
      button: submitButton,
      idleLabel: "Start Download Task",
      pendingLabel: "Submitting...",
    });
  });
}

if (convertForm) {
  updateConvertFormatOptions();

  convertForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(convertForm);

    await submitMultipartTask({
      endpoint: "/api/v1/tasks/conversions",
      payload: formData,
      button: convertSubmitButton,
      idleLabel: "Start Convert Task",
      pendingLabel: "Uploading...",
    });
  });
}

if (conversionTypeSelect) {
  conversionTypeSelect.addEventListener("change", updateConvertFormatOptions);
}

function updateConvertFormatOptions() {
  if (!conversionTypeSelect || !convertOutputFormatSelect || !convertFileInput) {
    return;
  }

  const conversionType = conversionTypeSelect.value || "image";
  const options = conversionFormatOptions[conversionType] || conversionFormatOptions.image;

  convertOutputFormatSelect.innerHTML = "";
  options.forEach((option, index) => {
    const optionNode = document.createElement("option");
    optionNode.value = option.value;
    optionNode.textContent = option.label;
    if (index === 0) {
      optionNode.selected = true;
    }
    convertOutputFormatSelect.appendChild(optionNode);
  });

  convertFileInput.accept =
    conversionType === "pdf"
      ? ".pdf"
      : ".jpg,.jpeg,.png,.webp";
}

async function submitJsonTask({ endpoint, payload, button, idleLabel, pendingLabel }) {
  setSubmitting(button, true, pendingLabel, idleLabel);
  resetStatusCard();

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    await handleTaskAcceptance(response);
  } catch (error) {
    renderRequestError(error);
  } finally {
    setSubmitting(button, false, pendingLabel, idleLabel);
  }
}

async function submitMultipartTask({ endpoint, payload, button, idleLabel, pendingLabel }) {
  setSubmitting(button, true, pendingLabel, idleLabel);
  resetStatusCard();

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: payload,
    });

    await handleTaskAcceptance(response);
  } catch (error) {
    renderRequestError(error);
  } finally {
    setSubmitting(button, false, pendingLabel, idleLabel);
  }
}

async function handleTaskAcceptance(response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Task creation failed.");
  }

  currentTaskId = data.task_id;
  showTaskCard();
  updateTaskSummary({
    task_id: currentTaskId,
    task_kind: data.task_kind,
    status: data.status,
    progress_percent: 0,
    message: data.message,
  });

  startPolling();
}

function renderRequestError(error) {
  showTaskCard();
  showError("REQUEST_FAILED", error.message);
  updateTaskSummary({
    task_id: "-",
    status: "FAILURE",
    progress_percent: 0,
    message: "The API could not accept the task request.",
  });
}

function setSubmitting(button, isSubmitting, pendingLabel, idleLabel) {
  if (!button) {
    return;
  }

  button.disabled = isSubmitting;
  button.textContent = isSubmitting ? pendingLabel : idleLabel;
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
      showError(data.error_code || "TASK_FAILED", data.error_message || data.message);
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
  taskKindNode.textContent = data.task_kind || "-";
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
  resultSourceFileNameNode.textContent = result.source_file_name || "-";
  resultOutputFormatNode.textContent = result.output_format || "-";
  resultConversionTypeNode.textContent = result.conversion_type || "-";
  resultGeneratedFilesNode.textContent = result.generated_files_count || "-";

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
