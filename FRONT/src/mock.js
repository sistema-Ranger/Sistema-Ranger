// DATOS DE EJEMPLO: el backend aún no expone métricas, alertas ni predicciones.
export const series = (base, amp, n, seed = 0) =>
  Array.from({ length: n }, (_, i) =>
    Math.max(0, base + amp * Math.sin((i + seed) / 3) + (i / n) * amp + ((((i + seed) * 7) % 5) - 2) * amp * 0.12));
export const clock = (n, stepSec, end = new Date()) =>
  Array.from({ length: n }, (_, i) => new Date(end - (n - 1 - i) * stepSec * 1000));
export const hhmm = (d, sec) =>
  d.toLocaleTimeString("es-DO", { hour: "2-digit", minute: "2-digit", ...(sec && { second: "2-digit" }), hour12: false });
export const HOSTS = [
  { name: "api-01", risk: 0.72 }, { name: "db-01", risk: 0.41 }, { name: "worker-01", risk: 0.33 },
  { name: "web-01", risk: 0.08 }, { name: "cache-01", risk: 0.05 },
];
export const ALERTS = [
  { sev: "Crítico", host: "api-01", text: "CPU > 90% durante 18 min", time: "14:32" },
  { sev: "Alto", host: "api-01", text: "Riesgo del modelo ≥ alto: RAM en ascenso, posible fuga de memoria", time: "14:20" },
  { sev: "Alto", host: "db-01", text: "Latencia de consultas subió de 180 a 620 ms", time: "14:05" },
  { sev: "Medio", host: "worker-01", text: "Disco libre por debajo de 25%", time: "13:48" },
  { sev: "Bajo", host: "web-01", text: "Aumento de errores HTTP 5xx (+12%)", time: "13:31" },
];

// ---- Logs, alertas, predicciones e historial (ejemplo) ----
const ago = (m) => new Date(Date.now() - m * 60000);
export const EVENTS = [
  [2, "critical", "api-01", "kernel", "OOM killer finalizó el proceso worker (memoria agotada)"],
  [5, "error", "api-01", "nginx", "upstream timed out (110) mientras se leía la respuesta"],
  [9, "warning", "db-01", "postgres", "Consulta lenta: 620 ms en SELECT sobre metrics"],
  [14, "error", "web-01", "nginx", "HTTP 502 en /api/v1/hosts (3 veces en 1 min)"],
  [21, "info", "cache-01", "redis", "Snapshot RDB guardado correctamente"],
  [27, "warning", "worker-01", "systemd", "Disco / al 78% de uso"],
  [33, "info", "api-01", "app", "Despliegue v1.4.2 completado"],
  [41, "warning", "api-01", "app", "RAM en ascenso sostenido (+9% en 30 min)"],
  [58, "info", "web-01", "nginx", "Recarga de configuración exitosa"],
  [73, "error", "db-01", "postgres", "Conexión rechazada: se alcanzó max_connections"],
  [95, "info", "cache-01", "collector", "Lote de 120 métricas recibido"],
  [130, "critical", "worker-01", "kernel", "Pérdida de enlace de red eth0 durante 40 s"],
].map(([m, level, host, source, message], id) => ({ id, time: ago(m), level, host, source, message }));

export const ALERT_LIST = [
  ["Crítico", "api-01", "CPU > 90% durante 18 min", "14:32", "open"],
  ["Alto", "api-01", "Riesgo del modelo ≥ alto: RAM en ascenso, posible fuga de memoria", "14:20", "open"],
  ["Alto", "db-01", "Latencia de consultas subió de 180 a 620 ms", "14:05", "ack"],
  ["Medio", "worker-01", "Disco libre por debajo de 25%", "13:48", "open"],
  ["Bajo", "web-01", "Aumento de errores HTTP 5xx (+12%)", "13:31", "ack"],
  ["Medio", "db-01", "Conexiones activas al 85% del máximo", "12:10", "resolved"],
  ["Alto", "worker-01", "Host sin reportar durante 6 min", "11:42", "resolved"],
].map(([sev, host, text, time, status], id) => ({ id, sev, host, text, time, status }));

export const FACTORS = {
  "api-01": ["RAM en ascenso sostenido", "↑"], "db-01": ["Latencia de consultas", "↑"],
  "worker-01": ["Disco libre bajo", "→"], "web-01": ["Errores HTTP 5xx", "→"], "cache-01": ["Sin factores relevantes", "↓"],
};

export const INCIDENTS = [
  ["INC-014", "api-01", "Saturación de memoria", "Crítico", "Abierto", "18/11/2026 14:20", null],
  ["INC-013", "db-01", "Latencia alta en consultas", "Alto", "Abierto", "18/11/2026 14:05", null],
  ["INC-012", "worker-01", "Host sin reportar", "Alto", "Resuelto", "18/11/2026 11:42", 28],
  ["INC-011", "db-01", "Límite de conexiones alcanzado", "Medio", "Resuelto", "17/11/2026 22:15", 35],
  ["INC-010", "web-01", "Errores 5xx por despliegue", "Alto", "Resuelto", "16/11/2026 09:50", 18],
  ["INC-009", "api-01", "CPU sostenida sobre 90%", "Crítico", "Resuelto", "14/11/2026 03:12", 47],
  ["INC-008", "cache-01", "Reinicio inesperado de Redis", "Bajo", "Resuelto", "12/11/2026 16:40", 6],
].map(([id, host, title, sev, status, started, minutes]) => ({ id, host, title, sev, status, started, minutes }));