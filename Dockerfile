# ── 1. Build the React app ───────────────────────────────────
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/wisemarket/package.json frontend/wisemarket/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/wisemarket/ ./
RUN npm run build

# ── 2. Python API that also serves the built app ─────────────
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data/ontology ./data/ontology
COPY --from=web /web/dist ./frontend/wisemarket/dist

EXPOSE 8000
# Hosting platforms set $PORT; --proxy-headers keeps real client IPs for rate limiting
CMD uvicorn backend.api.serve:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips="*"
