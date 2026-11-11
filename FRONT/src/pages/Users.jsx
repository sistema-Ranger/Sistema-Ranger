import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export const ROLES = {
  admin: "Administrador",
  infra: "Infraestructura",
  developer: "Desarrollador",
  analyst: "Analista",
  viewer: "Observador",
};
const EMPTY = { email: "", full_name: "", password: "", role: "viewer" };
const fmt = (d) => (d ? new Date(d).toLocaleString("es-DO") : "Nunca");

export default function Users() {
  const { user: me } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY);

  const load = () => api.users.list().then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const run = async (fn) => {
    setError("");
    try { await fn(); await load(); } catch (e) { setError(e.message); }
  };
  const create = (e) => {
    e.preventDefault();
    run(async () => { await api.users.create(form); setForm(EMPTY); });
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <h2>Usuarios</h2>
      {error && <p className="error" role="alert">{error}</p>}

      <form onSubmit={create} className="panel row-form">
        <label>Nombre<input value={form.full_name} onChange={set("full_name")} required maxLength={120} /></label>
        <label>Correo<input type="email" value={form.email} onChange={set("email")} required /></label>
        <label>Contraseña (mín. 8)<input type="password" value={form.password} onChange={set("password")} required minLength={8} maxLength={72} /></label>
        <label>Rol
          <select value={form.role} onChange={set("role")}>
            {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <button>Crear usuario</button>
      </form>

      <div className="panel table-wrap">
        <table>
          <thead><tr><th>Nombre</th><th>Rol</th><th>Estado</th><th>Último acceso</th><th></th></tr></thead>
          <tbody>
            {!data && <tr><td colSpan="5" className="muted">Cargando…</td></tr>}
            {data?.items.map((u) => {
              const self = u.id === me.id;
              return (
                <tr key={u.id} className={u.is_active ? "" : "off"}>
                  <td>{u.full_name}<small>{u.email}</small></td>
                  <td>
                    <select value={u.role} disabled={self} onChange={(e) => run(() => api.users.update(u.id, { role: e.target.value }))}>
                      {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </td>
                  <td>{u.is_active ? "Activo" : "Desactivado"}</td>
                  <td>{fmt(u.last_login_at)}</td>
                  <td>
                    {u.is_active ? (
                      <button className="ghost" disabled={self} onClick={() => run(() => api.users.deactivate(u.id))}>Desactivar</button>
                    ) : (
                      <button className="ghost" onClick={() => run(() => api.users.update(u.id, { is_active: true }))}>Reactivar</button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {data && <p className="muted foot">{data.total} usuarios</p>}
      </div>
    </>
  );
}
