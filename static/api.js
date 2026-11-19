export const getStatus = () => fetch("/api/status");
export const getMetrics = () => fetch("/api/metrics");
export const getConfig = () => fetch("/api/config");
export const getAutoStart = () => fetch("/api/autostart");

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
