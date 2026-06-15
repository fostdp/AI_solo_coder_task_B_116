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
}

const apiClient = new ApiClient();
