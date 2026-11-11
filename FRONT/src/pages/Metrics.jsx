import { useEffect, useState } from "react";
import { Legend, LineChart } from "../charts";
import { HOSTS, clock, hhmm, series } from "../mock";

const BLUE = "#2b6a9b", AMBER = "#b07a1a";
const CORES = [["Núcleo 0", BLUE, undefined], ["Núcleo 1", AMBER, "6 3"], ["Núcleo 2", "#6b4fa0", "2 3"], ["Núcleo 3", "#2f8f6a", "8 3 2 3"]];
const PARTS = [["/ (raíz)", 71.2], ["/var", 64.0], ["/data", 52.8], ["/boot", 23.1]];
const pcolor = (v) => (v >= 70 ? "#a83a14" : v >= 60 ? "#8c5a0a" : BLUE);
const day = (d) => d.toLocaleDateString("es-DO", { day: "2-digit", month: "2-digit", year: "numeric" });

export default function Metrics() {
  const [host, setHost] = useState(HOSTS[0].name);
  const [every, setEvery] = useState(10);
  const [paused, setPaused] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setTick((t) => t + 1), every * 1000);
    return () => clearInterval(id);
  }, [paused, every]);

  const n = 31, hi = HOSTS.findIndex((h) => h.name === host), seed = hi * 5 + tick;
  const times = clock(n, 10);
  const labels = times.map((d) => hhmm(d));
  const cores = CORES.map((c, k) => series(66 + hi * 3, 8, n, seed + k * 2));
  const ram = series(11.8, 0.6, n, seed), sent = series(3.5, 1.5, n, seed + 4), recv = series(11, 3, n, seed + 1);
  const last = (a) => a[n - 1];
  const avg = cores.reduce((s, c) => s + last(c), 0) / 4;
  const rows = [...Array(7)].map((_, i) => n - 1 - i);

  return (
    <>
      <header className="head">
        <div>
          <h2>Métricas en tiempo real</h2>
          <p className="muted">Lecturas enviadas por el recolector · intervalo configurable</p>
        </div>
        <div className="controls">
          <label>Host
            <select value={host} onChange={(e) => setHost(e.target.value)}>{HOSTS.map((h) => <option key={h.name}>{h.name}</option>)}</select>
          </label>
          <label>Actualizar cada
            <select value={every} onChange={(e) => setEvery(+e.target.value)}>
              {[5, 10, 30, 60].map((s) => <option key={s} value={s}>{s} segundos</option>)}
            </select>
          </label>
          <button className="ghost" onClick={() => setPaused(!paused)}>{paused ? "Reanudar" : "Pausar"}</button>
        </div>
      </header>
      <p className="notice">Datos de ejemplo: se conectarán cuando el backend publique las métricas del recolector.</p>

      <div className="grid1">
        <section className="panel">
          <div className="between"><h3>CPU</h3><span className="big mono">{avg.toFixed(1)} %</span></div>
          <p className="muted sm">Uso por núcleo · últimos 5 min</p>
          <Legend items={CORES.map(([name, color]) => ({ name, color }))} />
          <LineChart h={200} labels={labels} series={cores.map((data, k) => ({ data, color: CORES[k][1], dash: CORES[k][2] }))} />
        </section>
        <section className="panel">
          <div className="between"><h3>Memoria RAM</h3><span className="big mono">{last(ram).toFixed(1)} GB / 16 GB</span></div>
          <p className="muted sm">Memoria usada y disponible · últimos 5 min</p>
          <Legend items={[{ name: "Usada", color: AMBER }, { name: "Total 16 GB", color: "#9aa3ab" }]} />
          <LineChart h={200} area labels={labels} yMax={16} yTicks={[0, 4, 8, 12, 16]} yFmt={(v) => `${v} GB`}
            series={[{ data: ram, color: AMBER }, { data: Array(n).fill(16), color: "#9aa3ab", dash: "4 3" }]} />
        </section>
        <section className="panel">
          <div className="between"><h3>Almacenamiento</h3><span className="big mono">71.2 %</span></div>
          <ul className="parts">
            {PARTS.map(([name, v]) => (
              <li key={name}>
                <div className="between"><span className="mono">{name}</span><span className="mono">{v.toFixed(1)}%</span></div>
                <div className="bar thick"><b style={{ width: `${v}%`, background: pcolor(v) }} /></div>
              </li>
            ))}
          </ul>
          <p className="muted sm">Usado por partición · 412 de 640 GB en total</p>
        </section>
        <section className="panel">
          <div className="between"><h3>Tráfico de red</h3><span className="big mono">{last(recv).toFixed(1)} MB/s</span></div>
          <p className="muted sm">Bytes enviados y recibidos · últimos 5 min</p>
          <Legend items={[{ name: "Enviados", color: BLUE }, { name: "Recibidos", color: AMBER }]} />
          <LineChart h={200} labels={labels} yMax={20} yTicks={[0, 5, 10, 15, 20]} yFmt={(v) => `${v} MB/s`}
            series={[{ data: sent, color: BLUE, dash: "5 3" }, { data: recv, color: AMBER }]} />
        </section>
      </div>

      <section className="panel">
        <h3>Lecturas recientes</h3>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Fecha y hora</th><th>Host</th><th>CPU %</th><th>RAM %</th><th>Disco %</th><th>Red MB/s</th></tr></thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i} className="mono">
                  <td>{day(times[i])} {hhmm(times[i], true)}</td><td>{host}</td>
                  <td>{(cores.reduce((s, c) => s + c[i], 0) / 4).toFixed(1)}</td><td>{((ram[i] / 16) * 100).toFixed(1)}</td>
                  <td>71.2</td><td>{(sent[i] + recv[i] > 0 ? recv[i] + sent[i] * 0.3 : 0).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
