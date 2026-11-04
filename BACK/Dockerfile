FROM python:3.11-slim
WORKDIR /code
ENV PYTHONPATH=/code PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
# Migra la BD y arranca la API (el worker sobrescribe el comando en docker-compose)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
