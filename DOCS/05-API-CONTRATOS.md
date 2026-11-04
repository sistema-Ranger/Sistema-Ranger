# 05 · Contratos de la API REST

- Base URL: `http://localhost:8000/api/v1` (excepto `/health`).
- Formato: JSON, fechas ISO‑8601 en UTC (`2026-10-15T20:00:00Z`).
- Auth usuarios: `Authorization: Bearer <jwt>`.
- Auth recolectores: `X-Collector-Key: <COLLECTOR_API_KEY>` (solo endpoints `/ingest/*`).
- Documentación automática: `/docs` (Swagger) y `/openapi.json`. El frontend puede generar tipos con `openapi-typescript`.

## Convenciones

**Paginación** (listas): `?page=1&size=50` → 
```json
{ "items": [...], "total": 132, "page": 1, "size": 50 }
```

**Errores:**
```json
{ "detail": "Mensaje legible", "code": "HOST_NOT_FOUND" }
```
| HTTP | Uso |
|---|---|
| 400 | Validación de negocio |
| 401 | Sin token / token inválido / API key inválida |
| 403 | Rol sin permiso |
| 404 | Recurso no existe |
| 409 | Conflicto (hostname/email duplicado) |
| 422 | Error de schema (Pydantic) |

## Endpoints

### Sistema
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/health` | público | `{"status":"ok"}` |

### Autenticación y usuarios
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/login` | público | form `username`(email) + `password` → `{access_token, token_type, user}` |
| GET | `/auth/me` | autenticado | Usuario actual |
| GET | `/users` | admin | Listar |
| POST | `/users` | admin | Crear `{email, full_name, password, role}` |
| PATCH | `/users/{id}` | admin | Cambiar rol, nombre, `is_active` |
| DELETE | `/users/{id}` | admin | Desactivar (soft delete) |

### Hosts (infraestructura)
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/hosts` | autenticado | Filtros `environment`, `area`, `status`, `kind` |
| GET | `/hosts/{id}` | autenticado | Detalle + última métrica + último riesgo |
| POST | `/hosts` | admin, infra | Registro manual |
| PATCH | `/hosts/{id}` | admin, infra | Editar metadatos |
| DELETE | `/hosts/{id}` | admin | Desactivar |

### Ingesta (recolector)
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/ingest/register` | API key | Upsert del host por `hostname` → `{host_id}` |
| POST | `/ingest/metrics` | API key | Lote de lecturas; actualiza `last_seen_at` y `status` |
| POST | `/ingest/events` | API key | Lote de logs/eventos |

```json
// POST /ingest/register
{ "hostname": "api-01", "kind": "server", "environment": "dev", "os": "Linux 6.6", "cpu_cores": 4, "mem_total_mb": 8192, "ip_address": "172.18.0.5" }
```

```json
// POST /ingest/metrics
{
  "hostname": "api-01",
  "readings": [{
    "ts": "2026-10-15T20:00:10Z",
    "cpu_percent": 92.1,
    "cpu_per_core": [95.0, 88.2, 91.4, 93.8],
    "mem_percent": 87.3,
    "mem_used_mb": 7150,
    "disk_percent": 64.0,
    "disk_partitions": [{"mount": "/", "percent": 64.0, "used_gb": 38.4, "total_gb": 60}],
    "net_sent_bps": 125000.0,
    "net_recv_bps": 480000.0,
    "latency_ms": 620,
    "error_rate": 4.2,
    "is_available": true
  }]
}
// 202 → { "accepted": 1 }
```

```json
// POST /ingest/events
{
  "hostname": "api-01",
  "events": [{
    "ts": "2026-10-15T20:00:09Z",
    "level": "error",
    "source": "api",
    "message": "HTTP 503 GET /orders upstream timeout",
    "attributes": { "status_code": 503, "path": "/orders" }
  }]
}
```

### Métricas
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/metrics` | Crudas: `host_id`, `from`, `to`, `limit` (máx. 5000) |
| GET | `/metrics/latest` | Última lectura por host (`?host_id` opcional) |
| GET | `/metrics/aggregate` | `host_id`, `metric`, `from`, `to`, `bucket=minute\|hour\|day` → `[{period, avg, min, max, samples, alerts}]` |
| GET | `/metrics/export.csv` | Mismos filtros que aggregate; descarga CSV (rol analyst+) |

`metric` ∈ `cpu_percent | mem_percent | disk_percent | net_sent_bps | net_recv_bps | latency_ms | error_rate`.

### Eventos
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/events` | `q` (texto), `host_id`, `level` (multi), `source`, `from`, `to`, paginado |
| GET | `/events/summary` | Conteo por nivel: `{info, warning, error, critical}` con los mismos filtros |

### Predicciones y modelo
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/predictions/latest` | Última predicción por host → tabla "Predicciones por host" |
| GET | `/predictions` | Serie: `host_id`, `from`, `to` → gráfica "Riesgo estimado en el tiempo" |
| GET | `/predictions/summary` | `{current_risk_level, failure_probability, anomalies_today}` (`?host_id`) |
| GET | `/models/active` | Modelo activo: nombre, versión, fecha, precision, recall, f1, n_samples, feature_importance |
| POST | `/models/{id}/activate` | admin — activar otra versión |

```json
// GET /predictions/latest
[{ "host_id": 1, "hostname": "api-01", "risk_level": "high", "risk_score": 0.74,
   "failure_probability": 0.68, "top_factor": "mem_percent_slope_15m", "ts": "2026-10-15T20:01:00Z" }]
```

### Alertas
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/alerts` | autenticado | `status`, `severity`, `origin`, `host_id`, `from`, `to`, paginado (orden: severidad desc, fecha desc) |
| GET | `/alerts/summary` | autenticado | `{low, medium, high, critical}` de alertas activas |
| GET | `/alerts/{id}` | autenticado | Detalle con `evidence`, `trend`, `suggested_action` |
| POST | `/alerts/{id}/acknowledge` | infra, admin | Marca `acknowledged` |
| POST | `/alerts/{id}/resolve` | infra, admin | Marca `resolved` |

```json
// GET /alerts/{id}
{
  "id": 42, "host_id": 1, "hostname": "api-01", "origin": "correlation",
  "severity": "high", "status": "active",
  "title": "Degradación progresiva en api-01",
  "situation": "Degradación progresiva del servicio",
  "risk_score": 0.78, "trend": "rising",
  "evidence": [
    {"metric": "cpu_percent", "value": 92, "detail": "92% durante 18 min"},
    {"metric": "mem_percent", "value": 87, "detail": "87% y tendencia ascendente"},
    {"metric": "latency_ms", "value": 620, "detail": "de 180 ms a 620 ms"},
    {"metric": "events_error_count", "value": 37, "detail": "incremento de errores HTTP 5xx"}
  ],
  "suggested_action": "Revisar consumo de recursos, errores de aplicación y conexiones al servicio",
  "occurrences": 3, "first_seen_at": "...", "last_seen_at": "..."
}
```

### Reglas de alerta
| Método | Ruta | Rol |
|---|---|---|
| GET | `/alert-rules` | autenticado |
| POST | `/alert-rules` | admin, infra |
| PATCH | `/alert-rules/{id}` | admin, infra |
| DELETE | `/alert-rules/{id}` | admin, infra |

### Incidentes
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/incidents` | autenticado | Filtros `status`, `severity`, `host_id` |
| POST | `/incidents` | infra, admin | Crear; opcional `alert_ids: []` para vincular |
| GET | `/incidents/{id}` | autenticado | Con alertas vinculadas |
| PATCH | `/incidents/{id}` | infra, admin | Estado, causa raíz, resolución, asignado |

### Dashboard y reportes
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dashboard/overview` | `?host_id&range=1h\|6h\|24h\|7d` → KPIs (cpu/mem/disk/red promedio + sparkline), riesgo global, alertas recientes (5), hosts con estado |
| GET | `/reports/availability` | `from`, `to` → disponibilidad % por host, MTTR de incidentes |
| GET | `/reports/availability.csv` | Exportación |

```json
// GET /dashboard/overview?range=1h
{
  "kpis": {
    "cpu":  {"value": 41.2, "unit": "%",    "trend": [38,40,45,41]},
    "mem":  {"value": 63.0, "unit": "%",    "trend": [...]},
    "disk": {"value": 58.4, "unit": "%",    "trend": [...]},
    "net":  {"value": 1.8,  "unit": "MB/s", "trend": [...]}
  },
  "risk": {"level": "medium", "score": 0.41},
  "recent_alerts": [{"id": 42, "severity": "high", "hostname": "api-01", "title": "...", "first_seen_at": "..."}],
  "hosts": [{"id": 1, "hostname": "api-01", "status": "degraded", "last_seen_at": "...", "risk_level": "high"}]
}
```

## Matriz de permisos (resumen)

| Recurso | admin | infra | developer | analyst | viewer |
|---|---|---|---|---|---|
| Usuarios | CRUD | — | — | — | — |
| Hosts | CRUD | CRU | R | R | R |
| Métricas / eventos | R | R | R | R + export | R (solo dashboard) |
| Predicciones / modelo | R + activar | R | R | R | R (resumen) |
| Alertas | R + ack/resolve | R + ack/resolve | R | R | R |
| Reglas | CRUD | CRUD | R | R | — |
| Incidentes | CRUD | CRUD | R | R | R |
| Reportes | R + export | R + export | — | R + export | R |
