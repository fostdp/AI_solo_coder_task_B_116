# ============================================================
# 多阶段构建 - 后端 Python 服务
# Stage 1: builder - 编译依赖
# Stage 2: runtime - 运行镜像（仅含 .venv + 源码）
# ============================================================

# ---------- Stage 1: 编译依赖 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

# 安装编译依赖（仅在 builder 阶段需要，运行镜像不包含）
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libatlas-base-dev \
        gfortran \
 && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 安装 Python 依赖
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

# 仅安装运行时必需的系统库（不包含编译工具，减小镜像体积）
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libgomp1 \
        libatlas3-base \
        curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r appuser \
 && useradd -r -g appuser appuser \
 && mkdir -p /app \
 && chown -R appuser:appuser /app

# 从 builder 阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源码
COPY . .

# 权限
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 默认启动：API 网关（gunicorn + uvicorn worker）
# 微服务通过 docker-compose command 覆盖为 python -m services.xxx
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
