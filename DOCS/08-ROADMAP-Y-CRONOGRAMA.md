# 08 · Roadmap, cronograma y responsables

Período: **21 sep – 2 dic 2026** · Scrum adaptado, sprints semanales.

> El roadmap por fases suma más de 11 semanas si se ejecuta en serie; las fases **se solapan** según el calendario de abajo (el calendario manda).

## Calendario por semana

| Sem | Fechas | Actividades | Entregable | Fases |
|---|---|---|---|---|
| 1 | 21–27 sep | Alcance, requisitos, backlog, arquitectura preliminar | Propuesta y backlog ✅ | 1 |
| 2 | 28 sep–4 oct | UX/UI, modelo de datos, repo, CI/CD | Prototipo y modelo de datos ✅ | 1 |
| 3 | 5–11 oct | Registro de hosts, aplicaciones, servicios y usuarios; auth | Módulos maestros | 1, 3 |
| 4 | 12–18 oct | Integración de métricas, eventos y logs; almacenamiento | Recolección de datos | 2, 3, 4 |
| 5 | 19–25 oct | Dashboards, filtros, umbrales, alertas básicas (reglas) | Observabilidad inicial | 4, 6, 7 |
| 6 | 26 oct–1 nov | ETL, históricos, normalización, calidad de datos; generación de escenarios | Datos históricos integrados | 5, 7 |
| 7 | 2–8 nov | Detección de anomalías + modelo de riesgo v1 | Modelo analítico inicial | 5 |
| 8 | 9–15 nov | Correlación, alertas inteligentes, priorización | Motor de alertas | 5, 6 |
| 9 | 16–22 nov | Pruebas integración, rendimiento, seguridad; correcciones | MVP integrado | 8 |
| 10 | 23–29 nov | Documentación, manual, presentación, ensayo de demo; despliegue | Documentación final | 9 |
| 11 | 30 nov–2 dic | Entrega, demo, retrospectiva | Proyecto final | — |

## Hitos

- ✅ 27 sep — propuesta y backlog inicial.
- 11 oct — arquitectura, BD y recolección inicial listas.
- **25 oct — observabilidad y alertas básicas funcionando.**
- 8 nov — detección de anomalías / modelo predictivo implementado.
- 22 nov — MVP integrado y probado.
- 2 dic — entrega final y demostración.

## Fases (detalle técnico)

| Fase | Objetivo | Tareas clave |
|---|---|---|
| 1 Inicialización | Entorno con un comando | Repo, ramas, estructura, Compose, README |
| 2 Monitoreo | Datos reales del host | Recolector psutil: CPU, RAM, disco, red; buffer local si la API cae; envío a intervalos configurables; escenarios |
| 3 Backend | Recibir, guardar, exponer | API, modelos, Alembic, auth JWT, hosts, ingest, consultas históricas por rango y host |
| 4 Logs | Logs → eventos útiles | Captura, clasificación info/warning/error/critical, fingerprint, búsqueda y filtros |
| 5 ML | Anticipar fallos | Dataset, limpieza, features, IsolationForest + clasificador, evaluación P/R/F1, predicciones y riesgo |
| 6 Alertas | Avisar lo relevante | Severidades, reglas + modelo, dedup/cooldown, registro y UI |
| 7 Dashboard | Todo en un lugar | General, tiempo real, predicciones, alertas, historial, incidentes |
| 8 Pruebas | Estabilidad | Unitarias, API, modelo, integración, E2E (Playwright), carga básica |
| 9 Despliegue | Producción | Compose prod, Nginx, secretos, docs de instalación |

## Responsables

| Área | Anyi | Josué |
|---|---|---|
| Liderazgo / Backend / IA | **Responsable**: arquitectura, API, lógica, procesamiento de métricas y logs, modelo predictivo, BD | — |
| Frontend / UI-UX / DevOps / QA | — | **Responsable**: interfaz, dashboards, visualización, Docker, CI/CD, pruebas, documentación |
| Base de datos | Diseño y consultas PostgreSQL | Apoyo en integración y pruebas |
| Analítica / IA | Anomalías y predicción | Apoyo en visualización de resultados |
| Documentación | Apoyo | Responsable principal |
| Presentación | Ambos | Ambos |

## Backlog priorizado (MVP)

Formato: `ID · Historia · Responsable · Semana`

**Épica A — Base**
- A1 · Como admin inicio sesión con JWT · Anyi · S3
- A2 · Como admin gestiono usuarios y roles · Anyi (API) / Josué (UI) · S3
- A3 · Como infra registro y edito hosts por entorno/área · Anyi / Josué · S3

**Épica B — Recolección**
- B1 · El recolector se registra y envía métricas cada N s · Anyi · S4
- B2 · El recolector envía logs/eventos y guarda buffer si la API no responde · Anyi · S4
- B3 · Escenarios de fallo inyectables por variable de entorno · Anyi · S4–S6

**Épica C — Observabilidad**
- C1 · Dashboard general con KPIs, gráfica, alertas recientes y hosts · Josué · S5
- C2 · Métricas en tiempo real con intervalo y pausa · Josué · S5
- C3 · Logs y eventos con búsqueda, filtros y paginación · Josué · S5
- C4 · Historial agregado + exportar CSV · Josué (UI) / Anyi (API) · S6

**Épica D — Inteligencia**
- D1 · Reglas de umbral configurables generan alertas · Anyi · S5
- D2 · Pipeline de features compartido · Anyi · S6
- D3 · IsolationForest + clasificador entrenados y registrados · Anyi · S7
- D4 · Worker calcula riesgo por host cada minuto · Anyi · S7
- D5 · Pantalla Predicciones con evaluación del modelo · Josué · S7–S8
- D6 · Correlación + alertas con evidencia y acción sugerida · Anyi · S8
- D7 · Dedup, cooldown, escalado, autorresolución · Anyi · S8

**Épica E — Gestión**
- E1 · Alertas: ack/resolver, drawer de detalle, reglas desde UI · Josué · S8
- E2 · Incidentes vinculados a alertas · Josué / Anyi · S8–S9
- E3 · Reporte de disponibilidad + exportación · Anyi / Josué · S9

**Épica F — Calidad y entrega**
- F1 · CI: lint + tests backend y frontend en cada PR · Josué · S3 (continuo)
- F2 · E2E Playwright de flujos críticos · Josué · S9
- F3 · Compose prod + Nginx · Josué · S10
- F4 · Manual de usuario, doc técnica, informe del modelo, presentación · Josué / Anyi · S10

**Post-MVP:** Prometheus/Grafana como fuente alternativa, Celery + Redis, notificaciones email/Slack, retención con agregados horarios, multiempresa.
