import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

const KINDS = { server: "Servidor", application: "Aplicación", service: "Servicio", database: "Base de datos" };
const STATUS = { up: "En línea", degraded: "Degradado", down: "Caído", unknown: "Sin datos" };
const EMPTY = { hostname: "", display_name: "", kind: "server", environment: "dev", area: "", ip_address: "", os: "", cpu_cores: "", mem_total_mb: "" };
const NUM = ["cpu_cores", "mem_total_mb"];
const toForm = (h) => Object.fromEntries(Object.keys(EMPTY).map((k) => [k, h[k] ?? ""]));
const EDITABLE = ["display_name", "kind", "environment", "area", "ip_address", "os"];
const pick = (b) => Object.fromEntries(EDITABLE.map((k) => [k, b[k]]));
const toBody = (f) => Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : NUM.includes(k) ? Number(v) : v]));

export default function Hosts() {
  const { user } = useAuth();
  const canEdit = ["admin", "infra"].includes(user.role);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(null);
  const [q, setQ] = useState("");
  const [inactive, setInactive] = useState(false);

  const load = () => api.hosts.list().then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const run = async (fn) => { setError(""); try { await fn(); await load(); } catch (e) { setError(e.message); } };
  const reset = () => { setForm(EMPTY); setEditing(null); };
  const save = (e) => {
    e.preventDefault();
    run(async () => {
      const body = editing ? pick(toBody(form)) : toBody(form);
      if (editing) await api.hosts.update(editing, body); else await api.hosts.create(body);
      reset();
    });
  };
  const edit = (h) => { setForm(toForm(h)); setEditing(h.id); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const shown = data?.items.filter((h) => (inactive || h.is_active) && `${h.hostname} ${h.display_name ?? ""}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <h2>Hosts</h2>
      <p className="muted" style={{ margin: ".25rem 0 1.25rem" }}>Inventario de servidores, aplicaciones y servicios monitoreados.</p>
      {error && <p className="error" role="alert">{error}</p>}

      {canEdit && (
        <form onSubmit={save} className="panel row-form">
          <label>Hostname *<input value={form.hostname} onChange={set("hostname")} required maxLength={120} disabled={!!editing} /></label>
          <label>Nombre visible<input value={form.display_name} onChange={set("display_name")} maxLength={120} /></label>
          <label>Tipo
            <select value={form.kind} onChange={set("kind")}>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label>Entorno *<input value={form.environment} onChange={set("environment")} required maxLength={40} /></label>
          <label>Área<input value={form.area} onChange={set("area")} maxLength={80} /></label>
          <label>IP<input value={form.ip_address} onChange={set("ip_address")} placeholder="10.0.0.5" /></label>
          <label>Sistema operativo<input value={form.os} onChange={set("os")} maxLength={80} /></label>
          <label>Núcleos CPU<input type="number" min="1" value={form.cpu_cores} onChange={set("cpu_cores")} disabled={!!editing} /></label>
          <label>RAM (MB)<input type="number" min="1" value={form.mem_total_mb} onChange={set("mem_total_mb")} disabled={!!editing} /></label>
          <div className="actions">
            <button>{editing ? "Guardar cambios" : "Registrar host"}</button>
            {editing && <button type="button" className="ghost" onClick={reset}>Cancelar</button>}
          </div>
        </form>
      )}

      <div className="panel">
        <div className="toolbar">
          <input placeholder="Buscar por nombre…" value={q} onChange={(e) => setQ(e.target.value)} />
          <label className="check"><input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} /> Mostrar inactivos</label>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Host</th><th>Tipo</th><th>Entorno</th><th>IP</th><th>Estado</th>{canEdit && <th></th>}</tr></thead>
            <tbody>
              {!data && <tr><td colSpan="6" className="muted">Cargando…</td></tr>}
              {shown?.length === 0 && <tr><td colSpan="6" className="muted">No hay hosts registrados.</td></tr>}
              {shown?.map((h) => (
                <tr key={h.id} className={h.is_active ? "" : "off"}>
                  <td><span className="mono">{h.hostname}</span>{h.display_name && <small>{h.display_name}</small>}</td>
                  <td>{KINDS[h.kind]}</td><td>{h.environment}</td><td className="mono">{h.ip_address ?? "—"}</td>
                  <td>{h.is_active ? (STATUS[h.status] ?? h.status) : "Desactivado"}</td>
                  {canEdit && (
                    <td className="actions">
                      <button className="ghost" onClick={() => edit(h)}>Editar</button>
                      {h.is_active
                        ? <button className="ghost" onClick={() => window.confirm(`¿Desactivar ${h.hostname}?`) && run(() => api.hosts.update(h.id, { is_active: false }))}>Desactivar</button>
                        : <button className="ghost" onClick={() => run(() => api.hosts.update(h.id, { is_active: true }))}>Reactivar</button>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && <p className="muted sm foot">{shown.length} hosts</p>}
      </div>
    </>
  );
}
