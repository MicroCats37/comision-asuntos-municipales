FROM python:3.11-slim

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar proyecto
COPY pyproject.toml .
COPY documento_scraper.py .
COPY main.py .

# Instalar dependencias con uv (sin venv, directo al sistema)
RUN uv pip install --system --no-cache -r pyproject.toml

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
