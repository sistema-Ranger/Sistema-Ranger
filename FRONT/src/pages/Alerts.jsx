import { useState } from "react";
import { LEVELS } from "../charts";
import { ALERT_LIST } from "../mock";

const ST = { open: "Abierta", ack: "Reconocida", resolved: "Resuelta" };
const color = (s) => LEVELS.find((l) => l.name === s).color;

export default function Alerts() {
  const [items, setItems] = useState(ALERT_LIST);
  const [tab, setTab] = useState("open");
  const setStatus = (id, status) => setItems(items.map((a) => (a.id === id ? { ...a, status } : a)));
  const count = (s) => items.filter((a) => a.status === s).length;
  const rows = tab === "all" ? items : items.filter((a) => a.status === tab);

  return (
    <>
      <h2>Alertas</h2>
      <p className="muted" style={{ margin: ".25rem 0 1.25rem" }}>Alertas generadas por las reglas y por el modelo de riesgo.</p>
      <p className="notice">Datos de ejemplo: los cambios de estado se guardarán cuando el backend publique las alertas.</p>
      <div className="tabs">
        {[["open", `Abiertas (${count("open")})`], ["ack", `Reconocidas (${count("ack")})`], ["resolved", `Resueltas (${count("resolved")})`], ["all", "Todas"]].map(([k, t]) => (
          <button key={k} className={`ghost ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>{t}</button>
        ))}
      </div>
      <section className="panel table-wrap">
        <table>
          <thead><tr><th>Severidad</th><th>Host</th><th>Descripción</th><th>Hora</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan="6" className="muted">No hay alertas en esta categoría.</td></tr>}
            {rows.map((a) => (
              <tr key={a.id}>
                <td><span className="tag" style={{ background: color(a.sev) }}>{a.sev}</span></td>
                <td className="mono">{a.host}</td><td>{a.text}</td><td className="mono">{a.time}</td><td>{ST[a.status]}</td>
                <td className="actions">
                  {a.status === "open" && <button className="ghost" onClick={() => setStatus(a.id, "ack")}>Reconocer</button>}
                  {a.status !== "resolved" && <button className="ghost" onClick={() => setStatus(a.id, "resolved")}>Resolver</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
