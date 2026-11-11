const P = { l: 46, r: 12, t: 12, b: 26 };
export const LEVELS = [
  { name: "Bajo", color: "#35688f" }, { name: "Medio", color: "#b07a1a" },
  { name: "Alto", color: "#b5421a" }, { name: "Crítico", color: "#8b1d3f" },
];
export const level = (v) => LEVELS[Math.min(3, Math.floor(v * 4))];

export function Legend({ items }) {
  return (
    <div className="legend">
      {items.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}
    </div>
  );
}

export function LineChart({ series, labels, yMax = 100, yTicks = [0, 25, 50, 75, 100], yFmt = (v) => `${v}%`, threshold, area, h = 280 }) {
  const W = 700, iw = W - P.l - P.r, ih = h - P.t - P.b, n = series[0].data.length;
  const x = (i) => P.l + (i / (n - 1)) * iw;
  const y = (v) => P.t + ih - (v / yMax) * ih;
  const path = (d) => d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const step = Math.max(1, Math.floor((n - 1) / 4));
  return (
    <svg viewBox={`0 0 ${W} ${h}`} className="chart" role="img">
      {yTicks.map((t) => (
        <g key={t}><line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} className="grid" /><text x={P.l - 6} y={y(t) + 4} textAnchor="end">{yFmt(t)}</text></g>
      ))}
      {labels.map((l, i) => i % step === 0 && <text key={i} x={x(i)} y={h - 6} textAnchor="middle">{l}</text>)}
      {threshold && (
        <g><line x1={P.l} x2={W - P.r} y1={y(threshold.value)} y2={y(threshold.value)} stroke="#c8602f" strokeDasharray="5 4" />
          <text x={W - P.r} y={y(threshold.value) - 5} textAnchor="end" style={{ fill: "#c8602f" }}>{threshold.label}</text></g>
      )}
      {area && <path d={`${path(series[0].data)}L${x(n - 1)},${y(0)}L${x(0)},${y(0)}Z`} fill={series[0].color} opacity=".14" />}
      {series.map((s, k) => <path key={k} d={path(s.data)} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash} />)}
    </svg>
  );
}

export function Sparkline({ data, color }) {
  const mn = Math.min(...data), mx = Math.max(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 120},${33 - ((v - mn) / (mx - mn || 1)) * 28}`).join(" ");
  return (
    <svg viewBox="0 0 120 36" preserveAspectRatio="none" className="spark" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

const pol = (a, r) => [150 + r * Math.cos((a * Math.PI) / 180), 150 + r * Math.sin((a * Math.PI) / 180)];
const arc = (a1, a2) => { const [x1, y1] = pol(a1, 110), [x2, y2] = pol(a2, 110); return `M${x1},${y1}A110,110 0 0 1 ${x2},${y2}`; };

export function Gauge({ value }) {
  const [nx, ny] = pol(180 + value * 180, 92);
  return (
    <svg viewBox="0 0 300 170" className="gauge-svg" role="img" aria-label={`Riesgo ${Math.round(value * 100)}%`}>
      {LEVELS.map((l, i) => <path key={l.name} d={arc(182 + i * 45, 223 + i * 45)} stroke={l.color} strokeWidth="26" fill="none" />)}
      <line x1="150" y1="150" x2={nx} y2={ny} stroke="#1b1d21" strokeWidth="4" strokeLinecap="round" />
      <circle cx="150" cy="150" r="9" fill="#1b1d21" />
    </svg>
  );
}
