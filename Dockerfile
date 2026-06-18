# ── Builder stage ──
FROM python:3.11-slim AS builder
WORKDIR /build
COPY . .
RUN pip install --no-cache-dir build && python -m build

# ── Runtime stage ──
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl && \
    adduser --disabled-password --gecos "" appuser
USER appuser
ENTRYPOINT ["daily-briefing"]
