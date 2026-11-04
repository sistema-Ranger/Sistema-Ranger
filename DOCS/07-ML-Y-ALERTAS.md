# 07 · Machine Learning, riesgo y motor de alertas

## Visión general

Ranger combina tres señales por host en cada ciclo (60 s):

1. **Reglas de umbral** configurables (`alert_rules`).
2. **Detección de anomalías** no supervisada → `anomaly_score` (0–1).
3. **Clasificador de fallo** supervisado → `failure_probability` (0–1) dentro de un horizonte H.

Las tres se combinan en un `risk_score` y se correlacionan con eventos para producir alertas con evidencia.

## 1. Datos y generación de escenarios

Como no hay infraestructura productiva, el dataset se construye con **hosts simulados** (contenedores con el recolector) y **inyección de fallos controlada** (`COLLECTOR/scenarios.py`):

| Escenario | Cómo se simula | Firma esperada |
|---|---|---|
| `normal` | Carga base con ruido + ciclo diario sintético | Sin incidente |
| `cpu_spike` | Bucle de cálculo / `stress-ng --cpu` | CPU > 90 % sostenido, latencia ↑ |
| `memory_leak` | Proceso que asigna memoria gradualmente | RAM con pendiente positiva → OOM |
| `disk_fill` | Escritura progresiva de archivo | Disco libre ↓ hasta < 5 % |
| `error_burst` | Generador de logs 5xx/timeouts | `events` error/critical ↑, error_rate ↑ |
| `degradation` | Combinación memoria + latencia + errores | Caso de la alerta ejemplo |

Cada escenario registra en el log del recolector un evento `critical` con `source="scenario"` y `attributes.failure=true` en el instante de "caída" → eso define la **etiqueta**.

Volumen objetivo: ≥ 3 hosts × varios días de lecturas cada 10 s (o acelerar generando históricos sintéticos con `ml/src/synth.py` a partir de los mismos generadores).

## 2. Preparación (ETL)

`ml/src/features.py` — misma función usada en entrenamiento y en el worker (evitar *training/serving skew*).

1. Leer `metrics` y `events` por host.
2. Remuestrear a **1 minuto** (`resample('1min').mean()`), forward-fill máx. 2 min; huecos mayores → `is_available=0`.
3. Recortar outliers físicamente imposibles (CPU > 100, valores negativos).
4. Conteos de eventos por minuto y nivel.

### Features (por host y minuto)

| Grupo | Features |
|---|---|
| Nivel actual | `cpu_percent`, `mem_percent`, `disk_percent`, `net_recv_bps`, `net_sent_bps`, `latency_ms`, `error_rate` |
| Rolling (5/15/60 min) | `mean`, `std`, `max` de CPU, RAM, latencia |
| Tendencia | `slope_15m`, `slope_60m` (regresión lineal) de RAM, disco, latencia |
| Desviación | `zscore_60m` de CPU, RAM, latencia respecto a su propia media/std de 24 h |
| Eventos | `err_count_5m`, `crit_count_5m`, `warn_count_15m`, `distinct_fingerprints_15m` |
| Disponibilidad | `downtime_minutes_60m` |
| Contexto | `hour_of_day` (sin/cos) |

Escalado: `StandardScaler` dentro de un `Pipeline` de scikit-learn (se guarda junto al modelo).

### Etiqueta

`y = 1` si ocurre un fallo (`attributes.failure=true` o host `down` ≥ 2 min) en los **próximos H minutos**; H por defecto **30 min** (configurable: "horizonte configurable según disponibilidad de datos"). Las filas posteriores al fallo hasta recuperación se excluyen.

## 3. Modelos

| Componente | Algoritmo | Salida |
|---|---|---|
| Anomalías | `IsolationForest(contamination≈0.02)` entrenado solo con datos `normal` | `anomaly_score` = score normalizado a 0–1; `is_anomaly` si > p98 |
| Riesgo de fallo | `RandomForestClassifier(class_weight="balanced")` (alternativa: `GradientBoostingClassifier`, `LogisticRegression` como baseline) | `failure_probability` |
| Tendencia (apoyo) | Regresión lineal / `statsmodels` Holt para extrapolar RAM/disco | "Disco lleno en ~X min" para la evidencia |

### Evaluación

- **Split temporal** (sin shuffle): entrenar con los primeros 70 % de días, validar 15 %, test 15 %. Alternativa: `TimeSeriesSplit`.
- Métricas: **precision, recall, F1** (clase positiva), ROC-AUC, matriz de confusión; reportar también **lead time** medio (minutos de anticipación entre la primera alerta y el fallo).
- Comparar contra baseline de solo reglas.
- Umbral de decisión elegido en validación priorizando recall ≥ 0.8 con precision aceptable.
- Guardar en `ml/models/ranger-risk-<version>.joblib` + `metadata.json` y registrar en `model_registry` (`scripts/register_model.py`).

## 4. Score de riesgo

```
rule_signal = máx. severidad de reglas activas del host normalizada  (low .25, medium .5, high .75, critical 1)
risk_score  = 0.45 * failure_probability + 0.35 * anomaly_score + 0.20 * rule_signal
```

| risk_score | risk_level |
|---|---|
| < 0.30 | low (Bajo) |
| 0.30 – 0.59 | medium (Medio) |
| 0.60 – 0.79 | high (Alto) |
| ≥ 0.80 | critical (Crítico) |

Ajuste por contexto: +1 nivel si `environment='prod'` y el riesgo se mantiene ≥ 3 ciclos seguidos (frecuencia/duración).

`top_factor`: feature con mayor contribución (importancia × |z-score| actual) — se muestra en "Factor principal".

Sin modelo entrenado aún → el worker opera solo con reglas + z-score estadístico (`anomaly_score = min(1, max|z|/4)`), así las alertas básicas funcionan desde la semana 5.

## 5. Correlación

Para cada host con señal en el ciclo:

1. Ventana ±5 min alrededor del momento actual.
2. Adjuntar como evidencia: métricas fuera de rango, pendiente, eventos `error/critical` agrupados por `fingerprint` (top 3).
3. **Cuello de botella** (reglas heurísticas):
   - CPU alta + latencia ↑ → "Saturación de CPU".
   - RAM pendiente + errores de memoria/OOM → "Posible fuga de memoria".
   - Latencia ↑ + error_rate ↑ con CPU/RAM normales → "Dependencia externa / conexiones".
   - Disco libre ↓ con pendiente → "Saturación de almacenamiento (ETA X min)".
4. Si hay señales en ≥ 2 hosts del mismo `area` en la misma ventana → alerta `origin='correlation'` a nivel de área.

## 6. Motor de alertas (`BACK/app/services/alert_engine.py`)

```
para cada host activo:
    señales = evaluar_reglas(host) + evaluar_modelo(host)
    si no hay señales: resolver automáticamente alertas activas del host tras 3 ciclos limpios
    para cada señal:
        dedup_key = f"{host_id}:{origin}:{rule_id or metric}"
        si existe alerta no resuelta con dedup_key:
            occurrences += 1; last_seen_at = now
            si severidad nueva > actual: escalar severidad
        si no, y no se resolvió una igual hace < ALERT_COOLDOWN_MINUTES:
            crear alerta con title, situation, evidence, trend, risk_score, suggested_action
```

- **Priorización** en listados: `severity` desc → `risk_score` desc → `last_seen_at` desc.
- **Reducción de ruido:** dedup + cooldown + duración mínima (`duration_minutes`) + autorresolución.
- **Notificación:** in-app (badge en sidebar de Alertas + toast en el dashboard por polling). Email/Slack = `[post-MVP]`.

### Acciones sugeridas (plantillas)

| Situación | Acción sugerida |
|---|---|
| Saturación de CPU | Revisar procesos con mayor consumo y picos de tráfico; evaluar escalar recursos |
| Posible fuga de memoria | Revisar consumo por proceso, reiniciar servicio de forma controlada y analizar heap |
| Saturación de almacenamiento | Liberar espacio (logs, temporales), revisar rotación de logs, ampliar volumen |
| Ráfaga de errores | Revisar logs de la aplicación y despliegues recientes; validar dependencias |
| Degradación progresiva | Revisar consumo de recursos, errores de aplicación y conexiones al servicio |

## 7. Worker (`BACK/app/worker/`)

- `scheduler.py`: APScheduler `BlockingScheduler`, job `analyze_all_hosts` cada `ANALYSIS_INTERVAL_SECONDS`, job diario `cleanup`.
- Carga el modelo activo de `model_registry` al iniciar y lo recarga si cambia `is_active`.
- Cada ciclo: features → predicción → `INSERT predictions` → motor de alertas → actualizar `hosts.status` (`down` si `last_seen_at` > 3 × intervalo).
- Debe tolerar fallos por host (try/except por host, log y seguir).

## 8. Pruebas específicas

- `test_features.py`: slopes y rolling con series conocidas.
- `test_risk.py`: mapeo score→nivel y fórmula.
- `test_alert_engine.py`: dedup, cooldown, escalado, autorresolución.
- `test_model_contract.py`: el artefacto carga y produce probas en [0,1] con el vector de features esperado.
- Escenario E2E: levantar `collector` con `SCENARIO=memory_leak` → verificar que aparece alerta `high`/`critical` antes del evento de fallo (lead time > 0).
