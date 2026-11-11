# 03 · Entorno de desarrollo

## Requisitos

| Herramienta | Versión mínima | Obligatoria |
|---|---|---|
| Git | 2.40 | Sí |
| Docker Desktop / Engine | 24 + Compose v2 | Sí |
| Python | 3.11 | Recomendada (fuera de Docker) |
| Node.js + npm | 20 LTS | Recomendada (fuera de Docker) |
| VS Code (Python, ESLint, Docker) | Última | Recomendada |
| pgAdmin / DBeaver | Última | Opcional |

En Windows: Docker Desktop con backend WSL 2.

## Estructura del repositorio (real)

```
Sistema-Ranger/
├── BACK/                 # API REST (FastAPI) + worker
│   ├── app/              # ver 02-ARQUITECTURA.md
│   ├── alembic/          # migraciones (ADR-07)
│   ├── requirements.txt
│   └── Dockerfile
├── COLLECTOR/            # agente psutil + generador de logs/escenarios
│   ├── collector.py
│   ├── scenarios.py      # inyección de fallos simulados
│   ├── requirements.txt
│   └── Dockerfile
├── DB/
│   └── init.sql          # extensiones + seed mínimo
├── DOCS/                 # estos .md, diagramas, mockups, manual
├── FRONT/                # React + TS + Vite + Tailwind
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── ml/
│   ├── notebooks/
│   ├── data/             # datasets (no versionar grandes; .gitignore)
│   ├── models/           # *.joblib + metadata.json
│   └── src/              # features.py, train.py, evaluate.py
├── TEST/                 # pytest (backend, ml, integración)
├── docker/               # prod: compose, nginx
├── .github/workflows/    # CI
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

> Nota: el roadmap menciona `/backend`, `/frontend`… pero las carpetas reales son **en mayúsculas** (`BACK`, `FRONT`, `COLLECTOR`, `DB`, `DOCS`, `TEST`) y `ml`, `docker` en minúsculas. Usar siempre los nombres reales.

## Servicios

| Servicio | Contenedor | Imagen base | Puerto |
|---|---|---|---|
| Base de datos | `ranger-db` | `postgres:16-alpine` | 5432 |
| Backend | `ranger-backend` | `python:3.11-slim` | 8000 |
| Worker | `ranger-worker` | misma imagen que backend | — |
| Frontend | `ranger-frontend` | `node:20-alpine` | 5173 |
| Recolector | `ranger-collector` | `python:3.11-slim` | — |

## `.env.example`

```dotenv
# --- PostgreSQL ---
POSTGRES_USER=ranger
POSTGRES_PASSWORD=ranger_dev
POSTGRES_DB=ranger
POSTGRES_PORT=5432

# --- Puertos ---
BACKEND_PORT=8000
FRONTEND_PORT=5173

# --- Backend ---
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
JWT_SECRET=change_me_dev_only
JWT_EXPIRE_MINUTES=480
COLLECTOR_API_KEY=dev_collector_key
ADMIN_EMAIL=admin@ranger.local
ADMIN_PASSWORD=admin123

# --- Worker / ML ---
ANALYSIS_INTERVAL_SECONDS=60
MODEL_DIR=/code/ml/models
ALERT_COOLDOWN_MINUTES=15

# --- Recolector ---
COLLECT_INTERVAL=10
COLLECTOR_HOSTNAME=dev-container
COLLECTOR_SCENARIO=normal   # normal | cpu_spike | memory_leak | disk_fill | error_burst
```

## `docker-compose.yml` (desarrollo)

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: ranger-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./DB/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      retries: 10

  backend:
    build: ./BACK
    container_name: ranger-backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - ./BACK/app:/code/app
      - ./ml:/code/ml
      - ./TEST:/code/TEST
    depends_on:
      db:
        condition: service_healthy

  worker:
    build: ./BACK
    container_name: ranger-worker
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    command: ["python", "-m", "app.worker.scheduler"]
    volumes:
      - ./BACK/app:/code/app
      - ./ml:/code/ml
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./FRONT
    container_name: ranger-frontend
    environment:
      VITE_API_URL: http://localhost:${BACKEND_PORT:-8000}/api/v1
    ports:
      - "${FRONTEND_PORT:-5173}:5173"
    volumes:
      - ./FRONT/src:/app/src
    depends_on:
      - backend

  collector:
    build: ./COLLECTOR
    container_name: ranger-collector
    environment:
      API_URL: http://backend:8000/api/v1
      COLLECTOR_API_KEY: ${COLLECTOR_API_KEY}
      COLLECT_INTERVAL: ${COLLECT_INTERVAL:-10}
      HOSTNAME_OVERRIDE: ${COLLECTOR_HOSTNAME:-dev-container}
      SCENARIO: ${COLLECTOR_SCENARIO:-normal}
    depends_on:
      - backend

volumes:
  pgdata:
```

> Para simular varios hosts: `docker compose up --scale collector=3` no sirve con `container_name`; definir `collector-api01`, `collector-db01`, `collector-web01` con distinto `HOSTNAME_OVERRIDE` y `SCENARIO`.

## Dockerfiles

```dockerfile
# BACK/Dockerfile
FROM python:3.11-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```dockerfile
# FRONT/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

```dockerfile
# COLLECTOR/Dockerfile
FROM python:3.11-slim
WORKDIR /collector
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
CMD ["python", "collector.py"]
```

## Dependencias

| Servicio | Paquetes |
|---|---|
| BACK | fastapi, uvicorn[standard], sqlalchemy>=2, psycopg[binary], pydantic-settings, alembic, python-jose[cryptography], passlib[bcrypt], python-multipart, apscheduler, pandas, numpy, scikit-learn, joblib |
| COLLECTOR | psutil, requests |
| FRONT | react, react-dom, react-router-dom, @tanstack/react-query, axios, recharts, tailwindcss, lucide-react, date-fns, typescript, vite, vitest, @testing-library/react |
| ml | pandas, numpy, scikit-learn, statsmodels, joblib, jupyter, matplotlib |
| TEST | pytest, httpx, pytest-cov |

## Puesta en marcha

```bash
git clone https://github.com/Anyi2rod/Sistema-Ranger.git
cd Sistema-Ranger && git checkout develop
cp .env.example .env
docker compose up --build
```

- Dashboard: http://localhost:5173
- Health: http://localhost:8000/health → `{"status":"ok"}`
- Swagger: http://localhost:8000/docs

## Comandos útiles

| Acción | Comando |
|---|---|
| Segundo plano | `docker compose up -d` |
| Logs de un servicio | `docker compose logs -f backend` |
| Reconstruir tras cambiar deps | `docker compose up --build backend` |
| psql | `docker compose exec db psql -U ranger -d ranger` |
| Shell en contenedor | `docker compose exec backend bash` |
| Migrar BD | `docker compose exec backend alembic upgrade head` |
| Nueva migración | `docker compose exec backend alembic revision --autogenerate -m "msg"` |
| Tests | `docker compose exec backend pytest /code/TEST -v` |
| Reset total BD | `docker compose down -v` |

## Checklist de entorno listo

- [ ] `docker compose ps`: todos `running`, `db` `healthy`.
- [ ] `/health` responde `{"status":"ok"}`.
- [ ] `/docs` muestra Swagger.
- [ ] `localhost:5173` carga el dashboard.
- [ ] `docker compose logs collector` muestra envíos cada 10 s.

## Problemas comunes

| Problema | Solución |
|---|---|
| `port is already allocated` | Cambiar puerto en `.env` o detener el otro servicio |
| Backend no conecta a la BD | Esperar healthcheck o `docker compose restart backend` |
| Cambios en `init.sql` no aplican | `docker compose down -v` (o usar Alembic) |
| Frontend no recarga en Windows | `server.watch.usePolling: true` en `vite.config.ts` o clonar dentro de WSL |
| Error CORS | Agregar origen a `CORS_ORIGINS` |
| Dependencia no encontrada | `docker compose up --build <servicio>` |
