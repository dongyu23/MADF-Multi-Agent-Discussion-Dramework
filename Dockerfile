# ── Stage 1: Build main frontend ──
FROM node:22-alpine AS build-frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Build audit frontend ──
FROM node:22-alpine AS build-audit-frontend
WORKDIR /app
COPY audit-frontend/package.json audit-frontend/package-lock.json ./
RUN npm install
COPY audit-frontend/ ./
RUN npm run build

# ── Stage 3: Python + runtime ──
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git nginx supervisor curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<5" \
    redis httpx aiofiles python-dotenv psycopg2-binary \
    langchain-openai tavily-python supervisor

RUN pip install --no-cache-dir git+https://github.com/langchain-ai/deepagents.git#subdirectory=libs/deepagents

COPY backend/ ./backend/
COPY audit_backend/ ./audit_backend/
COPY agent_engine/ ./agent_engine/
COPY alembic.ini ./
COPY alembic/ ./alembic/

COPY --from=build-frontend /app/dist /usr/share/nginx/html
COPY --from=build-audit-frontend /app/dist /usr/share/nginx/html/audit

# Supervisor config
COPY <<'SUPERVISOR' /etc/supervisor/conf.d/madf.conf
[supervisord]
nodaemon=true
user=root

[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:backend]
command=uvicorn backend.main:app --host 127.0.0.1 --port 8000
directory=/app
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:audit-backend]
command=uvicorn audit_backend.main:app --host 127.0.0.1 --port 8001
directory=/app
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
SUPERVISOR

# Nginx config
COPY <<'NGINX' /etc/nginx/sites-available/default
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        proxy_read_timeout 180s;
    }

    location /audit/api/ {
        rewrite ^/audit(/api/.*)$ $1 break;
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_read_timeout 180s;
    }

    location /audit {
        alias /usr/share/nginx/html/audit;
        try_files $uri $uri/ /audit/index.html;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

EXPOSE 80

ENTRYPOINT ["sh", "-c", "alembic upgrade head && exec supervisord -c /etc/supervisor/conf.d/madf.conf"]
