# Gunicorn 配置 - 用于 FastAPI 生产环境
import multiprocessing
import os

# 监听地址
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Worker 进程数：CPU 核数 * 2 + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# 使用 Uvicorn Worker（ASGI）
worker_class = "uvicorn.workers.UvicornWorker"

# 每个 Worker 的线程数
threads = int(os.getenv("GUNICORN_THREADS", 2))

# 请求超时（秒）- GA 优化可能需要较长时间
timeout = int(os.getenv("GUNICORN_TIMEOUT", 600))

# 优雅关闭超时
graceful_timeout = 30

# 保活
keepalive = 5

# 日志
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# 最大请求数（自动重启防内存泄漏）
max_requests = 1000
max_requests_jitter = 100

# 预加载应用（减少内存开销）
preload_app = True
