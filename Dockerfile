FROM python:3.12-slim

WORKDIR /app

# Install system curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .env.example ./
COPY vantage ./vantage
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "vantage.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
