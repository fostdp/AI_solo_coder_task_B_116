#!/usr/bin/env python3
"""
InfluxDB 2.x 初始化脚本：
- 创建原始数据 bucket（spinning-bucket, 保留 7 天）
- 创建 1 分钟降采样 bucket（spinning-downsampled-1m, 保留 30 天）
- 创建 1 小时降采样 bucket（spinning-downsampled-1h, 保留 365 天）
- 创建 Flux Task 完成自动降采样聚合

在 docker-compose 中通过 depends_on 等待 InfluxDB 就绪后执行
"""
import os
import time
import sys
import logging
from influxdb_client import InfluxDBClient, TasksService, OrganizationsService
from influxdb_client.client.write_api import SYNCHRONOUS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("influxdb-init")

# 配置
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", "spinning-token")
INFLUXDB_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG", "spinning-org")
INFLUXDB_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET", "spinning-bucket")

# 降采样桶配置
DOWNSAMPLED_BUCKETS = [
    {
        "name": "spinning-downsampled-1m",
        "retention": 30 * 24 * 3600,  # 30 天
        "description": "1 分钟聚合降采样数据",
    },
    {
        "name": "spinning-downsampled-1h",
        "retention": 365 * 24 * 3600,  # 1 年
        "description": "1 小时聚合降采样数据",
    },
]

# Flux Task 定义 - 1 分钟降采样
FLUX_TASK_1M = """
option task = {{
    name: "downsample_1min",
    every: 1m,
    offset: 30s,
    concurrency: 1,
    retry: 2,
}}

data = from(bucket: "{src_bucket}")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "spindle_data")
    |> keep(columns: ["_time", "_measurement", "spindle_id", "_field", "_value"])

// 均值聚合（转速、张力、捻度、功率）
mean_aggr = data
    |> filter(fn: (r) => r._field =~ /rpm|tension|twist|power/)
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    |> set(key: "_field", value: fn: (r) => r._field + "_mean")
    |> to(bucket: "{dst_bucket}", org: "{org}")

// 最大/最小聚合
extremes = data
    |> filter(fn: (r) => r._field =~ /tension|rpm/)
    |> aggregateWindow(every: 1m, fn: max, createEmpty: false)
    |> set(key: "_field", value: fn: (r) => r._field + "_max")
    |> to(bucket: "{dst_bucket}", org: "{org}")

min_vals = data
    |> filter(fn: (r) => r._field =~ /tension|rpm/)
    |> aggregateWindow(every: 1m, fn: min, createEmpty: false)
    |> set(key: "_field", value: fn: (r) => r._field + "_min")
    |> to(bucket: "{dst_bucket}", org: "{org}")

// 计数（断头次数）
break_counts = data
    |> filter(fn: (r) => r._field == "is_broken")
    |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
    |> set(key: "_field", value: "break_count")
    |> to(bucket: "{dst_bucket}", org: "{org}")
"""

# Flux Task 定义 - 1 小时降采样（从 1 分钟桶再聚合）
FLUX_TASK_1H = """
option task = {{
    name: "downsample_1hour",
    every: 1h,
    offset: 2m,
    concurrency: 1,
    retry: 3,
}}

data = from(bucket: "{src_bucket}")
    |> range(start: -1h)
    |> keep(columns: ["_time", "_measurement", "spindle_id", "_field", "_value"])

mean_aggr = data
    |> filter(fn: (r) => r._field =~ /_mean$/)
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> to(bucket: "{dst_bucket}", org: "{org}")

max_aggr = data
    |> filter(fn: (r) => r._field =~ /_max$/)
    |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
    |> to(bucket: "{dst_bucket}", org: "{org}")

min_aggr = data
    |> filter(fn: (r) => r._field =~ /_min$/)
    |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
    |> to(bucket: "{dst_bucket}", org: "{org}")

sum_aggr = data
    |> filter(fn: (r) => r._field == "break_count")
    |> aggregateWindow(every: 1h, fn: sum, createEmpty: false)
    |> to(bucket: "{dst_bucket}", org: "{org}")
"""


def wait_for_influxdb(max_retries=30, delay=2):
    """等待 InfluxDB 就绪"""
    for i in range(max_retries):
        try:
            with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, timeout=5000) as client:
                if client.ping():
                    logger.info("InfluxDB 已就绪")
                    return True
        except Exception as e:
            logger.info(f"等待 InfluxDB... ({i+1}/{max_retries}) {e}")
        time.sleep(delay)
    logger.error("InfluxDB 连接超时")
    return False


def get_org_id(client):
    """获取组织 ID"""
    org_service = OrganizationsService(client.api_client)
    orgs = org_service.get_orgs(org=INFLUXDB_ORG)
    if not orgs.orgs:
        raise RuntimeError(f"组织 {INFLUXDB_ORG} 不存在")
    return orgs.orgs[0].id


def create_bucket_if_not_exists(client, bucket_config):
    """创建 bucket，如果不存在"""
    from influxdb_client import BucketsService, PostBucketRequest

    bucket_service = BucketsService(client.api_client)
    org_id = get_org_id(client)

    # 检查是否已存在
    existing = bucket_service.get_buckets(name=bucket_config["name"])
    if existing.buckets:
        logger.info(f"Bucket {bucket_config['name']} 已存在，跳过创建")
        return existing.buckets[0].id

    # 创建
    req = PostBucketRequest(
        org_id=org_id,
        name=bucket_config["name"],
        description=bucket_config["description"],
        retention_rules=[{
            "type": "expire",
            "everySeconds": bucket_config["retention"],
            "shardGroupDurationSeconds": min(bucket_config["retention"], 24 * 3600),
        }],
    )
    bucket = bucket_service.post_buckets(post_bucket_request=req)
    logger.info(f"Bucket {bucket_config['name']} 创建成功，ID: {bucket.id}")
    return bucket.id


def create_task_if_not_exists(client, task_name, flux_script):
    """创建 Flux Task，如果不存在（按名称去重）"""
    task_service = TasksService(client.api_client)
    org_id = get_org_id(client)

    # 检查是否已存在同名任务
    existing = task_service.get_tasks(name=task_name, org=INFLUXDB_ORG)
    if existing.tasks:
        logger.info(f"Task {task_name} 已存在（ID: {existing.tasks[0].id}），跳过创建")
        return existing.tasks[0].id

    # 创建任务
    from influxdb_client import TaskCreateRequest

    req = TaskCreateRequest(
        org_id=org_id,
        flux=flux_script,
        description=f"自动降采样任务：{task_name}",
        status="active",
    )
    task = task_service.post_tasks(task_create_request=req)
    logger.info(f"Task {task_name} 创建成功，ID: {task.id}")
    return task.id


def main():
    if not wait_for_influxdb():
        sys.exit(1)

    try:
        with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
            logger.info("=" * 60)
            logger.info("开始初始化 InfluxDB 降采样配置")
            logger.info("=" * 60)

            # 1. 创建降采样 buckets
            bucket_1m_id = create_bucket_if_not_exists(client, DOWNSAMPLED_BUCKETS[0])
            bucket_1h_id = create_bucket_if_not_exists(client, DOWNSAMPLED_BUCKETS[1])

            # 2. 创建 1 分钟降采样 Task
            flux_1m = FLUX_TASK_1M.format(
                src_bucket=INFLUXDB_BUCKET,
                dst_bucket=DOWNSAMPLED_BUCKETS[0]["name"],
                org=INFLUXDB_ORG,
            )
            create_task_if_not_exists(client, "downsample_1min", flux_1m)

            # 3. 创建 1 小时降采样 Task
            flux_1h = FLUX_TASK_1H.format(
                src_bucket=DOWNSAMPLED_BUCKETS[0]["name"],
                dst_bucket=DOWNSAMPLED_BUCKETS[1]["name"],
                org=INFLUXDB_ORG,
            )
            create_task_if_not_exists(client, "downsample_1hour", flux_1h)

            logger.info("=" * 60)
            logger.info("InfluxDB 初始化完成 ✓")
            logger.info(f"  原始桶:       {INFLUXDB_BUCKET} (保留 7 天)")
            logger.info(f"  1 分钟桶:     {DOWNSAMPLED_BUCKETS[0]['name']} (保留 30 天)")
            logger.info(f"  1 小时桶:     {DOWNSAMPLED_BUCKETS[1]['name']} (保留 365 天)")
            logger.info(f"  降采样任务:   downsample_1min / downsample_1hour")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
