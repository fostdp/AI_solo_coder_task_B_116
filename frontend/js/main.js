/**
 * main.js — 前端装配入口（薄 Glue 层）
 * 不包含业务逻辑，仅负责：
 *   1. 装配三大模块: SceneManager + SpinningFrame3D + EfficiencyPanelController
 *   2. 驱动 requestAnimationFrame 数据更新循环（模拟模式 vs API 模式）
 *   3. API 生命周期管理（connect/disconnect/data 回调）
 */
class App {
    constructor() {
        this.sceneManager = null;
        this.frame3d = null;
        this.panel = null;
        this.api = apiClient;
        this.lastUpdateTime = 0;

        this.init();
        this.bindControls();
        this.panel.bindGlobalControls(
            (data) => this.panel.showInfoPanel(data),
            () => this.runOptimization(),
        );
        this.panel.renderAlarms();
        this.startDataLoop();
    }

    init() {
        this.sceneManager = new SceneManager('three-container');
        this.frame3d = new SpinningFrame3D(this.sceneManager.scene);
        this.sceneManager.setSpinningWheel(this.frame3d);

        this.panel = new EfficiencyPanelController({
            sceneManager: this.sceneManager,
            spinningFrame: this.frame3d,
            chartManager: new ChartManager(),
            apiClient: this.api,
        });

        this.sceneManager.onComponentClick((data) => this.panel.showInfoPanel(data));
        this.sceneManager.setWaterVisible(true);
        this.frame3d.setYarnVisible(true);

        this.panel.writeDataDisplay();

        this.api.onData((data) => {
            this.panel.currentData = data;
            this.panel.writeApiData(data);
            if (data.alarms) {
                data.alarms.forEach(a => this.panel.pushAlarm(a));
            }
        });

        this.api.onConnection((type, connected) => {
            this.updateConnectionStatus(type, connected);
        });
    }

    bindControls() {
        // 顶层：use-api 切换、api-url 变更、panel 的 bindGlobalControls 已处理其他控件
        const useApi = document.getElementById('use-api');
        useApi.addEventListener('change', (e) => {
            this.panel.useApi = e.target.checked;
            if (this.panel.useApi) {
                this.connectApi();
            } else {
                this.disconnectApi();
            }
        });
    }

    async connectApi() {
        const url = document.getElementById('api-url').value;
        this.api.setBaseUrl(url);
        try {
            await this.api.checkHealth();
            document.getElementById('status').textContent = '连接中...';
            try {
                await this.api.connectWebSocket();
            } catch (e) {
                console.warn('WebSocket 失败，使用轮询', e);
            }
            const data = await this.api.getData();
            this.panel.currentData = data;
            if (data && !data.status) this.panel.writeApiData(data);
            document.getElementById('status').textContent = '运行中';
        } catch (e) {
            console.error('API 连接失败:', e);
            document.getElementById('use-api').checked = false;
            this.panel.useApi = false;
            alert('无法连接到后端 API，请确保服务已启动');
        }
    }

    disconnectApi() {
        this.api.disconnectWebSocket();
        this.panel.currentData = null;
        document.getElementById('status').textContent = '模拟模式';
    }

    updateConnectionStatus(type, connected) {
        const el = type === 'api'
            ? document.getElementById('api-status')
            : document.getElementById('ws-status');
        if (!el) return;
        const label = type === 'api' ? 'API' : 'WebSocket';
        el.textContent = connected ? `${label}已连接` : `${label}未连接`;
        el.className = 'status-indicator ' + (connected ? 'status-connected' : 'status-disconnected');
    }

    // rAF 数据更新：模拟模式本地计算，API 模式让 onData 回调触发
    startDataLoop() {
        const INTERVAL = 0.1;
        const loop = (t) => {
            const dt = (t - this.lastUpdateTime) / 1000;
            if (dt >= INTERVAL) {
                this.panel.elapsedTime += dt;
                if (!this.panel.useApi) {
                    this.panel.writeDataDisplay();
                    this.panel.updateChartsLocal();
                }
                this.lastUpdateTime = t;
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    async runOptimization() {
        const btn = document.getElementById('run-optimization');
        btn.disabled = true;
        btn.textContent = '优化中...';
        try {
            const params = this.panel.buildOptimizationPayload();
            const result = (this.panel.useApi && this.api.isApiConnected())
                ? await this.api.runOptimization(params)
                : this.panel.simulateOptimizationLocal(params);
            this.panel.renderOptimizationResult(result);
        } catch (e) {
            console.error('优化失败:', e);
            alert('优化计算失败: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '运行优化';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
