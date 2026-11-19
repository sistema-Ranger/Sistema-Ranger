import { useState } from "react";
import { EVENTS, hhmm } from "../mock";

const LV = { info: ["Info", "#35688f"], warning: ["Aviso", "#b07a1a"], error: ["Error", "#b5421a"], critical: ["Crítico", "#8b1d3f"] };

export default function Logs() {
  const [level, setLevel] = useState("");
  const [host, setHost] = useState("");
  const [q, setQ] = useState("");
  const hosts = [...new Set(EVENTS.map((e) => e.host))];
  const rows = EVENTS.filter((e) => (!level || e.level === level) && (!host || e.host === host) && e.message.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <h2>Logs y eventos</h2>
      <p className="muted" style={{ margin: ".25rem 0 1.25rem" }}>Eventos reportados por los recolectores de cada host.</p>
      <p className="notice">Datos de ejemplo: se conectarán cuando el backend publique los eventos.</p>
      <div className="kpis">
        {Object.entries(LV).map(([k, [t, c]]) => (
          <section className="panel" key={k}>
            <p className="muted">{t}</p>
            <p className="big mono" style={{ color: c }}>{EVENTS.filter((e) => e.level === k).length}</p>
          </section>
        ))}
      </div>
      <section className="panel">
        <div className="toolbar">
          <input placeholder="Buscar en el mensaje…" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={level} onChange={(e) => setLevel(e.target.value)} style={{ width: "auto" }}>
            <option value="">Todos los niveles</option>
            {Object.entries(LV).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
          </select>
          <select value={host} onChange={(e) => setHost(e.target.value)} style={{ width: "auto" }}>
            <option value="">Todos los hosts</option>
            {hosts.map((h) => <option key={h}>{h}</option>)}
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Hora</th><th>Nivel</th><th>Host</th><th>Origen</th><th>Mensaje</th></tr></thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan="5" className="muted">Sin resultados para ese filtro.</td></tr>}
              {rows.map((e) => (
                <tr key={e.id}>
                  <td className="mono">{hhmm(e.time, true)}</td>
                  <td><span className="tag" style={{ background: LV[e.level][1] }}>{LV[e.level][0]}</span></td>
                  <td className="mono">{e.host}</td><td className="mono">{e.source}</td><td>{e.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
