let queueHistoryChart = null;
let volumeChart = null;

// Configuration
const CONFIG = {
    retryAttempts: 3,
    retryDelay: 2000,
    updateInterval: 5000,
    historyInterval: 60000
};

const CHART_DEFAULTS = {
    animation: {
        duration: 750,
        easing: 'easeInOutQuart',
        delay: (context) => context.dataIndex * 50
    },
    transitions: {
        active: {
            animation: {
                duration: 400
            }
        }
    },
    emptyState: {
        animation: {
            duration: 600,
            easing: 'easeOutCubic'
        },
        font: {
            size: 16,
            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial'
        },
        color: 'rgba(150, 150, 150, 0.7)',
        padding: { top: 40 }
    }
};

async function fetchWithRetry(url, attempts = CONFIG.retryAttempts) {
    let lastError = null;
    
    for (let i = 0; i < attempts; i++) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            // Don't log error for empty data, it's a valid state
            return data;
        } catch (error) {
            lastError = error;
            if (i === attempts - 1) {
                // Only log actual errors, not empty states
                if (!(error instanceof SyntaxError)) {
                    console.warn(`Failed to fetch ${url}:`, error.message);
                }
                return [];
            }
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
        }
    }
    return [];
}

function createEmptyStateChart(ctx, message) {
    return new Chart(ctx, {
        type: 'line',
        data: { datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: CHART_DEFAULTS.emptyState.animation,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: message,
                    font: CHART_DEFAULTS.emptyState.font,
                    color: CHART_DEFAULTS.emptyState.color,
                    padding: CHART_DEFAULTS.emptyState.padding
                }
            }
        }
    });
}

function cleanupChart(chart) {
    if (chart) {
        chart.destroy();
    }
    return null;
}

async function updateQueueStats() {
    try {
        const data = await fetchWithRetry('/api/queue-stats');
        
        // Update queue stats
        const queue = data?.queue || {};
        for (const [key, value] of Object.entries(queue)) {
            const element = document.getElementById(`${key}-count`);
            if (element) {
                element.textContent = value;
            }
        }

        // Update processing stats
        const processing = data?.processing;
        if (processing) {
            const elements = {
                'avg-processing-time': processing.avg_processing_time.toFixed(2) + 's',
                'total-processed': processing.total_processed,
                'success-rate': processing.success_rate.toFixed(1) + '%'
            };

            for (const [id, value] of Object.entries(elements)) {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            }

            if (processing.hourly_volume) {
                updateVolumeChart(processing.hourly_volume);
            }
        }
    } catch (error) {
        console.warn('Queue stats temporarily unavailable:', error.message);
    }
}

async function updateQueueHistory() {
    const chartContainer = document.getElementById('queueHistoryChart');
    if (!chartContainer) return;

    try {
        const data = await fetchWithRetry('/api/queue-history');
        
        if (!Array.isArray(data) || data.length === 0) {
            queueHistoryChart = cleanupChart(queueHistoryChart);
            queueHistoryChart = createEmptyStateChart(
                chartContainer.getContext('2d'),
                'Queue is currently empty'
            );
            return;
        }

        const timestamps = data.map(point => {
            const date = new Date(point.timestamp * 1000);
            return date.toLocaleTimeString();
        });

        const datasets = [
            {
                label: 'Queued',
                data: data.map(point => point.queued || 0),
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            },
            {
                label: 'Processing',
                data: data.map(point => point.started || 0),
                borderColor: 'rgb(255, 205, 86)',
                tension: 0.1
            },
            {
                label: 'Failed',
                data: data.map(point => point.failed || 0),
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }
        ];

        queueHistoryChart = cleanupChart(queueHistoryChart);
        queueHistoryChart = new Chart(chartContainer.getContext('2d'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: CHART_DEFAULTS.animation,
                transitions: CHART_DEFAULTS.transitions,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    } catch (error) {
        console.warn('Queue history temporarily unavailable:', error.message);
        queueHistoryChart = cleanupChart(queueHistoryChart);
        queueHistoryChart = createEmptyStateChart(
            chartContainer.getContext('2d'),
            'Queue monitoring temporarily unavailable'
        );
    }
}

function updateVolumeChart(volumeData) {
    const chartContainer = document.getElementById('volumeChart');
    if (!chartContainer) return;

    if (!Array.isArray(volumeData) || volumeData.length === 0) {
        volumeChart = cleanupChart(volumeChart);
        volumeChart = createEmptyStateChart(
            chartContainer.getContext('2d'),
            'No messages processed yet'
        );
        return;
    }

    const labels = volumeData.map(item => {
        const hour = item.hour.split('-')[3];
        return `${hour}:00`;
    }).reverse();

    const data = volumeData.map(item => item.count || 0).reverse();

    volumeChart = cleanupChart(volumeChart);
    volumeChart = new Chart(chartContainer.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Message Volume',
                data: data,
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                borderColor: 'rgb(75, 192, 192)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: CHART_DEFAULTS.animation,
            transitions: CHART_DEFAULTS.transitions,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// Update stats at regular intervals
let queueStatsInterval = null;
let queueHistoryInterval = null;

function startIntervals() {
    if (!queueStatsInterval) {
        queueStatsInterval = setInterval(updateQueueStats, CONFIG.updateInterval);
    }
    if (!queueHistoryInterval) {
        queueHistoryInterval = setInterval(updateQueueHistory, CONFIG.historyInterval);
    }
}

function stopIntervals() {
    if (queueStatsInterval) {
        clearInterval(queueStatsInterval);
        queueStatsInterval = null;
    }
    if (queueHistoryInterval) {
        clearInterval(queueHistoryInterval);
        queueHistoryInterval = null;
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    updateQueueStats();
    updateQueueHistory();
    startIntervals();
});

// Cleanup on page unload
window.addEventListener('unload', () => {
    stopIntervals();
    cleanupChart(queueHistoryChart);
    cleanupChart(volumeChart);
});

// Handle visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopIntervals();
    } else {
        updateQueueStats();
        updateQueueHistory();
        startIntervals();
    }
});
