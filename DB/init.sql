-- DB/init.sql
-- Solo extensiones: el esquema lo crea Alembic (ADR-07) y el seed lo hace el backend al iniciar.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
