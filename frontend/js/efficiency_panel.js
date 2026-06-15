/**
 * efficiency_panel.js — 控制面板 & 能效分析模块
 * 职责:
 *   - 数值派生: 由 wheelSpeed 计算锭速、张力、捻度、功耗、能效 (模拟模式)
 *   - DOM 交互: 速度滑块、皮带参数、权重滑块、开关、按钮
 *   - 优化参数组装: 收集前端表单字段 → 请求体
 *   - 结果展示: 优化结果、权重归一化、收敛曲线、转速-捻度曲线、能效对比
 *
 * 依赖: ChartManager (charts.js), apiClient (api.js)
 * 对外接口: EfficiencyPanelController 实例
 */
class EfficiencyPanelController {
    constructor({ sceneManager, spinningFrame, chartManager, apiClient }) {
        this.sceneManager = sceneManager;
        this.frame = spinningFrame;           // SpinningFrame3D 实例
        this.charts = chartManager;
        this.api = apiClient;

        this.elapsedTime = 0;
        this.updateInterval = 0.1;
        this.lastUpdateTime = 0;
        this.useApi = false;
        this.currentData = null;
        this.alarms = [];
        this.convergenceChart = null;

        // ---- 模拟模式下的硬编码派生公式（后端模型的粗略前端副本） ----
        this.fallback = {
            baseTension: 5.0,
            tensionSlope: 0.15,
            baseTwist: 20,
            twistSlope: 0.8,
            basePower: 0.5,
            powerSlope: 0.015,
            efficiencySlope: 0.3,
            transmissionRatio: 3.5,
            breakageStart: 40,
            breakageSlope: 0.2,
        };
    }

    // ======================== 数据派生 ========================
    spindleSpeedFromWheel(wheelSpeed) {
        return wheelSpeed * this.fallback.transmissionRatio;
    }
    tensionFromWheel(wheelSpeed) {
        return this.fallback.baseTension + wheelSpeed * this.fallback.tensionSlope;
    }
    twistFromWheel(wheelSpeed) {
        return this.fallback.baseTwist + wheelSpeed * this.fallback.twistSlope;
    }
    powerFromWheel(wheelSpeed) {
        return this.fallback.basePower + wheelSpeed * this.fallback.powerSlope;
    }
    efficiencyFromWheel(wheelSpeed) {
        return wheelSpeed > 0 ? wheelSpeed * this.fallback.efficiencySlope : 0;
    }
    breakageFromWheel(wheelSpeed) {
        return wheelSpeed > this.fallback.breakageStart
            ? (wheelSpeed - this.fallback.breakageStart) * this.fallback.breakageSlope : 0;
    }

    // ======================== 事件监听（拆分自 main.js setupEventListeners） ========================
    bindGlobalControls(onComponentClick, onRunOptimization) {
        this._onComponentClick = onComponentClick;
        this._onRunOptimization = onRunOptimization;

        const speedControl = document.getElementById('speed-control');
        const speedValue = document.getElementById('speed-value');
        speedControl.addEventListener('input', (e) => {
            const speed = parseInt(e.target.value);
            speedValue.textContent = speed + ' rpm';
            if (!this.useApi) {
                this.sceneManager.setWheelSpeed(speed);
            }
        });

        document.getElementById('show-yarn').addEventListener('change', (e) => {
            this.frame.setYarnVisible(e.target.checked);
        });
        document.getElementById('show-water').addEventListener('change', (e) => {
            this.sceneManager.setWaterVisible(e.target.checked);
        });
        document.getElementById('reset-view').addEventListener('click', () => {
            this.sceneManager.resetCamera();
        });

        document.getElementById('toggle-rotation').addEventListener('click', () => {
            const isRotating = this.sceneManager.toggleRotation();
            const statusEl = document.getElementById('status');
            if (isRotating) {
                statusEl.textContent = this.useApi ? '运行中' : '模拟模式';
                statusEl.className = 'data-value status-running';
            } else {
                statusEl.textContent = '已暂停';
                statusEl.className = 'data-value status-stopped';
            }
        });

        document.getElementById('close-info').addEventListener('click', () => {
            this.hideInfoPanel();
        });
        document.getElementById('run-optimization').addEventListener('click', () => {
            if (this._onRunOptimization) this._onRunOptimization();
        });
        document.getElementById('use-api').addEventListener('change', (e) => {
            this.useApi = e.target.checked;
        });
        document.getElementById('api-url').addEventListener('change', (e) => {
            this.api.setBaseUrl(e.target.value);
        });

        this._bindWeightSliders();
    }

    _bindWeightSliders() {
        const pairs = [
            ['w-efficiency', 'w-eff-val'],
            ['w-production', 'w-prod-val'],
            ['w-twist', 'w-twist-val'],
            ['w-breakage', 'w-break-val'],
        ];
        pairs.forEach(([sid, vid]) => {
            const slider = document.getElementById(sid);
            const label = document.getElementById(vid);
            if (slider && label) {
                slider.addEventListener('input', (e) => {
                    label.textContent = parseFloat(e.target.value).toFixed(2);
                });
            }
        });
    }

    // ======================== 显示更新 ========================
    writeDataDisplay() {
        const wheelSpeed = this.sceneManager.wheelSpeed;
        document.getElementById('wheel-speed').textContent = wheelSpeed.toFixed(1);
        document.getElementById('spindle-speed').textContent =
            this.spindleSpeedFromWheel(wheelSpeed).toFixed(1);
        document.getElementById('tension').textContent =
            this.tensionFromWheel(wheelSpeed).toFixed(2);
        document.getElementById('twist').textContent =
            this.twistFromWheel(wheelSpeed).toFixed(1);
        document.getElementById('power').textContent =
            this.powerFromWheel(wheelSpeed).toFixed(3);
        document.getElementById('efficiency').textContent =
            this.efficiencyFromWheel(wheelSpeed).toFixed(2);
        document.getElementById('breakage-rate').textContent =
            this.breakageFromWheel(wheelSpeed).toFixed(1);
    }

    writeApiData(data) {
        const waterWheel = data.water_wheel || {};
        const spindles = data.spindles || [];
        const wheelRpm = waterWheel.rotational_speed || 0;
        this.sceneManager.setWheelSpeed(Math.min(wheelRpm, 60));
        const active = spindles.filter(s => !s.broken);
        const avg = (arr, field) => arr.length > 0
            ? arr.reduce((s, x) => s + x[field], 0) / arr.length : 0;
        const avgSpeed = avg(active, 'speed');
        const avgTension = avg(active, 'tension');
        const avgTwist = avg(active, 'twist');

        document.getElementById('wheel-speed').textContent = wheelRpm.toFixed(1);
        document.getElementById('spindle-speed').textContent = avgSpeed.toFixed(1);
        document.getElementById('tension').textContent = avgTension.toFixed(2);
        document.getElementById('twist').textContent = avgTwist.toFixed(1);
        document.getElementById('power').textContent = (data.energy_efficiency ? avgSpeed * 0.05 : 0.5).toFixed(2);
        document.getElementById('efficiency').textContent = (data.energy_efficiency || 0).toFixed(2);
        document.getElementById('breakage-rate').textContent = (data.breakage_rate || 0).toFixed(1);

        this.charts.addDataPoint(wheelRpm, avgTwist, this.elapsedTime);
        this.renderEfficiencyChart(data);
    }

    renderEfficiencyChart(data) {
        const payload = [
            { label: '水轮效率', value: 85 },
            { label: '传动效率', value: 92 },
            { label: '纺纱效率', value: 78 },
            { label: '综合能效', value: (data && data.energy_efficiency ? data.energy_efficiency : this.sceneManager.wheelSpeed) * 5 },
        ];
        this.charts.updateEfficiencyChart(payload);
    }

    updateChartsLocal() {
        const wheelSpeed = this.sceneManager.wheelSpeed;
        this.charts.addDataPoint(wheelSpeed, this.twistFromWheel(wheelSpeed), this.elapsedTime);
        this.renderEfficiencyChart(null);
    }

    // ======================== 优化参数组装 & 结果展示 ========================
    buildOptimizationPayload() {
        return {
            water_speed: parseFloat(document.getElementById('opt-water-speed').value),
            wheel_radius: 1.5,
            gear_ratio: 8.0,
            mechanical_efficiency: 0.85,
            friction_coefficient: 0.05,
            min_tension: parseFloat(document.getElementById('opt-min-tension').value),
            max_tension: parseFloat(document.getElementById('opt-max-tension').value),
            max_twist_cv: parseFloat(document.getElementById('opt-max-cv').value),
            population_size: parseInt(document.getElementById('opt-population').value),
            generations: parseInt(document.getElementById('opt-generations').value),
            belt_friction_coeff: parseFloat(document.getElementById('opt-belt-friction').value),
            wrap_angle_deg: parseFloat(document.getElementById('opt-wrap-angle').value),
            initial_belt_tension: parseFloat(document.getElementById('opt-belt-tension').value),
            weight_energy_efficiency: parseFloat(document.getElementById('w-efficiency').value),
            weight_production: parseFloat(document.getElementById('w-production').value),
            weight_twist_uniformity: parseFloat(document.getElementById('w-twist').value),
            weight_low_breakage: parseFloat(document.getElementById('w-breakage').value),
        };
    }

    simulateOptimizationLocal(params) {
        const history = [];
        let best = 0;
        for (let i = 0; i < params.generations; i++) {
            const val = 5 + Math.random() * 3 + (i / params.generations) * 8;
            if (val > best) best = val;
            history.push(best);
        }
        const sum = (params.weight_energy_efficiency + params.weight_production +
            params.weight_twist_uniformity + params.weight_low_breakage) || 1;
        return {
            optimal_num_spindles: 42,
            optimal_blade_angle: 48.5,
            max_objective_value: best,
            total_production_rate: 35.2,
            energy_efficiency: 12.8,
            twist_uniformity_cv: 3.2,
            breakage_rate: 2.1,
            convergence_history: history,
            weights_used: {
                energy_efficiency: params.weight_energy_efficiency / sum,
                production: params.weight_production / sum,
                twist_uniformity: params.weight_twist_uniformity / sum,
                low_breakage: params.weight_low_breakage / sum,
            },
        };
    }

    renderOptimizationResult(result) {
        const box = document.getElementById('optimization-result');
        box.classList.remove('hidden');
        document.getElementById('opt-spindles').textContent = result.optimal_num_spindles + ' 个';
        document.getElementById('opt-blade-angle').textContent =
            (Number(result.optimal_blade_angle) || 0).toFixed(1) + '°';
        document.getElementById('opt-efficiency').textContent =
            (Number(result.energy_efficiency) || 0).toFixed(2) + ' m/min·kW';
        document.getElementById('opt-production').textContent =
            (Number(result.total_production_rate) || 0).toFixed(2) + ' m/min';
        this._renderWeights(result.weights_used || {});
        this._renderConvergence(result.convergence_history);
    }

    _renderWeights(weights) {
        const labels = {
            energy_efficiency: '能效比',
            production: '生产率',
            twist_uniformity: '捻度均匀性',
            low_breakage: '低断头率',
        };
        const c = document.getElementById('weights-display');
        if (!c) return;
        c.innerHTML = Object.entries(labels).map(([k, name]) => {
            const v = weights[k] != null ? Number(weights[k]).toFixed(3) : '-';
            return `<div class="w-row"><span class="w-label">${name}</span><span class="w-value">${v}</span></div>`;
        }).join('');
    }

    _renderConvergence(history) {
        if (!history) return;
        const ctx = document.getElementById('convergence-chart').getContext('2d');
        if (this.convergenceChart) this.convergenceChart.destroy();
        this.convergenceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: history.map((_, i) => i),
                datasets: [{
                    label: '适应度值',
                    data: history,
                    borderColor: '#e94560',
                    backgroundColor: 'rgba(233, 69, 96, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: '收敛曲线',
                        color: '#e0e0e0',
                        font: { size: 12 },
                    },
                },
                scales: {
                    x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                },
            },
        });
    }

    // ======================== 组件点击信息面板 ========================
    showInfoPanel(data) {
        const panel = document.getElementById('info-panel');
        const title = document.getElementById('info-title');
        const body = document.getElementById('info-body');
        title.textContent = data.name || '部件信息';
        let html = '';
        if (data.description) {
            html += `<p style="margin-bottom: 10px; color: #e0e0e0; line-height: 1.6;">${data.description}</p>`;
        }
        html += '<div style="border-top: 1px solid rgba(233, 69, 96, 0.3); padding-top: 10px;">';
        const fields = {
            diameter: '直径', height: '高度', length: '长度', width: '宽度',
            weight: '重量', material: '材质', bladeCount: '叶片数',
            transmission: '传动方式', transmissionRatio: '传动比',
            speed: '转速', index: '编号',
        };
        for (const [k, label] of Object.entries(fields)) {
            if (data[k]) html += `<p><span class="info-label">${label}：</span><span class="info-value">${data[k]}</span></p>`;
        }
        html += '</div>';
        if (data.type === 'spindle') {
            const wheelSpeed = this.sceneManager.wheelSpeed;
            const sp = this.spindleSpeedFromWheel(wheelSpeed) * (data.baseRotationSpeed || 1);
            html += '<div style="border-top: 1px solid rgba(233, 69, 96, 0.3); padding-top: 10px; margin-top: 10px;">';
            html += `<p><span class="info-label">当前转速：</span><span class="info-value">${sp.toFixed(1)} rpm</span></p>`;
            html += '</div>';
        }
        body.innerHTML = html;
        panel.classList.remove('hidden');
    }

    hideInfoPanel() {
        document.getElementById('info-panel').classList.add('hidden');
    }

    // ======================== 告警面板 ========================
    pushAlarm(alarm) {
        this.alarms.unshift(alarm);
        if (this.alarms.length > 50) this.alarms = this.alarms.slice(0, 50);
        this.renderAlarms();
    }

    renderAlarms() {
        const list = document.getElementById('alarm-list');
        if (this.alarms.length === 0) {
            list.innerHTML = '<div class="alarm-empty">暂无告警</div>';
            return;
        }
        list.innerHTML = this.alarms.map(a => `
            <div class="alarm-item alarm-${a.severity || 'warning'}">
                <div class="alarm-header">
                    <span class="alarm-type">${a.alarm_type || '告警'}</span>
                    <span class="alarm-time">${new Date(a.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="alarm-message">${a.message || ''}</div>
            </div>
        `).join('');
    }
}
