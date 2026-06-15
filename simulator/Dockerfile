# ============================================================
# 多阶段构建 - 纺车模拟器
# Stage 1: builder - 编译依赖
# Stage 2: runtime - 运行镜像
# ============================================================

# ---------- Stage 1: 编译依赖 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# ---------- Stage 2: 运行镜像 ----------
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r simuser \
 && useradd -r -g simuser simuser \
 && mkdir -p /app \
 && chown -R simuser:simuser /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

RUN chown -R simuser:simuser /app
USER simuser

EXPOSE 5020

# 默认启动参数，可通过 docker-compose 覆盖
# 支持：--water-mode, --yarn-spec, --modbus-host, --modbus-port, --report-interval
CMD ["python", "simulator.py"]
