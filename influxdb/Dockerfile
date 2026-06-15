# InfluxDB 初始化容器（一次性作业）
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir influxdb-client==1.37.0

COPY init_influxdb.py .

ENTRYPOINT ["python", "init_influxdb.py"]
