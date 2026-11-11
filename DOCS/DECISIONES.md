# Decisiones y contradicciones detectadas (backend)

Registro de decisiones tomadas durante la implementación. Prioridad aplicada: `04` → `05` → `02` → resto.

| # | Etapa | Tema | Decisión | Doc a actualizar |
|---|---|---|---|---|
| D-01 | 1 | Hashing | Se usa `bcrypt` directamente en lugar de `passlib[bcrypt]`: passlib está sin mantenimiento y falla con bcrypt ≥ 4.1. | `03` (dependencias) |
| D-02 | 1 | Esquema | ADR-07 pasa a **aceptada**: Alembic crea el esquema; `DB/init.sql` solo crea `pg_trgm`. El contenedor `backend` ejecuta `alembic upgrade head` antes de `uvicorn`. | `02`, `03` |
| D-03 | 1 | Compose | Se monta también `./BACK/alembic:/code/alembic` para generar migraciones desde el contenedor. Los servicios `frontend` y `collector` se agregan cuando existan sus Dockerfiles. | `03` |
| D-04 | 1 | Tests | Los tests usan la BD `<POSTGRES_DB>_test` (o `TEST_DATABASE_URL`), recreada y migrada con Alembic en cada sesión de pytest; las tablas se truncan tras cada test. | `09` |
| D-05 | 1 | Escenarios | `07` lista el escenario `degradation`, que no aparece en `.env.example` de `03`; se añadió al comentario. | `03` |
| D-06 | 1 | Errores 422 | Los errores de schema conservan `detail` como lista de Pydantic y agregan `code: "VALIDATION_ERROR"`. | `05` |
| D-07 | 3 | Listas de hosts | `GET /hosts` devuelve el formato paginado de `05` (`size` por defecto 100, máx. 500) y acepta `is_active` como filtro extra. | `05` |
| D-08 | 3 | Ingesta sin registro | `/ingest/metrics` y `/ingest/events` responden `404 HOST_NOT_FOUND` si el hostname no se registró; el recolector se vuelve a registrar automáticamente. | `05` |
| D-09 | 3 | `last_seen_at` / `status` | `last_seen_at` = hora de recepción en el servidor (inmune a relojes desfasados y a lotes del buffer). La ingesta solo marca `up`/`down` (por `is_available`); `degraded` lo asigna el worker según el riesgo. | `05`, `07` |
| D-10 | 3 | Fingerprint | `fingerprint` = SHA-256 de `source` + mensaje normalizado (minúsculas; números, IPs, UUIDs y hex reemplazados). | `04` |
| D-11 | 3 | Recolector | Los escenarios modifican la lectura real de psutil (no estresan la máquina). `SCENARIO_RAMP_MINUTES` (30 por defecto) controla cuánto tarda en llegar al fallo; después simula 3 min de caída. `COLLECTOR/` se monta en solo lectura en `backend` para testear `scenarios.py`. | `03`, `07` |
| D-12 | 4 | Permisos de reglas | `05` dice `GET /alert-rules` = "autenticado", pero su matriz dice viewer "—". Se aplica la matriz: viewer recibe 403. | `05` |
| D-13 | 4 | Fechas `from`/`to` | Aceptan ISO-8601 (sin zona → UTC) o expresiones relativas `now`, `now-15m`, `now-6h`, `now-7d` (lo que pide `06` en Métricas). `from > to` → `400 INVALID_RANGE`; fecha inválida → `422 INVALID_DATE`. | `05` |
| D-14 | 4 | `/events/summary` | Aplica los mismos filtros que `/events` **excepto `level`**, para que los 4 contadores sigan teniendo sentido cuando hay un chip de nivel activo. | `05` |
| D-15 | 4 | `/dashboard/overview` | Campos adicionales: `series` (`[{ts, cpu, mem, disk, net}]`, 30 puntos) para la gráfica "Uso de recursos", `status` en `recent_alerts` y `display_name` en `hosts`. `risk` = peor última predicción entre hosts; `{level: null, score: null}` si aún no hay predicciones. Red en MB/s = (enviados + recibidos) / 10^6. | `05`, `06` |
| D-16 | 4 | `/alerts/summary` | Cuenta solo `status = active` (acepta `host_id` opcional). Orden de `/alerts`: severidad → `risk_score` → `last_seen_at` (`07`). | `05` |
| D-17 | 4 | Reportes | `/reports/availability` → `{from, to, hosts:[{host_id, hostname, availability_pct, samples, incidents_closed, mttr_minutes}], incidents_closed, mttr_minutes}`; rango por defecto 7 días. CSV solo para admin/infra/analyst. | `05` |
| D-18 | 4 | Incidentes | Si no se envía `host_id` y todas las `alert_ids` son del mismo host, se usa ese host. Pasar a `resolved`/`closed` llena `closed_at`; reabrir lo limpia. `DELETE /alert-rules/{id}` responde 204. | `05` |
| D-19 | 5 | Riesgo sin modelo | Mientras no haya clasificador, `failure_probability = NULL` y los pesos de `07` se renormalizan: `risk = (0.35·anomalía + 0.20·reglas) / 0.55`. Con modelo se usa la fórmula original. | `07` |
| D-20 | 5 | `zscore_60m` | = (valor actual − media 24 h) / std 24 h, con un mínimo de 60 muestras por minuto. Un host nuevo tiene anomalía 0 hasta acumular 1 h de historial (relevante para ensayar la demo). | `07` |
| D-21 | 5 | Reglas con duración | Métricas: la condición debe cumplirse en **todos** los minutos de los últimos `duration_minutes` (mín. 1). `events_error_count`: errores/critical en los últimos `max(duration, 5)` min. `risk_score`: el valor actual y las predicciones de la ventana. | `07` |
| D-22 | 5 | Señales | Origen `model` si `risk_level ≥ high` y no se disparó una regla `risk_score` (evita duplicados). Origen `correlation` por host si hay reglas de ≥ 2 categorías (CPU, RAM, disco, latencia, errores), con +1 de severidad si son ≥ 3; y por área si ≥ 2 hosts del mismo `area` tienen señales en el ciclo (una alerta por host, `dedup_key = host:correlation:area:<área>`). | `07` |
| D-23 | 5 | Autorresolución | Se resuelve cada alerta cuya señal no se ve desde 2.5 × `ANALYSIS_INTERVAL_SECONDS` (= al 3.er ciclo limpio). Es por alerta, no por host. | `07` |
| D-24 | 5 | Estado del host | Worker: `down` si `last_seen_at` > 3 × `COLLECT_INTERVAL` o la última lectura no está disponible; `degraded` si el riesgo es alto/crítico; si no, `up`. Ajuste por contexto: +1 nivel en `prod` si el riesgo ≥ medio se sostiene 3 ciclos. | `07` |
| D-25 | 5 | Predicciones | `/predictions/latest` y `/predictions` → admin/infra/developer/analyst. Viewer solo `/predictions/summary` y `/models/active` (matriz de `05`; `06` daba la página completa a todos). `/models/active` responde `null` si no hay modelo. `/predictions/summary` agrega `risk_score`. | `05`, `06` |
| D-26 | 5 | Artefacto del modelo | `.joblib` = dict `{features, classifier, anomaly_model?, anomaly_bounds?, anomaly_threshold?, feature_means?, feature_stds?}` (ver `BACK/app/worker/model.py`). Si falla la carga, se usa el fallback z-score. Job diario `cleanup` borra predicciones con más de 30 días. | `07` |
| D-27 | 5 | `ml/` en contenedores | El backend y el worker importan `ml.src.features` desde el volumen `./ml:/code/ml`. Para producción (Fase 9) hay que copiar `ml/` en la imagen (build context en la raíz). | `03` |
