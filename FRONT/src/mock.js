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
