import { useState } from "react";
import { Gauge, LEVELS, Legend, LineChart, Sparkline, level } from "../charts";
import { ALERTS, HOSTS, clock, hhmm, series } from "../mock";

const STEP = { "1h": 300, "6h": 1800, "24h": 7200 };
const BLUE = "#2b6a9b", AMBER = "#b07a1a", GREY = "#7b8794";
const sevColor = (s) => LEVELS.find((l) => l.name === s).color;

export default function Dashboard() {
  const [host, setHost] = useState("all");
  const [range, setRange] = useState("1h");
  const [now, setNow] = useState(new Date());
  const n = 13;
  const labels = clock(n, STEP[range], now).map((d) => hhmm(d));
  const cpu = series(46, 12, n, 1), ram = series(66, 6, n, 2), net = series(8, 4, n, 3);
  const focus = host === "all" ? HOSTS[0] : HOSTS.find((h) => h.name === host);
  const lv = level(focus.risk);
  const kpis = [
    { t: "CPU promedio", v: "58.4", u: "%", d: "▲ 6.2 pts · vs. hora anterior", s: cpu, c: BLUE },
    { t: "Memoria RAM", v: "71.8", u: "%", d: "▲ 3.1 pts · 11.5 de 16 GB", s: ram, c: AMBER },
    { t: "Almacenamiento", v: "64.3", u: "%", d: "▲ 0.4 pts · 412 de 640 GB", s: series(60, 3, n, 4), c: BLUE },
    { t: "Tráfico de red", v: "12.8", u: "MB/s", d: "▲ 38% · pico 19.4 MB/s", s: net, c: GREY },
  ];

  return (
    <>
      <header className="head">
        <div>
          <h2>Dashboard general</h2>
          <p className="muted">Estado actual de los hosts monitoreados · actualizado {hhmm(now, true)}</p>
        </div>
        <div className="controls">
          <label>Host
            <select value={host} onChange={(e) => setHost(e.target.value)}>
              <option value="all">Todos los hosts</option>
              {HOSTS.map((h) => <option key={h.name}>{h.name}</option>)}
            </select>
          </label>
          <label>Rango
            <select value={range} onChange={(e) => setRange(e.target.value)}>
              <option value="1h">Última hora</option><option value="6h">Últimas 6 horas</option><option value="24h">Últimas 24 horas</option>
            </select>
          </label>
          <button onClick={() => setNow(new Date())}>Actualizar</button>
        </div>
      </header>
      <p className="notice">Datos de ejemplo: se conectarán cuando el backend publique métricas y alertas.</p>

      <div className="kpis">
        {kpis.map((k) => (
          <section className="panel" key={k.t}>
            <p className="muted">{k.t}</p>
            <p className="big mono">{k.v} <small>{k.u}</small></p>
            <p className="muted sm">{k.d}</p>
            <Sparkline data={k.s} color={k.c} />
          </section>
        ))}
      </div>

      <div className="grid2">
        <section className="panel">
          <h3>Uso de recursos en tiempo real</h3>
          <Legend items={[{ name: "CPU", color: BLUE }, { name: "RAM", color: AMBER }, { name: "Red (0–25 MB/s, escalada)", color: GREY }]} />
          <LineChart labels={labels} threshold={{ value: 80, label: "Umbral CPU 80%" }}
            series={[{ data: cpu, color: BLUE }, { data: ram, color: AMBER }, { data: net.map((v) => (v / 25) * 100), color: GREY, dash: "2 3" }]} />
        </section>
        <section className="panel center">
          <h3 className="left">Nivel de riesgo (modelo ML)</h3>
          <Gauge value={focus.risk} />
          <p className="big mono">{Math.round(focus.risk * 100)}% · {lv.name}</p>
          <p className="muted sm">{focus.name} · probabilidad de fallo en los próximos 30 min</p>
          <Legend items={LEVELS} />
        </section>
      </div>

      <div className="grid2">
        <section className="panel">
          <h3>Alertas recientes</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Severidad</th><th>Host</th><th>Descripción</th><th>Hora</th></tr></thead>
              <tbody>
                {ALERTS.map((a, i) => (
                  <tr key={i}>
                    <td><span className="tag" style={{ background: sevColor(a.sev) }}>{a.sev}</span></td>
                    <td className="mono">{a.host}</td><td>{a.text}</td><td className="mono">{a.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <h3>Hosts monitoreados</h3>
          <ul className="hosts">
            {HOSTS.map((h) => {
              const l = level(h.risk);
              return (
                <li key={h.name}>
                  <i className="dot" style={{ background: l.color }} /><span className="mono">{h.name}</span>
                  <div className="bar"><b style={{ width: `${h.risk * 100}%`, background: l.color }} /></div>
                  <span className="muted sm">{l.name} · {Math.round(h.risk * 100)}%</span>
                </li>
              );
            })}
          </ul>
          <p className="muted sm">5 recolectores conectados</p>
        </section>
      </div>
    </>
  );
}
