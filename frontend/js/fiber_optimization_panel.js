/**
 * 棉麻丝纤维纺纱参数优化模块
 */
class FiberOptimizationPanel {
    constructor(containerId, apiClient) {
        this.container = document.getElementById(containerId);
        this.api = apiClient;
        this.fibers = [];
        this.currentFiber = null;
    }

    async init() {
        if (!this.container) return;
        this._renderLayout();
        try {
            const data = await this.api.getFibers();
            this.fibers = data.fibers || [];
            this._renderFiberList();
        } catch (e) {
            console.error('[FiberOptimization] 加载失败:', e);
        }
    }

    _renderLayout() {
        this.container.innerHTML = `
            <div class="fiber-panel">
                <div class="panel-header">
                    <h3>🧶 棉麻丝纤维纺纱参数优化</h3>
                    <p class="subtitle">基于纤维物理特性，智能推荐牵伸、加捻、锭速等工艺参数</p>
                </div>
                <div class="fiber-layout">
                    <div class="fiber-sidebar">
                        <h4>选择纤维原料</h4>
                        <div class="fiber-list" id="fiber-list"></div>
                    </div>
                    <div class="fiber-main">
                        <div class="fiber-detail" id="fiber-detail">
                            <div class="placeholder">请从左侧选择一种纤维</div>
                        </div>
                        <div class="optimization-form" id="optimization-form" style="display:none">
                            <h4>参数优化设置</h4>
                            <div class="form-row">
                                <label>纱线支数 (tex):
                                    <input type="number" id="fiber-yarn-count" value="100" min="10" max="600">
                                </label>
                                <label>粗纱支数 (tex):
                                    <input type="number" id="fiber-roving-count" value="2500" min="100" max="10000">
                                </label>
                                <label>质量优先级:
                                    <select id="fiber-quality-priority">
                                        <option value="quality">质量优先</option>
                                        <option value="balanced" selected>均衡</option>
                                        <option value="speed">产量优先</option>
                                    </select>
                                </label>
                            </div>
                            <button class="btn btn-primary" id="fiber-optimize-btn">优化工艺参数</button>
                        </div>
                        <div class="optimization-result" id="optimization-result" style="display:none"></div>
                        <div class="fiber-compare-section" id="fiber-compare-section" style="display:none">
                            <h4>多纤维对比</h4>
                            <div class="compare-controls">
                                <label>对比支数 (tex):
                                    <input type="number" id="compare-yarn-count" value="100">
                                </label>
                                <button class="btn btn-secondary" id="fiber-compare-btn">对比选中纤维</button>
                            </div>
                            <div id="fiber-compare-result"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderFiberList() {
        const container = document.getElementById('fiber-list');
        if (!container) return;

        container.innerHTML = this.fibers.map(f => `
            <div class="fiber-item" data-type="${f.fiber_type}" style="border-left:4px solid ${f.color}">
                <div class="fiber-color-dot" style="background:${f.color}"></div>
                <div class="fiber-info">
                    <div class="fiber-name">${f.fiber_name}</div>
                    <div class="fiber-origin">${f.origin}</div>
                    <div class="fiber-spec">细度:${f.fineness_dtex}dtex · 长度:${f.fiber_length_mm_avg}mm</div>
                </div>
                <input type="checkbox" class="fiber-compare-check" value="${f.fiber_type}">
            </div>
        `).join('');

        container.querySelectorAll('.fiber-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('fiber-compare-check')) return;
                container.querySelectorAll('.fiber-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                this._showFiberDetail(item.dataset.type);
            });
        });

        document.getElementById('fiber-optimize-btn').addEventListener('click', () => this._runOptimization());
        document.getElementById('fiber-compare-btn').addEventListener('click', () => this._runComparison());
    }

    async _showFiberDetail(fiberType) {
        const detail = await this.api.getFiberDetail(fiberType);
        this.currentFiber = fiberType;

        document.getElementById('optimization-form').style.display = 'block';
        document.getElementById('fiber-compare-section').style.display = 'block';

        const typicalRange = detail.typical_count_tex_range;
        document.getElementById('fiber-yarn-count').placeholder = `推荐 ${typicalRange[0]}-${typicalRange[1]} tex`;

        document.getElementById('fiber-detail').innerHTML = `
            <div class="fiber-detail-card">
                <div class="fiber-detail-header">
                    <div class="fiber-color-block" style="background:${detail.color}"></div>
                    <div>
                        <h4>${detail.fiber_name}</h4>
                        <div class="fiber-latin">${detail.scientific_name}</div>
                        <div class="fiber-origin">${detail.origin} · ${detail.color}</div>
                    </div>
                </div>
                <div class="fiber-detail-grid">
                    <div class="detail-item"><label>纤维长度</label><span>${detail.fiber_length_mm.min}-${detail.fiber_length_mm.max}mm (平均${detail.fiber_length_mm.avg}mm)</span></div>
                    <div class="detail-item"><label>纤维直径</label><span>${detail.fiber_diameter_um} μm</span></div>
                    <div class="detail-item"><label>线密度</label><span>${detail.fineness_dtex} dtex</span></div>
                    <div class="detail-item"><label>密度</label><span>${detail.density_g_cm3} g/cm³</span></div>
                    <div class="detail-item"><label>断裂强度</label><span>${detail.breaking_tenacity_cn_dtex} cN/dtex</span></div>
                    <div class="detail-item"><label>断裂伸长</label><span>${detail.elongation_at_break_percent}%</span></div>
                    <div class="detail-item"><label>回潮率</label><span>${detail.moisture_regain_percent}%</span></div>
                    <div class="detail-item"><label>初始模量</label><span>${detail.modulus_gpa} GPa</span></div>
                    <div class="detail-item"><label>摩擦系数</label><span>${detail.friction_coefficient}</span></div>
                    <div class="detail-item"><label>卷曲度</label><span>${detail.crimp_percent}%</span></div>
                    <div class="detail-item"><label>推荐捻系数</label><span>${detail.recommended_twist_factor_range[0]}-${detail.recommended_twist_factor_range[1]}</span></div>
                    <div class="detail-item"><label>推荐牵伸倍数</label><span>${detail.recommended_draft_range[0]}-${detail.recommended_draft_range[1]}倍</span></div>
                    <div class="detail-item"><label>最高锭速</label><span>${detail.max_spindle_speed_rpm} rpm</span></div>
                    <div class="detail-item"><label>常用纱支范围</label><span>${detail.typical_count_tex_range[0]}-${detail.typical_count_tex_range[1]} tex</span></div>
                </div>
                <p class="fiber-desc">${detail.description}</p>
            </div>
        `;
    }

    async _runOptimization() {
        if (!this.currentFiber) return;
        const yarnCount = parseFloat(document.getElementById('fiber-yarn-count').value);
        const rovingCount = parseFloat(document.getElementById('fiber-roving-count').value);
        const priority = document.getElementById('fiber-quality-priority').value;

        const result = await this.api.optimizeFiberParameters({
            fiber_type: this.currentFiber,
            yarn_count_tex: yarnCount,
            roving_count_tex: rovingCount,
            quality_priority: priority
        });

        if (result.error) {
            document.getElementById('optimization-result').innerHTML = `<div class="error">${result.error}</div>`;
            return;
        }

        document.getElementById('optimization-result').style.display = 'block';
        document.getElementById('optimization-result').innerHTML = `
            <h4>✅ 优化结果 <span class="score-badge">综合评分: ${(result.overall_optimization_score * 100).toFixed(1)}分</span></h4>
            ${result.warnings?.length ? `<div class="warnings">⚠️ ${result.warnings.join('；')}</div>` : ''}
            <div class="opt-groups">
                <div class="opt-group">
                    <h5>🔄 加捻参数</h5>
                    <div class="detail-item"><label>捻系数</label><span>${result.twist_parameters.twist_factor} (推荐${result.twist_parameters.twist_factor_range[0]}-${result.twist_parameters.twist_factor_range[1]})</span></div>
                    <div class="detail-item"><label>捻度</label><span>${result.twist_parameters.twist_per_meter} 捻/m (${result.twist_parameters.twist_per_inch} TPI)</span></div>
                    <div class="detail-item"><label>捻向</label><span>${result.twist_parameters.twist_direction}捻</span></div>
                    <div class="detail-item"><label>捻回角</label><span>${result.twist_parameters.twist_angle_deg}°</span></div>
                </div>
                <div class="opt-group">
                    <h5>📏 牵伸参数</h5>
                    <div class="detail-item"><label>实际牵伸倍数</label><span>${result.draft_parameters.actual_draft_ratio}倍</span></div>
                    <div class="detail-item"><label>推荐牵伸范围</label><span>${result.draft_parameters.recommended_draft_range[0]}-${result.draft_parameters.recommended_draft_range[1]}倍</span></div>
                    <div class="detail-item"><label>牵伸效率</label><span>${(result.draft_parameters.draft_efficiency * 100).toFixed(1)}%</span></div>
                    <div class="detail-item"><label>断头风险</label><span class="${result.draft_parameters.breakage_risk_percent > 3 ? 'high-risk' : ''}">${result.draft_parameters.breakage_risk_percent}%</span></div>
                    <div class="detail-item"><label>罗拉压力</label><span>${result.draft_parameters.roller_pressure_n} N</span></div>
                    <div class="detail-item"><label>建议</label><span>${result.draft_parameters.advice}</span></div>
                </div>
                <div class="opt-group">
                    <h5>⚙️ 锭子参数</h5>
                    <div class="detail-item"><label>推荐锭速</label><span>${result.spindle_parameters.recommended_spindle_rpm} rpm (上限${result.spindle_parameters.max_allowed_rpm})</span></div>
                    <div class="detail-item"><label>输出速度</label><span>${result.spindle_parameters.delivery_speed_m_min} m/min</span></div>
                    <div class="detail-item"><label>钢丝圈重量</label><span>${result.spindle_parameters.traveler_mass_mg} mg</span></div>
                    <div class="detail-item"><label>单锭产量</label><span>${result.spindle_parameters.production_rate_g_per_hour_per_spindle} g/h</span></div>
                    <div class="detail-item"><label>纺纱张力</label><span>${result.spindle_parameters.spinning_tension_cn} cN</span></div>
                </div>
            </div>
        `;
    }

    async _runComparison() {
        const checks = document.querySelectorAll('.fiber-compare-check:checked');
        const fiberTypes = Array.from(checks).map(c => c.value);
        if (fiberTypes.length < 2) {
            alert('请至少选择2种纤维进行对比');
            return;
        }
        const yarnCount = parseFloat(document.getElementById('compare-yarn-count').value) || 100;

        const result = await this.api.compareFibers({
            fiber_types: fiberTypes,
            yarn_count_tex: yarnCount
        });

        const container = document.getElementById('fiber-compare-result');
        container.innerHTML = `
            <h5>对比结论：最优产量 - ${result.comparison.highest_production} | 最低断头 - ${result.comparison.lowest_breakage} | 综合最佳 - ${result.comparison.best_overall}</h5>
            <div class="compare-table-wrap">
                <table class="compare-table">
                    <thead><tr>
                        <th>纤维</th>
                        <th>捻度(捻/m)</th>
                        <th>牵伸倍数</th>
                        <th>锭速(rpm)</th>
                        <th>产量(g/h·锭)</th>
                        <th>断头风险(%)</th>
                        <th>综合评分</th>
                    </tr></thead>
                    <tbody>
                        ${result.fibers.map(f => `
                            <tr>
                                <td><strong>${f.fiber_info.fiber_name}</strong></td>
                                <td>${f.twist_parameters.twist_per_meter}</td>
                                <td>${f.draft_parameters.actual_draft_ratio}</td>
                                <td>${f.spindle_parameters.recommended_spindle_rpm}</td>
                                <td>${f.spindle_parameters.production_rate_g_per_hour_per_spindle}</td>
                                <td class="${f.draft_parameters.breakage_risk_percent > 3 ? 'high-risk' : ''}">${f.draft_parameters.breakage_risk_percent}</td>
                                <td><strong>${(f.overall_optimization_score * 100).toFixed(1)}</strong></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}
