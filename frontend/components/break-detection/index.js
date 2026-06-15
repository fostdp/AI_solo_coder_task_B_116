/**
 * 自动生头与断头检测可视化模块
 * 模拟基于图像识别的纱线断头检测与自动接驳机械手
 */
class BreakDetectionPanel {
    constructor(containerId, apiClient) {
        this.container = document.getElementById(containerId);
        this.api = apiClient;
        this.spindleStatus = [];
        this.detectionStats = null;
        this.breakLog = [];
    }

    async init() {
        if (!this.container) return;
        this._renderLayout();
        try {
            await this._loadVisionStatus();
            await this._loadRobotStatus();
            await this._loadSpindleStatus();
            await this._loadStats();
        } catch (e) {
            console.error('[BreakDetection] 初始化失败:', e);
        }
        this._startAutoRefresh();
    }

    _renderLayout() {
        this.container.innerHTML = `
            <div class="detection-panel">
                <div class="panel-header">
                    <h3>🔍 智能断头检测与自动生头</h3>
                    <p class="subtitle">机器视觉识别 + AI算法 + 自动接驳机械手，模拟现代纺纱智能化技术</p>
                </div>
                <div class="detection-top">
                    <div class="vision-status-card" id="vision-status">
                        <h4>📷 视觉检测系统</h4>
                        <div class="vision-loading">加载中...</div>
                    </div>
                    <div class="robot-status-card" id="robot-status">
                        <h4>🤖 自动生头机械手</h4>
                        <div class="robot-loading">加载中...</div>
                    </div>
                    <div class="stats-card" id="stats-card">
                        <h4>📊 运行统计</h4>
                        <div class="stats-loading">加载中...</div>
                    </div>
                </div>
                <div class="spindle-monitor">
                    <h4>🎯 32锭实时状态监测</h4>
                    <div class="spindle-grid" id="spindle-grid"></div>
                </div>
                <div class="simulation-section">
                    <h4>🧪 断头模拟</h4>
                    <div class="sim-controls">
                        <label>锭子编号:
                            <select id="sim-spindle-id">
                                ${Array.from({length: 32}, (_, i) => `<option value="${i}">锭 ${i + 1}</option>`).join('')}
                            </select>
                        </label>
                        <label>锭速 (rpm):
                            <input type="number" id="sim-speed" value="350" min="50" max="500">
                        </label>
                        <label>张力 (cN):
                            <input type="number" id="sim-tension" value="50" min="5" max="150">
                        </label>
                        <label>纤维类型:
                            <select id="sim-fiber">
                                <option value="cotton">棉花</option>
                                <option value="hemp">苎麻</option>
                                <option value="flax">亚麻</option>
                                <option value="silk">桑蚕丝</option>
                                <option value="wool">绵羊毛</option>
                            </select>
                        </label>
                        <button class="btn btn-danger" id="sim-trigger-btn">💥 模拟断头</button>
                    </div>
                    <div class="sim-result" id="sim-result"></div>
                </div>
                <div class="break-log-section">
                    <h4>📝 断头事件日志</h4>
                    <div class="break-log" id="break-log">
                        <div class="empty-log">暂无断头事件记录</div>
                    </div>
                </div>
            </div>
        `;
        document.getElementById('sim-trigger-btn').addEventListener('click', () => this._triggerSimulatedBreak());
    }

    _startAutoRefresh() {
        setInterval(async () => {
            try {
                await this._loadSpindleStatus();
                await this._loadStats();
            } catch (e) {}
        }, 3000);
    }

    async _loadVisionStatus() {
        const data = await this.api.getVisionStatus();
        const card = document.getElementById('vision-status');
        if (!card) return;
        card.innerHTML = `
            <div class="vision-detail">
                <div class="status-row">
                    <span class="status-indicator online"></span>
                    <span class="status-label">系统状态</span>
                    <span class="status-value">在线运行</span>
                </div>
                <div class="detail-item"><label>检测算法</label><span>${data.algorithm?.name || '-'}</span></div>
                <div class="detail-item"><label>推理设备</label><span>${data.algorithm?.inference_device || '-'}</span></div>
                <div class="detail-item"><label>模型大小</label><span>${data.algorithm?.model_size_mb || '-'} MB</span></div>
                <div class="detail-item"><label>检测相机数</label><span>${data.cameras?.length || 0} 台</span></div>
                <div class="detail-item"><label>累计扫描</label><span>${data.statistics?.total_frames_scanned || 0} 帧</span></div>
                <div class="detail-item"><label>检出断头</label><span>${data.statistics?.breaks_detected || 0} 次</span></div>
                <div class="detail-item"><label>平均延迟</label><span>${data.statistics?.avg_detection_latency_ms || 0} ms</span></div>
            </div>
            <div class="camera-grid">
                ${(data.cameras || []).map(c => `
                    <div class="camera-mini">
                        <div class="camera-id">${c.camera_id}</div>
                        <div class="camera-spec">${c.resolution} @ ${c.fps}fps</div>
                        <div class="camera-coverage">${c.coverage}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async _loadRobotStatus() {
        const data = await this.api.getRobotStatus();
        const card = document.getElementById('robot-status');
        if (!card) return;
        card.innerHTML = `
            <div class="robot-detail">
                <div class="status-row">
                    <span class="status-indicator ${data.status === 'idle' ? 'idle' : 'working'}"></span>
                    <span class="status-label">机械手状态</span>
                    <span class="status-value">${data.status === 'idle' ? '待机' : '工作中'}</span>
                </div>
                <div class="detail-item"><label>累计尝试</label><span>${data.total_attempts} 次</span></div>
                <div class="detail-item"><label>成功次数</label><span class="success">${data.successful} 次</span></div>
                <div class="detail-item"><label>失败次数</label><span class="fail">${data.failed} 次</span></div>
                <div class="detail-item"><label>成功率</label><span class="rate">${data.success_rate_percent}%</span></div>
                <div class="detail-item"><label>平均接驳时间</label><span>${data.avg_piecing_time_ms} ms</span></div>
                <div class="detail-item"><label>累计节纱</label><span class="saving">${data.total_yarn_saved_m} m</span></div>
            </div>
        `;
    }

    async _loadStats() {
        const data = await this.api.getDetectionStats();
        this.detectionStats = data;
        const card = document.getElementById('stats-card');
        if (!card) return;
        card.innerHTML = `
            <div class="stats-detail">
                <div class="stat-big">
                    <div class="stat-num">${data.total_breaks || 0}</div>
                    <div class="stat-label">累计断头</div>
                </div>
                <div class="detail-item"><label>视觉检出率</label><span>${data.detection_rate_percent || 0}%</span></div>
                <div class="detail-item"><label>自动接驳成功率</label><span>${data.auto_piecing_success_rate_percent || 0}%</span></div>
                <div class="detail-item"><label>累计停机时间</label><span>${data.total_downtime_seconds || 0}s</span></div>
                <div class="detail-item"><label>累计失纱</label><span>${data.total_yarn_lost_m || 0}m</span></div>
            </div>
        `;
    }

    async _loadSpindleStatus() {
        const data = await this.api.getSpindleStatus();
        this.spindleStatus = data.spindles || [];
        const grid = document.getElementById('spindle-grid');
        if (!grid) return;

        const statusColors = {
            running: { bg: '#10B981', label: '运行' },
            broken: { bg: '#EF4444', label: '断头' },
            needs_manual: { bg: '#F59E0B', label: '需人工' },
            piecing: { bg: '#3B82F6', label: '接驳中' }
        };

        grid.innerHTML = this.spindleStatus.map(s => {
            const c = statusColors[s.status] || statusColors.running;
            return `
                <div class="spindle-cell" style="background:${c.bg}22;border-color:${c.bg}" data-id="${s.spindle_id}">
                    <div class="spindle-id">锭 ${s.spindle_id + 1}</div>
                    <div class="spindle-status-dot" style="background:${c.bg}"></div>
                    <div class="spindle-status-text">${c.label}</div>
                </div>
            `;
        }).join('');
    }

    async _triggerSimulatedBreak() {
        const spindleId = parseInt(document.getElementById('sim-spindle-id').value);
        const speed = parseFloat(document.getElementById('sim-speed').value);
        const tension = parseFloat(document.getElementById('sim-tension').value);
        const fiber = document.getElementById('sim-fiber').value;

        const resultDiv = document.getElementById('sim-result');
        resultDiv.innerHTML = '<div class="loading">正在模拟断头检测与接驳...</div>';

        try {
            const result = await this.api.simulateBreak({
                spindle_id: spindleId,
                speed_rpm: speed,
                tension_cn: tension,
                fiber_type: fiber
            });

            this.breakLog.unshift(result);
            if (this.breakLog.length > 50) this.breakLog = this.breakLog.slice(0, 50);
            this._renderBreakLog();
            await this._loadSpindleStatus();
            await this._loadVisionStatus();
            await this._loadRobotStatus();
            await this._loadStats();

            resultDiv.innerHTML = `
                <div class="sim-result-card">
                    <div class="sim-step ${result.detection.detected ? 'ok' : 'fail'}">
                        <span class="step-icon">${result.detection.detected ? '✅' : '❌'}</span>
                        <span class="step-text">视觉检测 ${result.detection.detected ? '成功识别断头' : '漏检'}（置信度 ${(result.break_event.confidence * 100).toFixed(1)}%，延迟 ${result.break_event.detection_latency_ms}ms，相机 ${result.detection.camera_id || '未知'}）</span>
                    </div>
                    ${result.auto_piecing ? `
                        <div class="sim-step ${result.auto_piecing.success ? 'ok' : 'fail'}">
                            <span class="step-icon">${result.auto_piecing.success ? '🤖' : '💢'}</span>
                            <span class="step-text">
                                自动生头 ${result.auto_piecing.success ? '成功' : '失败'}（耗时 ${result.auto_piecing.piecing_time_ms}ms，失纱 ${result.auto_piecing.yarn_lost_m}m，节纱 ${result.auto_piecing.yarn_saved_m}m，停机 ${result.auto_piecing.downtime_seconds}s）
                            </span>
                        </div>
                        <div class="sim-sub-steps">
                            ${result.auto_piecing.steps.map(s => `
                                <div class="sub-step">
                                    <span class="sub-step-name">${s.name}</span>
                                    <div class="sub-step-bar"><div style="width:${s.time_ms / result.auto_piecing.piecing_time_ms * 100}%"></div></div>
                                    <span class="sub-step-time">${s.time_ms}ms</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<div class="sim-step warn"><span class="step-icon">⚠️</span><span class="step-text">断头未检测到，等待人工发现</span></div>'}
                    <div class="sim-break-info">
                        <div>断头原因: ${result.break_event.break_cause_cn} (${result.break_event.break_cause})</div>
                        <div>断头时张力: ${result.break_event.tension_at_break_cn} cN</div>
                        <div>断头时锭速: ${result.break_event.speed_at_break_rpm} rpm</div>
                        <div>锭子状态: <strong class="${result.spindle_status === 'running' ? 'ok' : result.spindle_status === 'needs_manual' ? 'warn' : 'fail'}">${{running: '恢复运行', broken: '断头停机', needs_manual: '需人工处理'}[result.spindle_status]}</strong></div>
                    </div>
                </div>
            `;
        } catch (e) {
            resultDiv.innerHTML = `<div class="error">模拟失败: ${e.message}</div>`;
        }
    }

    _renderBreakLog() {
        const container = document.getElementById('break-log');
        if (!this.breakLog.length) {
            container.innerHTML = '<div class="empty-log">暂无断头事件记录</div>';
            return;
        }
        container.innerHTML = this.breakLog.map((log, idx) => {
            const time = new Date(log.break_event.timestamp * 1000).toLocaleTimeString();
            return `
                <div class="log-item ${log.auto_piecing?.success ? 'success' : log.auto_piecing ? 'fail' : 'warn'}">
                    <div class="log-time">${time}</div>
                    <div class="log-spindle">锭${log.break_event.spindle_id + 1}</div>
                    <div class="log-cause">${log.break_event.break_cause_cn}</div>
                    <div class="log-detect">检测: ${log.detection.detected ? '✅' : '❌'}</div>
                    <div class="log-piece">接驳: ${log.auto_piecing ? (log.auto_piecing.success ? '✅' : '❌') : '-'}</div>
                    <div class="log-downtime">${log.auto_piecing?.downtime_seconds || 0}s</div>
                </div>
            `;
        }).join('');
    }
}
