let queueHistoryChart = null;
let volumeChart = null;

function updateQueueStats() {
    fetch('/api/queue-stats')
        .then(response => response.json())
        .then(data => {
            // Update queue stats
            const queue = data.queue;
            document.getElementById('queued-count').textContent = queue.queued;
            document.getElementById('started-count').textContent = queue.started;
            document.getElementById('finished-count').textContent = queue.finished;
            document.getElementById('failed-count').textContent = queue.failed;
            document.getElementById('deferred-count').textContent = queue.deferred;
            document.getElementById('scheduled-count').textContent = queue.scheduled;

            // Update processing stats
            const processing = data.processing;
            document.getElementById('avg-processing-time').textContent = 
                processing.avg_processing_time.toFixed(2) + 's';
            document.getElementById('total-processed').textContent = 
                processing.total_processed;
            document.getElementById('success-rate').textContent = 
                processing.success_rate.toFixed(1) + '%';

            // Update volume chart
            updateVolumeChart(processing.hourly_volume);
        })
        .catch(error => console.error('Error fetching queue stats:', error));
}

function updateQueueHistory() {
    fetch('/api/queue-history')
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) return;

            const timestamps = data.map(point => {
                const date = new Date(point.timestamp * 1000);
                return date.toLocaleTimeString();
            });

            const datasets = [
                {
                    label: 'Queued',
                    data: data.map(point => point.queued),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                },
                {
                    label: 'Processing',
                    data: data.map(point => point.started),
                    borderColor: 'rgb(255, 205, 86)',
                    tension: 0.1
                },
                {
                    label: 'Failed',
                    data: data.map(point => point.failed),
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
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Error fetching queue history:', error));
}

function updateVolumeChart(volumeData) {
    if (!volumeData || volumeData.length === 0) return;

    const labels = volumeData.map(item => {
        const hour = item.hour.split('-')[3];
        return `${hour}:00`;
    }).reverse();

    const data = volumeData.map(item => item.count).reverse();

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
            }
        }
    });
}

// Update stats every 5 seconds
setInterval(updateQueueStats, 5000);

// Update history every minute
setInterval(updateQueueHistory, 60000);

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    updateQueueStats();
    updateQueueHistory();
});
