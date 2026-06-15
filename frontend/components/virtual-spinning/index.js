/**
 * 公众体验虚拟纺纱模块
 * 用户可调节水流速度、选择纤维原料，实时观察纱线生成过程
 */
class VirtualSpinningPanel {
    constructor(containerId, apiClient) {
        this.container = document.getElementById(containerId);
        this.api = apiClient;
        this.sessionId = null;
        this.currentState = null;
        this.rafId = null;
        this.canvas = null;
        this.ctx = null;
        this.pollTimer = null;
        this.waterParticles = [];
        this.yarnPoints = [];
    }

    async init() {
        if (!this.container) return;
        this._renderLayout();
        this._initCanvas();
        this._startRenderLoop();
        this._setupControls();
    }

    _renderLayout() {
        this.container.innerHTML = `
            <div class="virtual-spinning-panel">
                <div class="panel-header">
                    <h3>🎨 体验虚拟纺纱</h3>
                    <p class="subtitle">调节水流和原料，亲手"驱动"古代水转大纺车，见证神奇的纱线诞生过程</p>
                </div>
                <div class="vs-main-layout">
                    <div class="vs-canvas-area">
                        <canvas id="vs-canvas" width="800" height="500"></canvas>
                        <div class="vs-hud">
                            <div class="hud-item">
                                <span class="hud-label">💧 水流速度</span>
                                <span class="hud-value" id="hud-water">0.0 m/s</span>
                            </div>
                            <div class="hud-item">
                                <span class="hud-label">⚙️ 水轮转速</span>
                                <span class="hud-value" id="hud-wheel">0 rpm</span>
                            </div>
                            <div class="hud-item">
                                <span class="hud-label">🧵 锭子转速</span>
                                <span class="hud-value" id="hud-spindle">0 rpm</span>
                            </div>
                            <div class="hud-item">
                                <span class="hud-label">📏 已纺纱长</span>
                                <span class="hud-value" id="hud-length">0.000 m</span>
                            </div>
                            <div class="hud-item">
                                <span class="hud-label">⚖️ 纱线张力</span>
                                <span class="hud-value" id="hud-tension">0 cN</span>
                            </div>
                            <div class="hud-item quality">
                                <span class="hud-label">⭐ 质量评分</span>
                                <span class="hud-value" id="hud-quality">0</span>
                            </div>
                            <div class="hud-item efficiency">
                                <span class="hud-label">🌿 效率评分</span>
                                <span class="hud-value" id="hud-efficiency">0</span>
                            </div>
                            <div class="hud-item break-count">
                                <span class="hud-label">💔 断头次数</span>
                                <span class="hud-value" id="hud-breaks">0</span>
                            </div>
                        </div>
                        <div class="vs-message" id="vs-message">点击"开始纺纱"启动水轮</div>
                    </div>
                    <div class="vs-controls-area">
                        <div class="vs-session-info" id="vs-session-info">
                            <strong>会话状态:</strong> <span id="vs-session-status">未开始</span>
                            <button class="btn btn-small" id="vs-create-btn">创建会话</button>
                        </div>
                        <div class="control-group">
                            <h5>💧 调节水流速度</h5>
                            <div class="slider-control">
                                <input type="range" id="vs-water-slider" min="0.1" max="8" step="0.1" value="2" disabled>
                                <span id="vs-water-value">2.0 m/s</span>
                            </div>
                            <div class="water-presets">
                                <button data-speed="0.5" class="preset-btn" disabled>细流</button>
                                <button data-speed="1.5" class="preset-btn" disabled>缓流</button>
                                <button data-speed="2.5" class="preset-btn active" disabled>常流</button>
                                <button data-speed="4.0" class="preset-btn" disabled>急流</button>
                                <button data-speed="6.0" class="preset-btn" disabled>洪水</button>
                            </div>
                            <div class="water-hint">💡 提示：水流太快会增加断头风险，太慢则产量低</div>
                        </div>
                        <div class="control-group">
                            <h5>🧶 选择纤维原料</h5>
                            <div class="fiber-selector" id="vs-fiber-selector">
                                <button class="fiber-btn active" data-type="cotton" style="border-color:#FFF8E7" disabled>
                                    <span class="fiber-color" style="background:#FFF8E7"></span>
                                    <span class="fiber-name">棉花</span>
                                    <span class="fiber-diff">简单</span>
                                </button>
                                <button class="fiber-btn" data-type="hemp" style="border-color:#F5E6C8" disabled>
                                    <span class="fiber-color" style="background:#F5E6C8"></span>
                                    <span class="fiber-name">苎麻</span>
                                    <span class="fiber-diff">中等</span>
                                </button>
                                <button class="fiber-btn" data-type="silk" style="border-color:#FFF5F0" disabled>
                                    <span class="fiber-color" style="background:#FFF5F0"></span>
                                    <span class="fiber-name">桑蚕丝</span>
                                    <span class="fiber-diff">困难</span>
                                </button>
                                <button class="fiber-btn" data-type="wool" style="border-color:#FAF0E6" disabled>
                                    <span class="fiber-color" style="background:#FAF0E6"></span>
                                    <span class="fiber-name">绵羊毛</span>
                                    <span class="fiber-diff">中等</span>
                                </button>
                            </div>
                        </div>
                        <div class="control-group">
                            <h5>🎮 操作控制</h5>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-large" id="vs-start-btn" disabled>▶️ 开始纺纱</button>
                                <button class="btn btn-secondary" id="vs-pause-btn" disabled>⏸️ 暂停</button>
                                <button class="btn btn-warning" id="vs-reset-btn" disabled>🔄 重置</button>
                            </div>
                        </div>
                        <div class="control-group tips">
                            <h5>📖 纺纱小贴士</h5>
                            <ul>
                                <li>🌊 水流速度决定水轮转速，是纺纱的动力来源</li>
                                <li>🧵 不同纤维有不同特性：棉花简单易纺，蚕丝精细但难纺</li>
                                <li>⚖️ 张力过高会断头，过低则纱线松垮</li>
                                <li>⭐ 质量和效率需要平衡，追求极致可能顾此失彼</li>
                                <li>🎯 挑战：纺出10米不断头的纱线！</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _initCanvas() {
        this.canvas = document.getElementById('vs-canvas');
        this.ctx = this.canvas.getContext('2d');
        this._initWaterParticles();
        this._initYarnPoints();
    }

    _initWaterParticles() {
        this.waterParticles = [];
        for (let i = 0; i < 80; i++) {
            this.waterParticles.push({
                x: Math.random() * 800,
                y: 150 + Math.random() * 80,
                size: 2 + Math.random() * 4,
                speed: 0.5 + Math.random() * 1.5,
                alpha: 0.3 + Math.random() * 0.5
            });
        }
    }

    _initYarnPoints() {
        this.yarnPoints = [];
        for (let i = 0; i < 50; i++) {
            this.yarnPoints.push({
                x: 300 + i * 10,
                y: 350,
                offsetX: 0,
                offsetY: 0
            });
        }
    }

    _setupControls() {
        document.getElementById('vs-create-btn').addEventListener('click', () => this._createSession());
        document.getElementById('vs-start-btn').addEventListener('click', () => this._control('start'));
        document.getElementById('vs-pause-btn').addEventListener('click', () => this._control('pause'));
        document.getElementById('vs-reset-btn').addEventListener('click', () => this._control('reset'));

        const waterSlider = document.getElementById('vs-water-slider');
        waterSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            document.getElementById('vs-water-value').textContent = val.toFixed(1) + ' m/s';
            if (this.sessionId) {
                this._setParameter({ water_speed: val });
            }
        });

        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const speed = parseFloat(btn.dataset.speed);
                waterSlider.value = speed;
                waterSlider.dispatchEvent(new Event('input'));
                document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        document.querySelectorAll('.fiber-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.dataset.type;
                document.querySelectorAll('.fiber-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (this.sessionId) {
                    this._setParameter({ fiber_type: type });
                }
            });
        });
    }

    async _createSession() {
        const activeBtn = document.querySelector('.fiber-btn.active');
        const result = await this.api.createVirtualSpinningSession({
            water_speed: parseFloat(document.getElementById('vs-water-slider').value),
            fiber_type: activeBtn?.dataset.type || 'cotton'
        });
        this.sessionId = result.session_id;
        this.currentState = result.snapshot;
        document.getElementById('vs-session-status').textContent = '已连接';
        document.getElementById('vs-session-status').className = 'connected';
        this._enableControls(true);
        this._startPolling();
    }

    async _control(action) {
        if (!this.sessionId) return;
        const result = await this.api.controlVirtualSpinning({
            session_id: this.sessionId,
            action: action
        });
        this.currentState = result.snapshot;
        this._updateHUD();
    }

    async _setParameter(params) {
        if (!this.sessionId) return;
        const result = await this.api.controlVirtualSpinning({
            session_id: this.sessionId,
            action: '',
            ...params
        });
        this.currentState = result.snapshot;
        this._updateHUD();
    }

    _enableControls(enabled) {
        const ids = ['vs-water-slider', 'vs-start-btn', 'vs-pause-btn', 'vs-reset-btn'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = !enabled;
        });
        document.querySelectorAll('.preset-btn').forEach(b => b.disabled = !enabled);
        document.querySelectorAll('.fiber-btn').forEach(b => b.disabled = !enabled);
    }

    _startPolling() {
        this.pollTimer = setInterval(async () => {
            if (!this.sessionId) return;
            try {
                this.currentState = await this.api.getVirtualSpinningSnapshot(this.sessionId);
                this._updateHUD();
            } catch (e) {
                console.error('[VirtualSpinning] 轮询失败:', e);
            }
        }, 100);
    }

    _updateHUD() {
        if (!this.currentState) return;
        document.getElementById('hud-water').textContent = this.currentState.water_speed.toFixed(2) + ' m/s';
        document.getElementById('hud-wheel').textContent = this.currentState.wheel_rpm.toFixed(1) + ' rpm';
        document.getElementById('hud-spindle').textContent = this.currentState.spindle_rpm.toFixed(1) + ' rpm';
        document.getElementById('hud-length').textContent = this.currentState.yarn_length_m.toFixed(3) + ' m';
        document.getElementById('hud-tension').textContent = this.currentState.yarn_tension_cn.toFixed(1) + ' cN';
        document.getElementById('hud-quality').textContent = this.currentState.quality_score.toFixed(0);
        document.getElementById('hud-efficiency').textContent = this.currentState.efficiency_score.toFixed(0);
        document.getElementById('hud-breaks').textContent = this.currentState.break_count;
        document.getElementById('vs-message').textContent = this.currentState.message || '';
        document.getElementById('vs-message').className = 'vs-message ' + (this.currentState.is_running ? 'running' : '');
    }

    _startRenderLoop() {
        const render = () => {
            this._render();
            this.rafId = requestAnimationFrame(render);
        };
        render();
    }

    _render() {
        if (!this.ctx) return;
        const ctx = this.ctx;
        const W = 800, H = 500;

        ctx.clearRect(0, 0, W, H);

        const grad = ctx.createLinearGradient(0, 0, 0, H);
        grad.addColorStop(0, '#E8F4FD');
        grad.addColorStop(0.4, '#D1E9F7');
        grad.addColorStop(1, '#A8D8EA');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, W, H);

        this._drawWater(ctx, W, H);
        this._drawWaterWheel(ctx, W, H);
        this._drawSpinningFrame(ctx, W, H);
        this._drawYarn(ctx, W, H);
        this._drawFibers(ctx, W, H);
    }

    _drawWater(ctx, W, H) {
        const waterSpeed = this.currentState?.water_speed || 0;

        ctx.fillStyle = '#3498DB';
        ctx.beginPath();
        ctx.moveTo(0, 180);
        for (let x = 0; x <= W; x += 20) {
            const y = 180 + Math.sin((x + Date.now() * waterSpeed * 0.05) * 0.02) * 8;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(W, 260);
        ctx.lineTo(0, 260);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        this.waterParticles.forEach(p => {
            p.x += p.speed * (0.5 + waterSpeed * 0.3);
            if (p.x > W + 10) {
                p.x = -10;
                p.y = 155 + Math.random() * 80;
            }
            ctx.globalAlpha = p.alpha;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1;
    }

    _drawWaterWheel(ctx, W, H) {
        const cx = 200, cy = 180, r = 90;
        const wheelRpm = this.currentState?.wheel_rpm || 0;
        const rotation = (wheelRpm / 60) * (Date.now() / 1000) * Math.PI * 2;

        ctx.save();
        ctx.translate(cx, cy);

        ctx.fillStyle = '#6B4423';
        ctx.strokeStyle = '#4A2E15';
        ctx.lineWidth = 2;

        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        const bladeCount = 12;
        for (let i = 0; i < bladeCount; i++) {
            const angle = rotation + (i / bladeCount) * Math.PI * 2;
            ctx.save();
            ctx.rotate(angle);
            ctx.fillStyle = '#8B5A2B';
            ctx.fillRect(r - 5, -6, 25, 12);
            ctx.strokeRect(r - 5, -6, 25, 12);
            ctx.restore();
        }

        ctx.beginPath();
        ctx.arc(0, 0, 15, 0, Math.PI * 2);
        ctx.fillStyle = '#4A2E15';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, 0, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#B8860B';
        ctx.fill();

        ctx.restore();

        ctx.strokeStyle = '#8B5A2B';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx, cy + 200);
        ctx.lineTo(cx - 80, cy + 220);
        ctx.lineTo(cx + 80, cy + 220);
        ctx.stroke();
    }

    _drawSpinningFrame(ctx, W, H) {
        const baseY = 300;

        ctx.fillStyle = '#A0522D';
        ctx.fillRect(350, baseY, 380, 80);
        ctx.strokeStyle = '#6B3410';
        ctx.lineWidth = 2;
        ctx.strokeRect(350, baseY, 380, 80);

        const spindleCount = 8;
        const spacing = 340 / spindleCount;
        const spindleRpm = this.currentState?.spindle_rpm || 0;
        const twistRot = this.currentState?.twist_rotation_rad || 0;

        for (let i = 0; i < spindleCount; i++) {
            const sx = 380 + i * spacing;
            const sy = baseY - 20;

            ctx.fillStyle = '#DAA520';
            ctx.fillRect(sx - 3, sy - 50, 6, 50);

            const bobbinY = sy - 25;
            ctx.fillStyle = '#F5DEB3';
            ctx.beginPath();
            ctx.ellipse(sx, bobbinY, 10, 18, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#DEB887';
            ctx.stroke();

            const spinAngle = twistRot + (i * 0.3);
            ctx.strokeStyle = '#FFF8DC';
            ctx.lineWidth = 1.5;
            for (let t = 0; t < 3; t++) {
                const a = spinAngle + t * Math.PI * 0.66;
                ctx.beginPath();
                ctx.moveTo(sx, bobbinY - 15);
                ctx.lineTo(sx + Math.cos(a) * 12, bobbinY - 15 + Math.sin(a) * 12);
                ctx.stroke();
            }
        }

        ctx.fillStyle = '#CD853F';
        ctx.fillRect(340, baseY + 80, 400, 15);
    }

    _drawYarn(ctx, W, H) {
        if (!this.currentState) return;

        const fiberType = this.currentState.fiber_type || 'cotton';
        const fiberColors = {
            cotton: '#FFF8E7', hemp: '#F5E6C8', silk: '#FFF5F0',
            wool: '#FAF0E6', flax: '#E8D4A8'
        };
        const color = fiberColors[fiberType] || '#FFF8E7';

        const startX = 370, startY = 330;
        const endX = 760, endY = 350;
        const length = this.currentState.yarn_length_m || 0;
        const twistAngle = this.currentState.twist_rotation_rad || 0;

        ctx.strokeStyle = color;
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(startX, startY);

        const segments = 30;
        for (let i = 1; i <= segments; i++) {
            const t = i / segments;
            const x = startX + (endX - startX) * t;
            const wave = Math.sin(twistAngle * 3 + t * 20) * (4 + length * 0.1);
            const y = startY + (endY - startY) * t + wave;
            ctx.lineTo(x, y);
        }
        ctx.stroke();

        ctx.strokeStyle = 'rgba(139,119,101,0.3)';
        ctx.lineWidth = 1;
        for (let i = 0; i < 40; i++) {
            const t = i / 40;
            const x = startX + (endX - startX) * t;
            const wave = Math.sin(twistAngle * 3 + t * 20) * (4 + length * 0.1);
            const y = startY + (endY - startY) * t + wave;
            const a = twistAngle + t * 15;
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x + Math.cos(a) * 6, y + Math.sin(a) * 6);
            ctx.stroke();
        }
    }

    _drawFibers(ctx, W, H) {
        if (!this.currentState?.fibers) return;
        const fibers = this.currentState.fibers;
        const fiberType = this.currentState.fiber_type || 'cotton';
        const fiberColors = {
            cotton: '#FFF8E7', hemp: '#F5E6C8', silk: '#FFF5F0',
            wool: '#FAF0E6', flax: '#E8D4A8'
        };

        fibers.forEach(f => {
            const x = 360 + f.x;
            const y = 330 + f.y;
            if (x < 340 || x > 380) return;
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(f.angle || 0);
            ctx.fillStyle = f.color || fiberColors[fiberType];
            ctx.fillRect(-f.length / 2, -f.thickness / 2, f.length, f.thickness || 1);
            ctx.restore();
        });
    }

    destroy() {
        if (this.rafId) cancelAnimationFrame(this.rafId);
        if (this.pollTimer) clearInterval(this.pollTimer);
        if (this.sessionId) {
            this.api.closeVirtualSpinningSession(this.sessionId).catch(() => {});
        }
    }
}
