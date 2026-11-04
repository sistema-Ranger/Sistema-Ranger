# 09 · Convenciones, calidad y pruebas

## Git

| Rama | Propósito | Se fusiona en |
|---|---|---|
| `main` | Estable, entregable | — |
| `develop` | Integración | `main` al cerrar cada fase |
| `feature/<nombre>` | Funcionalidad (`feature/collector-cpu`) | `develop` |
| `fix/<nombre>` | Corrección | `develop` |

- Nadie trabaja directo sobre `main`. PR hacia `develop` revisado por el otro integrante.
- PR pequeño (idealmente < 400 líneas), descripción con: qué, por qué, cómo probar, capturas si es UI.

### Conventional Commits

`tipo(alcance): descripción en minúsculas`

| Tipo | Ejemplo |
|---|---|
| feat | `feat(collector): enviar uso de ram` |
| fix | `fix(api): validar rango de fechas` |
| docs | `docs: guía del entorno de desarrollo` |
| test | `test(api): prueba del endpoint /metrics` |
| refactor | `refactor(back): separar routers` |
| chore | `chore(docker): agregar healthcheck a db` |
| ci | `ci: ejecutar pytest en pull requests` |

Alcances: `api`, `back`, `worker`, `db`, `collector`, `ml`, `front`, `docker`, `ci`, `docs`.

## Estilo de código

**Python (BACK, COLLECTOR, ml)**
- Formato `ruff format`, lint `ruff check`, tipado con hints en todas las funciones públicas.
- SQLAlchemy 2.x estilo `Mapped[...]` / `mapped_column`.
- Pydantic v2: `XxxCreate`, `XxxUpdate`, `XxxRead` (`model_config = ConfigDict(from_attributes=True)`).
- Routers delgados → lógica en `services/`. Nada de SQL crudo en routers.
- Configuración solo vía `config.Settings`.
- Logging con `logging` (no `print`), nivel según `APP_ENV`.

**TypeScript (FRONT)**
- `strict: true`, ESLint + Prettier.
- Componentes funcionales, `PascalCase.tsx`; hooks `useXxx.ts`.
- Sin `any`; tipos de API en `src/types/api.ts`.
- Tailwind para estilos; tokens en `index.css` (ver `06`).

**Nombres**
- Código/BD/API en inglés; UI y documentación en español.
- Endpoints en plural y kebab-case (`/alert-rules`).

## Pruebas

| Nivel | Herramienta | Ubicación | Mínimo |
|---|---|---|---|
| Unitarias backend | pytest | `TEST/back/` | services y security |
| API | pytest + httpx `TestClient` con BD de prueba | `TEST/api/` | cada router: happy path + 401/403 + 422 |
| ML | pytest | `TEST/ml/` | features, risk, contrato del modelo |
| Integración | pytest + docker compose | `TEST/integration/` | ingest → worker → alerta |
| Frontend | Vitest + Testing Library | `FRONT/src/**/*.test.tsx` | componentes con lógica, hooks |
| E2E | Playwright | `FRONT/e2e/` | login, dashboard carga, ack de alerta, filtros de logs |
| Rendimiento | script/locust básico | `TEST/perf/` | ingest de 10 hosts × 1 lectura/s sin errores |

Cobertura objetivo: ≥ 70 % en `BACK/app/services` y `ml/src`.

### Prueba base existente

```python
# TEST/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

## CI (GitHub Actions — `.github/workflows/ci.yml`)

En cada PR a `develop`/`main`:
1. **backend:** setup Python 3.11 → `pip install -r BACK/requirements.txt` → `ruff check` → `pytest` (servicio `postgres:16-alpine`).
2. **frontend:** setup Node 20 → `npm ci` → `npm run lint` → `npm run test -- --run` → `npm run build`.
3. **docker:** `docker compose build` para validar Dockerfiles.

## Seguridad (checklist MVP)

- [ ] Contraseñas con bcrypt; JWT con expiración.
- [ ] Dependencias de rol en cada endpoint protegido.
- [ ] API key obligatoria en `/ingest/*`.
- [ ] Validación estricta de entrada (Pydantic) y límites de tamaño de lote (máx. 500 lecturas/eventos).
- [ ] CORS restringido a `CORS_ORIGINS`.
- [ ] Secretos solo en `.env` (no versionado) y secretos distintos en prod.
- [ ] Sin SQL concatenado (solo ORM/parámetros).

## Definition of Done

Una historia está terminada cuando:
1. Código en `develop` vía PR aprobado.
2. Tests nuevos pasan y CI verde.
3. Endpoint visible y documentado en Swagger (descripción + ejemplo).
4. UI con estados loading / vacío / error.
5. Documentación `.md` afectada actualizada (`04`, `05`, `06`…).
6. Probado con `docker compose up --build` desde cero.

## Entregables de documentación final

- `README.md` (qué es, cómo levantar, capturas).
- `DOCS/` con estos archivos + diagramas C4/UML (Mermaid).
- Manual de usuario (PDF/Markdown) por rol.
- Informe del modelo: dataset, features, métricas, matriz de confusión, lead time, limitaciones.
- Reporte de pruebas con evidencias.
- Presentación y guion de demo (escenario `degradation`).
