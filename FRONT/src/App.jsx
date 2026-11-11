import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Metrics from "./pages/Metrics";
import Users, { ROLES } from "./pages/Users";

function Guard({ roles }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="boot">Cargando…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}

function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand-row">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#6fb1e0" strokeWidth="2" strokeLinejoin="round" aria-hidden="true">
            <polyline points="2,12 7,12 10,4 14,20 17,12 22,12" />
          </svg>
          <div><strong>Ranger</strong><small>Monitoreo y predicción</small></div>
        </div>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/metricas">Métricas</NavLink>
          {["Logs y eventos", "Predicciones", "Alertas", "Historial"].map((t) => <span key={t} className="soon" title="Próximamente">{t}</span>)}
          {user.role === "admin" && <NavLink to="/usuarios">Usuarios</NavLink>}
        </nav>
        <div className="me">
          <strong>{user.full_name}</strong>
          <small>{ROLES[user.role]}</small>
          <button className="ghost" onClick={logout}>Cerrar sesión</button>
        </div>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Guard />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="metricas" element={<Metrics />} />
          <Route element={<Guard roles={["admin"]} />}>
            <Route path="usuarios" element={<Users />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
