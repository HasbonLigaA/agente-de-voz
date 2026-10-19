FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY scripts/docker-entry.sh /docker-entry.sh
RUN chmod +x /docker-entry.sh

ENV PYTHONUNBUFFERED=1
ENV PORT=8767
ENV TLS_CERT_PATH=/certs/fullchain.pem
ENV TLS_KEY_PATH=/certs/key.pem

EXPOSE 8767 8768

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f "http://127.0.0.1:${PORT}/api/health" || exit 1

ENTRYPOINT ["/docker-entry.sh"]
