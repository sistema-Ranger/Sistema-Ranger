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
