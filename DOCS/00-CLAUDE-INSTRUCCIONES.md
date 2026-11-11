# 00 · Instrucciones para Claude — Proyecto Ranger

> Este archivo es el punto de entrada. Léelo antes que cualquier otro documento del proyecto.

## Qué es Ranger

Sistema web de monitoreo y **predicción de fallos** en infraestructura tecnológica. Recolecta métricas, logs y eventos de hosts, los almacena, detecta anomalías con reglas + Machine Learning, estima riesgo y genera **alertas inteligentes** visibles en un dashboard.

- **Tipo:** Proyecto Final TDS — ITLA (Instituto Tecnológico de Las Américas).
- **Docentes:** Willis Ezequiel Polanco / Eduandy Isabel Cruz.
- **Equipo:** Anyi Rafelina Rodríguez Dotel (2024-0022) · Josué Fondeur Román (2024-0193).
- **Repositorio:** `Anyi2rod/Sistema-Ranger` (GitHub).
- **Período:** 21 sep – 2 dic 2026 (11 semanas, Scrum con sprints semanales).

## Mapa de documentos

| Archivo | Contenido | Úsalo cuando… |
|---|---|---|
| `00-CLAUDE-INSTRUCCIONES.md` | Reglas de trabajo y mapa | Siempre |
| `01-VISION-Y-ALCANCE.md` | Problema, objetivos, usuarios, alcance / fuera de alcance | Decidir si algo entra en el MVP |
| `02-ARQUITECTURA.md` | Capas, contenedores, flujos, decisiones técnicas (ADR) | Diseñar cualquier componente |
| `03-ENTORNO-DESARROLLO.md` | Estructura del repo, Docker Compose, `.env`, comandos | Crear Dockerfiles, configs, scripts |
| `04-MODELO-DE-DATOS.md` | Esquema PostgreSQL (DDL), enums, índices | Escribir `init.sql`, `models.py`, migraciones |
| `05-API-CONTRATOS.md` | Endpoints REST, payloads, códigos de error | Backend (routers/schemas) y cliente del frontend |
| `06-FRONTEND-UI.md` | Pantallas, rutas, componentes, tokens de diseño | Maquetar vistas React |
| `07-ML-Y-ALERTAS.md` | Features, modelos, score de riesgo, motor de alertas | Carpeta `ml/` y lógica de alertas |
| `08-ROADMAP-Y-CRONOGRAMA.md` | Fases, semanas, hitos, responsables, backlog | Planificar o priorizar |
| `09-CONVENCIONES-Y-CALIDAD.md` | Git, commits, estilo de código, pruebas, DoD | Escribir código, PRs y tests |

## Reglas de trabajo

1. **Idioma:** responde en español. Identificadores de código, tablas y endpoints en **inglés** (`hosts`, `metrics`, `/api/v1/alerts`); textos de UI, comentarios de dominio y documentación en español.
2. **Respeta la estructura real del repo** (`BACK/`, `COLLECTOR/`, `DB/`, `DOCS/`, `FRONT/`, `TEST/`, `docker/`, `ml/`). No inventes carpetas raíz nuevas sin proponerlo explícitamente.
3. **Fuente de verdad:** si hay conflicto entre documentos, gana este orden: `04` (datos) → `05` (API) → `02` (arquitectura) → resto. Si detectas una contradicción, señálala y propone qué documento actualizar.
4. **Entrega código listo para pegar:** archivos completos con su ruta como encabezado (`// FRONT/src/pages/Alerts.tsx`), sin `...` ni fragmentos omitidos, salvo que se pida un diff.
5. **Coherencia de contratos:** los nombres de campos del modelo de datos, los schemas Pydantic y los tipos TypeScript deben coincidir exactamente.
6. **Alcance MVP:** no agregues funcionalidades listadas en "Fuera de alcance" (`01`). Si algo es "nice to have", márcalo como `[post-MVP]`.
7. **Cada entrega incluye:** qué archivos se crean/modifican, comando para probarlo y mensaje de commit sugerido (Conventional Commits).
8. **Pruebas:** toda lógica nueva de backend o ML viene con al menos un test `pytest`; componentes con lógica no trivial, con test Vitest.
9. **Sin secretos en código:** todo valor sensible vía variables de entorno (`03`).
10. **Explicaciones breves:** el equipo conoce los conceptos básicos; prioriza implementación sobre teoría.

## Estado actual (actualizar cada semana)

- **Semana actual:** 4 (12–18 oct) — Backend completo: modelos + Alembic, JWT/roles, ingesta, consultas, worker con reglas + z-score y motor de alertas (84 tests, 96 % de cobertura).
- **Hecho:** propuesta, estructura, entorno Docker (db, backend, worker, collector), mockups, roadmap, API de `05` completa; decisiones en `DECISIONES.md`.
- **Siguiente hito:** 25 oct — conectar el frontend a la API; después, el dataset y el modelo v1 en `ml/` (sem. 6–7).
