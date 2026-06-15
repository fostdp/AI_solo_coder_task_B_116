# ============================================================
# 前端多阶段构建
# Stage 1: compressor - 预 gzip 压缩所有静态文件
# Stage 2: nginx - 提供静态服务 + API/WS 反向代理
# ============================================================

# ---------- Stage 1: 预压缩 ----------
FROM alpine:3.19 AS compressor

WORKDIR /app

# 安装 gzip
RUN apk add --no-cache gzip

# 复制前端静态文件（路径相对于 docker build context = 项目根目录）
COPY frontend .

# 递归 gzip 压缩所有可压缩类型，保留原文件
# 压缩级别 9，最大压缩
RUN find . -type f \( \
        -name "*.html" -o \
        -name "*.css" -o \
        -name "*.js" -o \
        -name "*.json" -o \
        -name "*.svg" -o \
        -name "*.xml" -o \
        -name "*.txt" -o \
        -name "*.ico" -o \
        -name "*.png" -o \
        -name "*.jpg" -o \
        -name "*.jpeg" -o \
        -name "*.gif" \
    \) \
    -exec sh -c 'gzip -9 -c "{}" > "{}.gz"' \; \
    && echo "预压缩完成"

# ---------- Stage 2: Nginx 运行镜像 ----------
FROM nginx:1.25-alpine

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 复制预压缩后的静态文件（包含 .gz）
COPY --from=compressor /app /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/nginx-health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
