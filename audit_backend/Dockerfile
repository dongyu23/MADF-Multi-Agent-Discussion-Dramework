FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<5" redis httpx python-dotenv psycopg2-binary
COPY audit_backend/ ./audit_backend/
EXPOSE 8001
CMD ["uvicorn", "audit_backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
