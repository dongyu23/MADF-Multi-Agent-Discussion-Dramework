FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<5" \
    redis httpx aiofiles python-dotenv psycopg2-binary \
    langchain-openai tavily-python

RUN pip install --no-cache-dir git+https://github.com/langchain-ai/deepagents.git#subdirectory=libs/deepagents

COPY backend/ ./backend/
COPY agent_engine/ ./agent_engine/
COPY alembic.ini ./
COPY alembic/ ./alembic/

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
