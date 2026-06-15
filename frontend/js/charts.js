class ChartManager {
    constructor() {
        this.twistChart = null;
        this.efficiencyChart = null;
        this.maxDataPoints = 20;
        this.timeLabels = [];
        this.speedData = [];
        this.twistData = [];
        
        this.initCharts();
    }

    initCharts() {
        this.initTwistChart();
        this.initEfficiencyChart();
    }

    initTwistChart() {
        const ctx = document.getElementById('twist-chart').getContext('2d');
        
        this.twistChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '水轮转速 (rpm)',
                        data: [],
                        borderColor: '#e94560',
                        backgroundColor: 'rgba(233, 69, 96, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: '纱线捻度 (T/m)',
                        data: [],
                        borderColor: '#64ffda',
                        backgroundColor: 'rgba(100, 255, 218, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 300
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#8892b0',
                            font: {
                                size: 10
                            },
                            boxWidth: 12
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 33, 62, 0.9)',
                        titleColor: '#e94560',
                        bodyColor: '#e0e0e0',
                        borderColor: '#e94560',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(136, 146, 176, 0.1)'
                        },
                        ticks: {
                            color: '#8892b0',
                            font: {
                                size: 9
                            },
                            maxTicksLimit: 6
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '转速 (rpm)',
                            color: '#e94560',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            color: 'rgba(136, 146, 176, 0.1)'
                        },
                        ticks: {
                            color: '#8892b0',
                            font: {
                                size: 9
                            }
                        },
                        min: 0,
                        max: 120
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '捻度 (T/m)',
                            color: '#64ffda',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#8892b0',
                            font: {
                                size: 9
                            }
                        },
                        min: 0,
                        max: 120
                    }
                }
            }
        });
    }

    initEfficiencyChart() {
        const ctx = document.getElementById('efficiency-chart').getContext('2d');
        
        this.efficiencyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['水轮效率', '传动效率', '纺纱效率', '综合能效'],
                datasets: [{
                    label: '效率 (%)',
                    data: [75, 82, 68, 55],
                    backgroundColor: [
                        'rgba(233, 69, 96, 0.7)',
                        'rgba(100, 255, 218, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ],
                    borderColor: [
                        '#e94560',
                        '#64ffda',
                        '#ffce56',
                        '#9966ff'
                    ],
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 500
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 33, 62, 0.9)',
                        titleColor: '#e94560',
                        bodyColor: '#e0e0e0',
                        borderColor: '#e94560',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                return `效率: ${context.parsed.y.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#8892b0',
                            font: {
                                size: 9
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(136, 146, 176, 0.1)'
                        },
                        ticks: {
                            color: '#8892b0',
                            font: {
                                size: 9
                            },
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    updateTwistChart(speed, twist, time) {
        const timeLabel = time.toFixed(1) + 's';
        
        this.twistChart.data.labels.push(timeLabel);
        this.twistChart.data.datasets[0].data.push(speed);
        this.twistChart.data.datasets[1].data.push(twist);

        if (this.twistChart.data.labels.length > this.maxDataPoints) {
            this.twistChart.data.labels.shift();
            this.twistChart.data.datasets[0].data.shift();
            this.twistChart.data.datasets[1].data.shift();
        }

        this.twistChart.update('none');
    }

    updateEfficiencyChart(speed) {
        const waterWheelEff = Math.min(85, 60 + speed * 0.25);
        const transmissionEff = Math.min(90, 70 + speed * 0.2);
        const spinningEff = Math.min(75, 55 + speed * 0.2);
        const overallEff = waterWheelEff * transmissionEff * spinningEff / 10000;

        this.efficiencyChart.data.datasets[0].data = [
            waterWheelEff,
            transmissionEff,
            spinningEff,
            overallEff
        ];

        this.efficiencyChart.update('none');
    }

    updateCharts(speed, twist, time) {
        this.updateTwistChart(speed, twist, time);
        this.updateEfficiencyChart(speed);
    }
}
