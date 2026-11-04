# 06 · Frontend y UI

Stack: React 18 + TypeScript + Vite + Tailwind CSS + React Router + TanStack Query + Axios + Recharts + lucide-react + date-fns.

## Estructura de `FRONT/src`

```
src/
├── main.tsx / App.tsx
├── api/                 # client.ts (axios + interceptor JWT), endpoints por recurso
├── types/               # api.ts — espejo exacto de schemas (05) — o generados con openapi-typescript
├── hooks/               # useDashboard, useAlerts, useMetrics... (TanStack Query)
├── auth/                # AuthContext, ProtectedRoute, RoleGate
├── layouts/AppLayout.tsx  # Sidebar + header + <Outlet/>
├── components/
│   ├── ui/              # Card, KpiCard, Select, DateInput, Button, Badge, Table, Pagination, EmptyState, Chip
│   ├── charts/          # LineChartCard, BarChartCard, Sparkline, RiskGauge
│   └── domain/          # SeverityBadge, HostStatusDot, AlertRow, EvidenceList
├── pages/               # una por ruta
└── styles/index.css     # tokens + Tailwind
```

## Rutas

| Ruta | Página | Roles | En mockup |
|---|---|---|---|
| `/login` | Login | público | ➕ nueva |
| `/` | Dashboard general | todos | ✅ |
| `/metricas` | Métricas en tiempo real | todos menos viewer | ✅ |
| `/logs` | Logs y eventos | todos menos viewer | ✅ |
| `/predicciones` | Predicciones | todos | ✅ |
| `/alertas` | Alertas (+ detalle en drawer) | todos | ✅ |
| `/historial` | Historial | todos menos viewer | ✅ |
| `/incidentes` | Incidentes | todos | ➕ nueva |
| `/infraestructura` | Hosts | admin, infra | ➕ nueva |
| `/usuarios` | Usuarios | admin | ➕ nueva |

Sidebar (orden): Dashboard · Métricas · Logs y eventos · Predicciones · Alertas · Historial · Incidentes · Infraestructura · Usuarios. Ocultar ítems según rol.

## Tokens de diseño (derivados de los mockups)

```css
:root {
  --bg: #F2F2F0;            /* fondo de contenido */
  --surface: #FFFFFF;       /* tarjetas */
  --border: #E4E4E0;
  --sidebar: #1B1D21;       /* sidebar oscuro */
  --sidebar-active: #2C2F35;
  --text: #1A1A1A;
  --text-muted: #6B6B6B;
  --primary: #1F5F8B;       /* botones Actualizar / Filtrar / Consultar */
  --primary-hover: #184C70;

  --sev-low: #3B7DB3;       /* Bajo */
  --sev-medium: #C98A1B;    /* Medio */
  --sev-high: #C75A1E;      /* Alto */
  --sev-critical: #8E1B3A;  /* Crítico */

  --ok: #2E8B57; --warn: #C98A1B; --down: #B3261E; --unknown: #9A9A9A;
  --radius: 10px;
}
```

- Tipografía: **IBM Plex Sans** (UI) y **IBM Plex Mono** (valores numéricos de KPIs: `— %`, `— MB/s`).
- Tarjetas: fondo blanco, borde 1px `--border`, radio 10px, padding 16–20px, sin sombras fuertes.
- Tarjetas de severidad (Alertas): borde superior de 3px con el color de la severidad.
- Logo: icono de pulso + "Ranger" / subtítulo "Monitoreo y predicción".
- Mapeo enum → UI: `low→Bajo`, `medium→Medio`, `high→Alto`, `critical→Crítico`; `info/warning/error/critical` se muestran tal cual.

## Pantallas

### Dashboard general (`/`)
- Header: título, subtítulo "Estado actual de los hosts monitoreados", selects **Host** (Todos los hosts) y **Rango** (Última hora / 6 h / 24 h / 7 días), botón **Actualizar**.
- 4 `KpiCard`: CPU promedio (%), Memoria RAM (%), Almacenamiento (%), Tráfico de red (MB/s), cada una con sparkline de tendencia.
- "Uso de recursos en tiempo real": línea CPU, RAM, red por minuto.
- "Nivel de riesgo (modelo ML)": `RiskGauge` + leyenda Bajo/Medio/Alto/Crítico + link "Ver predicciones".
- "Alertas recientes": tabla Severidad · Host · Descripción · Hora + "Ver todas".
- "Hosts monitoreados": lista con punto de estado y último contacto.
- Datos: `GET /dashboard/overview`, refetch cada 15 s.
- Vacíos: "Sin alertas todavía", "Ningún recolector conectado".

### Métricas en tiempo real (`/metricas`)
- Selects **Host** y **Actualizar cada** (5/10/30/60 s) + botón **Pausar/Reanudar**.
- Grid 2×2: CPU por núcleo (líneas), Memoria usada vs disponible (área, `— GB / — GB`), Almacenamiento por partición (barras), Red enviados/recibidos (líneas).
- Tabla "Lecturas recientes": Fecha y hora · Host · CPU % · RAM % · Disco % · Red MB/s.
- Datos: `GET /metrics?host_id&from=now-15m` con `refetchInterval` según select.
- Vacío: "Esperando datos del recolector".

### Logs y eventos (`/logs`)
- Filtros: búsqueda en mensajes (placeholder "Ej. timeout, disk full, conexión rechazada"), Host, Desde, Hasta, botón **Filtrar**; chips de Nivel: Todos · Info · Warning · Error · Critical.
- 4 contadores por nivel (`/events/summary`).
- Tabla Eventos: Fecha y hora · Host · Nivel (badge) · Origen · Mensaje; paginación "Mostrando X de Y" + Anterior/Siguiente.
- Vacío: "No hay eventos registrados para estos filtros".

### Predicciones (`/predicciones`)
- Select Host.
- 4 KPIs: Nivel de riesgo actual, Probabilidad de fallo (horizonte del modelo, p. ej. 60 min*), Anomalías detectadas hoy, Modelo en uso (nombre + "Entrenado: fecha").
- "Riesgo estimado en el tiempo": línea `risk_score` con franjas de severidad de fondo (`ReferenceArea` 0–0.3–0.6–0.8–1) y puntos marcados donde `is_anomaly`.
- "Evaluación del modelo": Precision, Recall, F1-score, Muestras de entrenamiento + barras horizontales de importancia de características.
- Tabla "Predicciones por host": Host · Riesgo · Probabilidad · Factor principal · Generada.
- Vacío: "El modelo aún no ha generado predicciones".

> *El mockup dice "Probabilidad de fallo (24 h)"; el texto debe salir de `horizon_minutes` del modelo activo.

### Alertas (`/alertas`)
- Selects **Estado** (Activas / Reconocidas / Resueltas / Todas) y **Origen** (Todos / Reglas / Modelo / Correlación).
- 4 tarjetas por severidad con conteo.
- "Lista de alertas": Severidad · Host · Descripción · Origen · Fecha; clic abre **drawer de detalle** con evidencia, tendencia, riesgo, acción sugerida y botones Reconocer / Resolver / Crear incidente.
- Panel "Reglas de alerta" con botón **Nueva regla** (modal: métrica, operador, umbral, duración, severidad, host).
- Vacío: "No hay alertas activas".

### Historial (`/historial`)
- Filtros: Host, Métrica, Desde, Hasta, Agrupar por (Minuto/Hora/Día), botón **Consultar**; botón **Exportar CSV** arriba a la derecha.
- "Evolución de la métrica": línea avg con banda min–max y marcadores en periodos con alertas. Debajo: Promedio · Máximo · Mínimo · Registros.
- Tabla Registros: Periodo · Host · Promedio · Mínimo · Máximo · Alertas.
- Vacío: "Elige un host y un rango de fechas para consultar".

### Nuevas (no en mockup — mantener el mismo lenguaje visual)
- **Login:** tarjeta centrada sobre `--sidebar`, logo, email, contraseña, botón primario.
- **Incidentes:** tabla (título, host, severidad, estado, abierto, cerrado) + formulario/drawer con causa raíz y resolución, alertas vinculadas.
- **Infraestructura:** tabla de hosts con filtros entorno/área/estado y modal de edición.
- **Usuarios:** tabla + modal crear/editar rol.

## Reglas de implementación

- Todas las llamadas vía hooks de TanStack Query; nada de `fetch` suelto en componentes.
- Estados obligatorios en cada vista: **loading** (skeleton), **vacío** (texto del mockup), **error** (mensaje + reintentar).
- Fechas: recibir UTC, mostrar en hora local `dd/MM/yyyy HH:mm:ss`.
- Responsive: sidebar colapsable < 1024px; grids pasan a 1 columna < 768px.
- Accesibilidad: contraste AA, la severidad no se comunica solo por color (texto + color).
