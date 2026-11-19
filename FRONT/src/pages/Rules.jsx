import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

const METRICS = { cpu_percent: "CPU (%)", mem_percent: "RAM (%)", disk_free_percent: "Disco libre (%)", risk_score: "Riesgo del modelo (0–1)", events_error_count: "Errores en la ventana", latency_ms: "Latencia (ms)", error_rate: "Tasa de errores" };
const OPS = { gt: ">", gte: "≥", lt: "<", lte: "≤" };
const SEV = { low: ["Bajo", "#35688f"], medium: ["Medio", "#b07a1a"], high: ["Alto", "#b5421a"], critical: ["Crítico", "#8b1d3f"] };
const EMPTY = { name: "", metric: "cpu_percent", operator: "gt", threshold: "", duration_minutes: 0, severity: "medium", host_id: "", enabled: true };
const toForm = (r) => ({ ...r, host_id: r.host_id ?? "" });
const toBody = (f) => ({
  name: f.name, metric: f.metric, operator: f.operator, threshold: Number(f.threshold),
  duration_minutes: Number(f.duration_minutes), severity: f.severity, enabled: f.enabled,
  host_id: f.host_id === "" ? null : Number(f.host_id),
});

export default function Rules() {
  const { user } = useAuth();
  const canEdit = ["admin", "infra"].includes(user.role);
  const [rules, setRules] = useState(null);
  const [hosts, setHosts] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(null);

  const load = () => api.rules.list().then(setRules).catch((e) => setError(e.message));
  useEffect(() => { load(); api.hosts.list({ size: 200 }).then((d) => setHosts(d.items)).catch(() => {}); }, []);

  const run = async (fn) => { setError(""); try { await fn(); await load(); } catch (e) { setError(e.message); } };
  const reset = () => { setForm(EMPTY); setEditing(null); };
  const save = (e) => {
    e.preventDefault();
    run(async () => {
      const body = toBody(form);
      if (editing) await api.rules.update(editing, body); else await api.rules.create(body);
      reset();
    });
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const hostName = (id) => (id ? hosts.find((h) => h.id === id)?.hostname ?? `#${id}` : "Todos");

  return (
    <>
      <h2>Reglas de alerta</h2>
      <p className="muted" style={{ margin: ".25rem 0 1.25rem" }}>Umbrales que generan alertas cuando una métrica los supera.</p>
      {error && <p className="error" role="alert">{error}</p>}

      {canEdit && (
        <form onSubmit={save} className="panel row-form">
          <label>Nombre *<input value={form.name} onChange={set("name")} required maxLength={120} /></label>
          <label>Métrica
            <select value={form.metric} onChange={set("metric")}>{Object.entries(METRICS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label>Condición
            <select value={form.operator} onChange={set("operator")}>{Object.entries(OPS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label>Umbral *<input type="number" step="any" value={form.threshold} onChange={set("threshold")} required /></label>
          <label>Duración (min)<input type="number" min="0" max="1440" value={form.duration_minutes} onChange={set("duration_minutes")} /></label>
          <label>Severidad
            <select value={form.severity} onChange={set("severity")}>{Object.entries(SEV).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}</select>
          </label>
          <label>Host
            <select value={form.host_id} onChange={set("host_id")}>
              <option value="">Todos los hosts</option>
              {hosts.map((h) => <option key={h.id} value={h.id}>{h.hostname}</option>)}
            </select>
          </label>
          <div className="actions">
            <button>{editing ? "Guardar cambios" : "Crear regla"}</button>
            {editing && <button type="button" className="ghost" onClick={reset}>Cancelar</button>}
          </div>
        </form>
      )}

      <div className="panel table-wrap">
        <table>
          <thead><tr><th>Regla</th><th>Condición</th><th>Severidad</th><th>Host</th><th>Activa</th>{canEdit && <th></th>}</tr></thead>
          <tbody>
            {!rules && <tr><td colSpan="6" className="muted">Cargando…</td></tr>}
            {rules?.length === 0 && <tr><td colSpan="6" className="muted">No hay reglas.</td></tr>}
            {rules?.map((r) => (
              <tr key={r.id} className={r.enabled ? "" : "off"}>
                <td>{r.name}</td>
                <td className="mono">{METRICS[r.metric] ?? r.metric} {OPS[r.operator]} {r.threshold}{r.duration_minutes > 0 && ` · ${r.duration_minutes} min`}</td>
                <td><span className="tag" style={{ background: SEV[r.severity][1] }}>{SEV[r.severity][0]}</span></td>
                <td>{hostName(r.host_id)}</td>
                <td><input type="checkbox" checked={r.enabled} disabled={!canEdit} onChange={(e) => run(() => api.rules.update(r.id, { enabled: e.target.checked }))} aria-label={`Activar ${r.name}`} /></td>
                {canEdit && (
                  <td className="actions">
                    <button className="ghost" onClick={() => { setForm(toForm(r)); setEditing(r.id); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Editar</button>
                    <button className="ghost" onClick={() => window.confirm(`¿Eliminar la regla "${r.name}"?`) && run(() => api.rules.remove(r.id))}>Eliminar</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
