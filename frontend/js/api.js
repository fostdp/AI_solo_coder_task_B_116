class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl || 'http://localhost:8000';
        this.ws = null;
        this.wsConnected = false;
        this.apiConnected = false;
        this.dataCallbacks = [];
        this.alarmCallbacks = [];
        this.connectionCallbacks = [];
    }

    setBaseUrl(url) {
        this.baseUrl = url;
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/api/health`);
            const data = await response.json();
            this.apiConnected = data.status === 'healthy';
            this._notifyConnection('api', this.apiConnected);
            return data;
        } catch (e) {
            this.apiConnected = false;
            this._notifyConnection('api', false);
            throw e;
        }
    }

    async getData() {
        try {
            const response = await fetch(`${this.baseUrl}/api/data`);
            return await response.json();
        } catch (e) {
            console.error('Failed to get data:', e);
            throw e;
        }
    }

    async runDynamics(params) {
        try {
            const response = await fetch(`${this.baseUrl}/api/dynamics`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            return await response.json();
        } catch (e) {
            console.error('Failed to run dynamics:', e);
            throw e;
        }
    }

    async runOptimization(params) {
        try {
            const response = await fetch(`${this.baseUrl}/api/optimize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            return await response.json();
        } catch (e) {
            console.error('Failed to run optimization:', e);
            throw e;
        }
    }

    async getAlarms(params = {}) {
        try {
            const query = new URLSearchParams(params).toString();
            const response = await fetch(`${this.baseUrl}/api/alarms?${query}`);
            return await response.json();
        } catch (e) {
            console.error('Failed to get alarms:', e);
            throw e;
        }
    }

    connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                const wsUrl = this.baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
                this.ws = new WebSocket(`${wsUrl}/api/websocket`);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.wsConnected = true;
                    this._notifyConnection('websocket', true);
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'data') {
                            this._notifyData(msg.data);
                        }
                    } catch (e) {
                        console.error('Failed to parse WS message:', e);
                    }
                };

                this.ws.onerror = (e) => {
                    console.error('WebSocket error:', e);
                    this.wsConnected = false;
                    this._notifyConnection('websocket', false);
                    reject(e);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.wsConnected = false;
                    this._notifyConnection('websocket', false);
                };
            } catch (e) {
                reject(e);
            }
        });
    }

    disconnectWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.wsConnected = false;
            this._notifyConnection('websocket', false);
        }
    }

    sendWsMessage(type, data = {}) {
        if (this.ws && this.wsConnected) {
            this.ws.send(JSON.stringify({ type, ...data }));
        }
    }

    onData(callback) {
        this.dataCallbacks.push(callback);
    }

    onAlarm(callback) {
        this.alarmCallbacks.push(callback);
    }

    onConnection(callback) {
        this.connectionCallbacks.push(callback);
    }

    _notifyData(data) {
        this.dataCallbacks.forEach(cb => {
            try { cb(data); } catch (e) { console.error(e); }
        });
    }

    _notifyAlarm(alarm) {
        this.alarmCallbacks.forEach(cb => {
            try { cb(alarm); } catch (e) { console.error(e); }
        });
    }

    _notifyConnection(type, connected) {
        this.connectionCallbacks.forEach(cb => {
            try { cb(type, connected); } catch (e) { console.error(e); }
        });
    }

    isApiConnected() {
        return this.apiConnected;
    }

    isWsConnected() {
        return this.wsConnected;
    }

    // ========== 历史纺车对比 API ==========
    async getHistoricalWheels() {
        const res = await fetch(`${this.baseUrl}/api/historical/wheels`);
        return await res.json();
    }

    async getHistoricalWheelDetail(wheelType) {
        const res = await fetch(`${this.baseUrl}/api/historical/wheels/${wheelType}`);
        return await res.json();
    }

    async compareHistoricalWheels(params = {}) {
        const res = await fetch(`${this.baseUrl}/api/historical/comparison`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    // ========== 纤维参数优化 API ==========
    async getFibers() {
        const res = await fetch(`${this.baseUrl}/api/fibers`);
        return await res.json();
    }

    async getFiberDetail(fiberType) {
        const res = await fetch(`${this.baseUrl}/api/fibers/${fiberType}`);
        return await res.json();
    }

    async optimizeFiberParameters(params) {
        const res = await fetch(`${this.baseUrl}/api/fibers/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    async compareFibers(params) {
        const res = await fetch(`${this.baseUrl}/api/fibers/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    // ========== 断头检测与自动生头 API ==========
    async simulateBreak(params) {
        const res = await fetch(`${this.baseUrl}/api/detection/simulate-break`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    async getVisionStatus() {
        const res = await fetch(`${this.baseUrl}/api/detection/vision-status`);
        return await res.json();
    }

    async getRobotStatus() {
        const res = await fetch(`${this.baseUrl}/api/detection/robot-status`);
        return await res.json();
    }

    async getDetectionStats(windowSeconds = null) {
        const query = windowSeconds ? `?window_seconds=${windowSeconds}` : '';
        const res = await fetch(`${this.baseUrl}/api/detection/statistics${query}`);
        return await res.json();
    }

    async getSpindleStatus() {
        const res = await fetch(`${this.baseUrl}/api/detection/spindle-status`);
        return await res.json();
    }

    // ========== 公众虚拟纺纱体验 API ==========
    async createVirtualSpinningSession(params = {}) {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    async controlVirtualSpinning(params) {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await res.json();
    }

    async getVirtualSpinningSnapshot(sessionId) {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/snapshot/${sessionId}`);
        return await res.json();
    }

    async closeVirtualSpinningSession(sessionId) {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/session/${sessionId}`, {
            method: 'DELETE'
        });
        return await res.json();
    }

    async getVirtualSpinningStats() {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/statistics`);
        return await res.json();
    }

    async getVirtualSpinningFiberOptions() {
        const res = await fetch(`${this.baseUrl}/api/virtual-spinning/fiber-options`);
        return await res.json();
    }
}

const apiClient = new ApiClient();
