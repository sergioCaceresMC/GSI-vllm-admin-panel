export const getStatus = () => fetch("/api/status");
export const getMetrics = () => fetch("/api/metrics");
export const getConfig = () => fetch("/api/config");
export const getAutoStart = () => fetch("/api/autostart");

const validationMessages = {
  model: "Modelo: introduce un identificador con el formato organización/modelo.",
  served_model_name: "Nombre API: usa de 1 a 64 letras, números, puntos, guiones o guiones bajos.",
  gpu_memory_utilization: "Fracción de memoria GPU: introduce un número mayor que 0 y menor o igual a 1.",
  max_model_len: "Contexto máximo: introduce un entero positivo o -1 para el ajuste automático.",
  max_num_seqs: "Secuencias simultáneas: introduce un entero positivo.",
};

export async function requireOk(response, fallback) {
  if (response.ok) return;

  const data = await response.json().catch(() => null);
  const detail = data?.detail;
  const messages = Array.isArray(detail)
    ? detail.map((item) => validationMessages[item?.loc?.[1]]).filter(Boolean)
    : [];
  const message = typeof detail === "string" ? detail.trim() : "";
  throw new Error(messages.join(" ") || message || `${fallback} (HTTP ${response.status}).`);
}

export function serviceAction(command) {
  return fetch(`/api/${command}`, { method: "POST" });
}

function putJSON(url, value) {
  return fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  });
}

export const putConfig = (config) => putJSON("/api/config", config);
export const putAutoStart = (enabled) => putJSON("/api/autostart", { enabled });
