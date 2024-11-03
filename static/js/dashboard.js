let queueHistoryChart = null;
let volumeChart = null;

// Configuration
const CONFIG = {
    retryAttempts: 3,
    retryDelay: 2000,
    updateInterval: 5000,
    historyInterval: 60000
};

async function fetchWithRetry(url, attempts = CONFIG.retryAttempts) {
    for (let i = 0; i < attempts; i++) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            if (i === attempts - 1) throw error;
            console.warn(`Attempt ${i + 1} failed, retrying after ${CONFIG.retryDelay}ms...`);
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
        }
    }
}

async function updateQueueStats() {
    try {
        const data = await fetchWithRetry('/api/queue-stats');
        
        // Update queue stats
        const queue = data.queue;
        for (const [key, value] of Object.entries(queue)) {
            const element = document.getElementById(`${key}-count`);
            if (element) element.textContent = value;
        }

        // Update processing stats
        const processing = data.processing;
        if (processing) {
            document.getElementById('avg-processing-time').textContent = 
                processing.avg_processing_time.toFixed(2) + 's';
            document.getElementById('total-processed').textContent = 
                processing.total_processed;
            document.getElementById('success-rate').textContent = 
                processing.success_rate.toFixed(1) + '%';

            // Update volume chart if data available
            if (processing.hourly_volume) {
                updateVolumeChart(processing.hourly_volume);
            }
        }
    } catch (error) {
        console.error('Error updating queue stats:', error);
    }
}

async function updateQueueHistory() {
    try {
        const data = await fetchWithRetry('/api/queue-history');
        
        if (!Array.isArray(data) || data.length === 0) {
            if (queueHistoryChart) {
                queueHistoryChart.destroy();
                queueHistoryChart = null;
            }
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

        if (queueHistoryChart) {
            queueHistoryChart.destroy();
        }

        const ctx = document.getElementById('queueHistoryChart').getContext('2d');
        queueHistoryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
        console.error('Error updating queue history:', error);
        // Keep the existing chart if there's an error
    }
}

function updateVolumeChart(volumeData) {
    if (!Array.isArray(volumeData) || volumeData.length === 0) {
        if (volumeChart) {
            volumeChart.destroy();
            volumeChart = null;
        }
        return;
    }

    const labels = volumeData.map(item => {
        const hour = item.hour.split('-')[3];
        return `${hour}:00`;
    }).reverse();

    const data = volumeData.map(item => item.count || 0).reverse();

    if (volumeChart) {
        volumeChart.destroy();
    }

    const ctx = document.getElementById('volumeChart').getContext('2d');
    volumeChart = new Chart(ctx, {
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
const queueStatsInterval = setInterval(updateQueueStats, CONFIG.updateInterval);
const queueHistoryInterval = setInterval(updateQueueHistory, CONFIG.historyInterval);

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    updateQueueStats();
    updateQueueHistory();
});

// Cleanup on page unload
window.addEventListener('unload', () => {
    clearInterval(queueStatsInterval);
    clearInterval(queueHistoryInterval);
});
