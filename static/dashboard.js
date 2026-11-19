import {
  getAutoStart,
  getConfig,
  getMetrics,
  getStatus,
  putAutoStart,
  putConfig,
  requireOk,
  serviceAction,
} from "./api.js?v=4";

async function updateStatus() {
  const status = document.getElementById("status");

  try {
    const response = await getStatus();

    if (!response.ok) {
      throw new Error("Error consultando el estado");
    }

    const data = await response.json();

    let text = "";

    switch (data.state) {
      case "ready":
        text = "Modelo disponible";
        break;

      case "starting":
        text = "Servicio activo, esperando al modelo";
        break;

      case "stopped":
        text = "Servicio detenido";
        break;

      default:
        text = "Estado desconocido";
    }

    status.dataset.state = data.state;
    if (status.textContent !== text) {
      status.textContent = text;
    }
  } catch (error) {
    status.dataset.state = "error";
    if (status.textContent !== "Error de conexión") {
      status.textContent = "Error de conexión";
    }
  }
}

async function action(command) {
  try {
    const response = await serviceAction(command);

    await requireOk(response, "No se pudo controlar el servicio");

    await updateStatus();
  } catch (error) {
    alert("Error: " + error.message);
  }
}

async function updateMetrics() {
  try {
    const response = await getMetrics();

    if (!response.ok) {
      throw new Error("No se pudieron obtener las métricas");
    }

    const data = await response.json();

    document.getElementById("cpu").textContent = data.cpu;

    document.getElementById("ram").textContent =
      `${data.ram.used_gb} / ${data.ram.total_gb} GB (${data.ram.percent}%)`;

    if (data.gpu) {
      document.getElementById("gpu-name").textContent = data.gpu.name;
      document.getElementById("gpu-util").textContent =
        data.gpu.utilization;

      document.getElementById("vram").textContent =
        `${data.gpu.memory_used} / ${data.gpu.memory_total} MiB`;

      document.getElementById("gpu-temp").textContent =
        data.gpu.temperature;
    }
  } catch (error) {
    console.error("Error de monitorización:", error);
  }
}

let currentConfig = null;
const toolChoice = document.getElementById("enable_auto_tool_choice");
const toolParser = document.getElementById("tool_call_parser");

function updateToolParser() {
  toolParser.disabled = toolChoice.value !== "true";
}

toolChoice.addEventListener("change", updateToolParser);

async function loadConfig() {
  const response = await getConfig();

  if (!response.ok) {
    throw new Error("No se pudo cargar la configuración");
  }

  currentConfig = await response.json();

  document.getElementById("model").value = currentConfig.model;

  document.getElementById("served_model_name").value =
    currentConfig.served_model_name;

  document.getElementById("gpu_memory_utilization").value =
    currentConfig.gpu_memory_utilization;

  document.getElementById("max_model_len").value =
    currentConfig.max_model_len;

  document.getElementById("max_num_seqs").value =
    currentConfig.max_num_seqs;
  toolChoice.value = String(currentConfig.enable_auto_tool_choice ?? "");
  toolParser.value = currentConfig.tool_call_parser ?? "";
  updateToolParser();
}

async function saveConfig() {
  const config = {
    ...currentConfig,

    model: document.getElementById("model").value,

    served_model_name: document.getElementById("served_model_name").value,

    gpu_memory_utilization: document.getElementById("gpu_memory_utilization").valueAsNumber,
    max_model_len: document.getElementById("max_model_len").valueAsNumber,
    max_num_seqs: document.getElementById("max_num_seqs").valueAsNumber,
    enable_auto_tool_choice: toolChoice.value === "" ? null : toolChoice.value === "true",
    tool_call_parser: toolChoice.value === "true" ? toolParser.value.trim() || null : null,
  };

  const response = await putConfig(config);

  await requireOk(response, "No se pudo guardar la configuración");

  currentConfig = config;

  document.getElementById("config-message").textContent =
    "Configuración guardada. Reinicia vLLM para aplicarla.";
}

async function applyConfig() {
  const message = document.getElementById("config-message");
  try {
    await saveConfig();
  } catch (error) {
    message.textContent = error.message;
    return;
  }

  try {
    const response = await serviceAction("restart");
    await requireOk(response, "No se pudo reiniciar vLLM");
    message.textContent = "Reinicio solicitado. Esperando a que el modelo esté disponible.";
  } catch (error) {
    message.textContent = `Configuración guardada. Error al reiniciar vLLM: ${error.message}`;
  }
}

loadConfig().catch((error) => {
  console.error(error);
});

async function loadAutoStart() {
  const response = await getAutoStart();

  if (!response.ok) {
    throw new Error("No se pudo consultar el inicio automático");
  }

  const data = await response.json();

  document.getElementById("autostart").checked = data.enabled;
}

async function setAutoStart() {
  const checkbox = document.getElementById("autostart");

  const enabled = checkbox.checked;

  try {
    const response = await putAutoStart(enabled);

    await requireOk(response, "No se pudo actualizar el inicio automático");
  } catch (error) {
    checkbox.checked = !enabled;
    alert("Error: " + error.message);
  }
}

loadAutoStart().catch(console.error);

updateMetrics();
setInterval(updateMetrics, 3000);

updateStatus();
setInterval(updateStatus, 3000);

for (const button of document.querySelectorAll("[data-service-action]")) {
  button.addEventListener("click", () => action(button.dataset.serviceAction));
}

document.getElementById("autostart").addEventListener("change", setAutoStart);
document.getElementById("apply-config").addEventListener("click", applyConfig);
document.getElementById("save-config").addEventListener("click", () => {
  saveConfig().catch((error) => {
    document.getElementById("config-message").textContent = error.message;
  });
});
