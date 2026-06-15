/**
 * 历史纺车技术对比模块
 * 展示手摇纺车、脚踏纺车、水转大纺车的效率与质量对比
 */
class HistoricalComparisonPanel {
    constructor(containerId, apiClient) {
        this.container = document.getElementById(containerId);
        this.api = apiClient;
        this.wheels = [];
        this.comparisonData = null;
        this.currentWheelType = 'water_wheel';
    }

    async init() {
        if (!this.container) return;
        this._renderLayout();
        try {
            await this._loadWheelList();
            await this._loadComparison();
        } catch (e) {
            console.error('[HistoricalComparison] 初始化失败:', e);
            this.container.innerHTML = '<div class="error-message">数据加载失败，请检查后端服务</div>';
        }
    }

    _renderLayout() {
        this.container.innerHTML = `
            <div class="historical-panel">
                <div class="panel-header">
                    <h3>🏛️ 古代纺车技术演进对比</h3>
                    <p class="subtitle">从手摇到水转，见证古代纺织技术的伟大飞跃</p>
                </div>
                <div class="comparison-controls">
                    <label>每日运行时长:
                        <input type="number" id="hist-operating-hours" value="10" min="1" max="24" step="1"> 小时
                    </label>
                    <label>设备利用率:
                        <input type="range" id="hist-utilization" value="0.8" min="0.1" max="1.0" step="0.05">
                        <span id="hist-utilization-value">80%</span>
                    </label>
                    <button id="hist-refresh-btn" class="btn btn-primary">重新计算对比</button>
                </div>
                <div class="wheel-cards" id="hist-wheel-cards"></div>
                <div class="comparison-charts">
                    <h4>📊 效率对比图表</h4>
                    <canvas id="hist-efficiency-chart" height="250"></canvas>
                </div>
                <div class="comparison-charts">
                    <h4>🧵 纱线质量对比</h4>
                    <canvas id="hist-quality-chart" height="250"></canvas>
                </div>
                <div class="timeline-section">
                    <h4>📜 技术演进时间线</h4>
                    <div class="timeline" id="hist-timeline"></div>
                </div>
            </div>
        `;

        document.getElementById('hist-utilization').addEventListener('input', (e) => {
            document.getElementById('hist-utilization-value').textContent = Math.round(e.target.value * 100) + '%';
        });
        document.getElementById('hist-refresh-btn').addEventListener('click', () => this._loadComparison());
    }

    async _loadWheelList() {
        const data = await this.api.getHistoricalWheels();
        this.wheels = data.wheels || [];
    }

    async _loadComparison() {
        const hours = parseFloat(document.getElementById('hist-operating-hours').value) || 10;
        const utilization = parseFloat(document.getElementById('hist-utilization').value) || 0.8;

        this.comparisonData = await this.api.compareHistoricalWheels({
            operating_hours: hours,
            utilization_rate: utilization
        });

        this._renderWheelCards();
        this._renderEfficiencyChart();
        this._renderQualityChart();
        this._renderTimeline();
    }

    _renderWheelCards() {
        const container = document.getElementById('hist-wheel-cards');
        if (!container || !this.comparisonData?.details) return;

        const typeColors = {
            hand_spun: { bg: 'linear-gradient(135deg, #8B7355, #A0826D)', icon: '🖐️' },
            foot_treadle: { bg: 'linear-gradient(135deg, #CD853F, #DEB887)', icon: '🦶' },
            water_wheel: { bg: 'linear-gradient(135deg, #2E86AB, #5DADE2)', icon: '💧' }
        };

        container.innerHTML = this.comparisonData.details.map(d => {
            const colors = typeColors[d.spec.wheel_type] || typeColors.water_wheel;
            return `
                <div class="wheel-card" style="background: ${colors.bg}" data-type="${d.spec.wheel_type}">
                    <div class="wheel-card-icon">${colors.icon}</div>
                    <h4>${d.spec.wheel_name}</h4>
                    <div class="wheel-era">${d.spec.era} · ${d.spec.dynasty}</div>
                    <div class="wheel-year">${d.spec.year_range}</div>
                    <div class="wheel-specs">
                        <div class="spec-item">
                            <span class="spec-label">锭子数</span>
                            <span class="spec-value">${d.spec.num_spindles} 锭</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">动力</span>
                            <span class="spec-value">${d.spec.power_source}</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">日产纱量</span>
                            <span class="spec-value">${d.efficiency.daily_production_kg.toFixed(3)} kg</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">劳动效率</span>
                            <span class="spec-value">${d.efficiency.labor_efficiency_kg_per_person_day.toFixed(3)} kg/人日</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">捻度CV</span>
                            <span class="spec-value">${d.quality.twist_uniformity_cv_percent}%</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">纱线等级</span>
                            <span class="spec-value grade">${d.quality.yarn_grade}</span>
                        </div>
                    </div>
                    <p class="wheel-desc">${d.spec.description}</p>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.wheel-card').forEach(card => {
            card.addEventListener('click', () => {
                card.classList.toggle('expanded');
            });
        });
    }

    _renderEfficiencyChart() {
        const canvas = document.getElementById('hist-efficiency-chart');
        if (!canvas || !this.comparisonData?.details) return;
        const ctx = canvas.getContext('2d');

        const labels = this.comparisonData.details.map(d => d.spec.wheel_name);
        const production = this.comparisonData.details.map(d => d.efficiency.daily_production_kg);
        const laborEff = this.comparisonData.details.map(d => d.efficiency.labor_efficiency_kg_per_person_day);

        if (window._histEffChart) window._histEffChart.destroy();
        window._histEffChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '日产纱量 (kg)',
                        data: production,
                        backgroundColor: 'rgba(46, 134, 171, 0.7)',
                        borderColor: '#2E86AB',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: '劳动效率 (kg/人日)',
                        data: laborEff,
                        backgroundColor: 'rgba(205, 133, 63, 0.7)',
                        borderColor: '#CD853F',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: '日产纱量 (kg)' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: '劳动效率 (kg/人日)' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: { legend: { position: 'top' } }
            }
        });
    }

    _renderQualityChart() {
        const canvas = document.getElementById('hist-quality-chart');
        if (!canvas || !this.comparisonData?.details) return;
        const ctx = canvas.getContext('2d');

        const labels = this.comparisonData.details.map(d => d.spec.wheel_name);
        const twistCV = this.comparisonData.details.map(d => d.quality.twist_uniformity_cv_percent);
        const breakage = this.comparisonData.details.map(d => d.quality.breakage_rate_percent);
        const qualityIdx = this.comparisonData.details.map(d => d.quality.overall_quality_index * 100);

        if (window._histQualChart) window._histQualChart.destroy();
        window._histQualChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['捻度均匀性(低CV好)', '低断头率', '综合质量指数', '纱线条干(低CV好)', '强度均匀性(低CV好)'],
                datasets: this.comparisonData.details.map((d, i) => ({
                    label: d.spec.wheel_name,
                    data: [
                        100 - d.quality.twist_uniformity_cv_percent,
                        100 - d.quality.breakage_rate_percent,
                        d.quality.overall_quality_index * 100,
                        100 - d.quality.yarn_evenness_cv_percent,
                        100 - d.quality.yarn_strength_cv_percent
                    ],
                    backgroundColor: ['rgba(139,115,85,0.2)', 'rgba(205,133,63,0.2)', 'rgba(46,134,171,0.2)'][i],
                    borderColor: ['#8B7355', '#CD853F', '#2E86AB'][i],
                    borderWidth: 2,
                    pointBackgroundColor: ['#8B7355', '#CD853F', '#2E86AB'][i]
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 20 }
                    }
                }
            }
        });
    }

    _renderTimeline() {
        const container = document.getElementById('hist-timeline');
        if (!container) return;

        const timeline = [
            { era: '新石器时代', year: '约公元前5000年', event: '手摇纺车出现', wheel: 'hand_spun', desc: '最早的纺纱工具，开启人类纺织文明' },
            { era: '商周', year: '约公元前1600年', event: '丝织技术兴起', wheel: 'hand_spun', desc: '桑蚕丝开始用于高档纺织品' },
            { era: '宋元', year: '约公元1000年', event: '脚踏纺车普及', wheel: 'foot_treadle', desc: '解放双手，产量提升3-5倍' },
            { era: '宋元', year: '约公元1200年', event: '水转大纺车问世', wheel: 'water_wheel', desc: '水力驱动32锭，日夜不息，古代纺织机械巅峰' },
            { era: '明清', year: '公元1368-1900年', event: '各类纺车并存', wheel: 'water_wheel', desc: '家庭手摇、作坊脚踏、工场水转，各擅其场' }
        ];

        container.innerHTML = timeline.map((item, idx) => `
            <div class="timeline-item ${idx % 2 === 0 ? 'left' : 'right'}">
                <div class="timeline-content">
                    <div class="timeline-era">${item.era} · ${item.year}</div>
                    <div class="timeline-event">${item.event}</div>
                    <div class="timeline-desc">${item.desc}</div>
                </div>
                <div class="timeline-dot"></div>
            </div>
        `).join('');
    }
}
