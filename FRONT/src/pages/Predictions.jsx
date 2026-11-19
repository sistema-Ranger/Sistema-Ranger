import { useState } from "react";
import { LineChart, level } from "../charts";
import { FACTORS, HOSTS, clock, hhmm } from "../mock";

const MULT = { 15: 0.85, 30: 1, 60: 1.2 };

export default function Predictions() {
  const [horizon, setHorizon] = useState(30);
  const [sel, setSel] = useState(HOSTS[0].name);
  const rows = HOSTS.map((h) => ({ ...h, risk: Math.min(0.99, h.risk * MULT[horizon]) }));
  const cur = rows.find((r) => r.name === sel);
  const n = 13;
  const trend = Array.from({ length: n }, (_, i) => Math.max(0, cur.risk * 100 * (0.55 + 0.45 * (i / (n - 1))) + Math.sin(i) * 3));
  const labels = clock(n, 300).map((d) => hhmm(d));

  return (
    <>
      <header className="head">
        <div>
          <h2>Predicciones</h2>
          <p className="muted">Probabilidad de fallo estimada por el modelo de machine learning</p>
        </div>
        <div className="controls">
          <label>Horizonte
            <select value={horizon} onChange={(e) => setHorizon(+e.target.value)}>
              <option value={15}>15 minutos</option><option value={30}>30 minutos</option><option value={60}>60 minutos</option>
            </select>
          </label>
        </div>
      </header>
      <p className="notice">Datos de ejemplo: se conectarán cuando el modelo publique sus predicciones.</p>

      <div className="grid2">
        <section className="panel">
          <h3>Riesgo por host</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Host</th><th>Riesgo</th><th>Nivel</th><th>Factor principal</th><th>Tendencia</th></tr></thead>
              <tbody>
                {rows.map((r) => {
                  const l = level(r.risk);
                  return (
                    <tr key={r.name} onClick={() => setSel(r.name)} style={{ cursor: "pointer", background: r.name === sel ? "#f3f6f9" : undefined }}>
                      <td className="mono">{r.name}</td>
                      <td style={{ minWidth: 140 }}>
                        <div className="between"><span className="mono">{Math.round(r.risk * 100)}%</span></div>
                        <div className="bar"><b style={{ width: `${r.risk * 100}%`, background: l.color }} /></div>
                      </td>
                      <td><span className="tag" style={{ background: l.color }}>{l.name}</span></td>
                      <td>{FACTORS[r.name][0]}</td><td className="mono">{FACTORS[r.name][1]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="muted sm foot">Haz clic en un host para ver su evolución.</p>
        </section>
        <section className="panel">
          <h3>Evolución del riesgo · {sel}</h3>
          <p className="muted sm">Última hora, probabilidad de fallo en los próximos {horizon} min</p>
          <LineChart h={240} labels={labels} series={[{ data: trend, color: level(cur.risk).color }]} threshold={{ value: 75, label: "Crítico 75%" }} />
        </section>
      </div>
    </>
  );
}
