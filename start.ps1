# ============================================================
# 水转大纺车系统 - Windows 一键启动脚本
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  水转大纺车动力学仿真系统 v1.2.0" -ForegroundColor Cyan
Write-Host "  一键启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 步骤 1: 检查 Docker
Write-Host "[1/4] 检查 Docker 运行状态..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker 未运行，请先启动 Docker Desktop"
    }
    Write-Host "    Docker 版本: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "    错误: $_" -ForegroundColor Red
    exit 1
}

# 步骤 2: 检查端口
Write-Host "[2/4] 检查端口占用..." -ForegroundColor Yellow
$ports = @(80, 8000, 8086, 6379, 1883, 5020)
$portConflicts = @()
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn -and $conn.State -eq "Listen") {
        $portConflicts += $port
    }
}
if ($portConflicts.Count -gt 0) {
    Write-Host "    警告: 端口 $($portConflicts -join ', ') 可能被占用" -ForegroundColor Yellow
} else {
    Write-Host "    所有端口可用" -ForegroundColor Green
}

# 步骤 3: 构建并启动
Write-Host "[3/4] 构建并启动所有服务 (11 个容器)..." -ForegroundColor Yellow
Write-Host "    首次构建可能需要 5-10 分钟，请耐心等待..." -ForegroundColor Gray

docker-compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "    构建失败" -ForegroundColor Red
    exit 1
}

docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "    启动失败" -ForegroundColor Red
    exit 1
}

# 步骤 4: 等待服务就绪
Write-Host "[4/4] 等待服务就绪..." -ForegroundColor Yellow
$maxWait = 60
$waitCount = 0
while ($waitCount -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/api/health" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "    API 网关就绪 ✓" -ForegroundColor Green
            break
        }
    } catch {
        # 忽略连接错误
    }
    $waitCount++
    Write-Progress -Activity "等待服务就绪" -PercentComplete ($waitCount / $maxWait * 100) -SecondsRemaining ($maxWait - $waitCount)
    Start-Sleep -Seconds 1
}
Write-Progress -Activity "等待服务就绪" -Completed

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  系统启动完成 ✓" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端:       http://localhost/" -ForegroundColor Cyan
Write-Host "  API 文档:   http://localhost/api/docs" -ForegroundColor Cyan
Write-Host "  InfluxDB:   http://localhost:8086" -ForegroundColor Cyan
Write-Host ""
Write-Host "  常用命令:" -ForegroundColor Yellow
Write-Host "    查看状态:  docker-compose ps" -ForegroundColor Gray
Write-Host "    查看日志:  docker-compose logs -f [服务名]" -ForegroundColor Gray
Write-Host "    停止:      docker-compose down" -ForegroundColor Gray
Write-Host "    查看模式:  docker-compose run --rm simulator python simulator.py --list-modes" -ForegroundColor Gray
Write-Host ""
