import { useState } from "react";
import { LEVELS } from "../charts";
import { INCIDENTS } from "../mock";

const color = (s) => LEVELS.find((l) => l.name === s).color;

export default function History() {
  const [sev, setSev] = useState("");
  const rows = INCIDENTS.filter((i) => !sev || i.sev === sev);
  const done = INCIDENTS.filter((i) => i.minutes != null);
  const mttr = Math.round(done.reduce((s, i) => s + i.minutes, 0) / done.length);

  return (
    <>
      <h2>Historial de incidentes</h2>
      <p className="muted" style={{ margin: ".25rem 0 1.25rem" }}>Registro de incidentes detectados y su tiempo de resolución.</p>
      <p className="notice">Datos de ejemplo: se conectarán cuando el backend publique los incidentes.</p>
      <div className="kpis">
        <section className="panel"><p className="muted">Incidentes totales</p><p className="big mono">{INCIDENTS.length}</p></section>
        <section className="panel"><p className="muted">Abiertos</p><p className="big mono">{INCIDENTS.filter((i) => i.status === "Abierto").length}</p></section>
        <section className="panel"><p className="muted">Tiempo medio de resolución</p><p className="big mono">{mttr} <small>min</small></p></section>
        <section className="panel"><p className="muted">Críticos</p><p className="big mono" style={{ color: color("Crítico") }}>{INCIDENTS.filter((i) => i.sev === "Crítico").length}</p></section>
      </div>
      <section className="panel">
        <div className="toolbar">
          <select value={sev} onChange={(e) => setSev(e.target.value)} style={{ width: "auto" }}>
            <option value="">Todas las severidades</option>
            {LEVELS.map((l) => <option key={l.name}>{l.name}</option>)}
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Host</th><th>Incidente</th><th>Severidad</th><th>Inicio</th><th>Duración</th><th>Estado</th></tr></thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i.id}>
                  <td className="mono">{i.id}</td><td className="mono">{i.host}</td><td>{i.title}</td>
                  <td><span className="tag" style={{ background: color(i.sev) }}>{i.sev}</span></td>
                  <td className="mono">{i.started}</td><td className="mono">{i.minutes != null ? `${i.minutes} min` : "En curso"}</td><td>{i.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
