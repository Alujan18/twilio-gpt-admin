// Auto-refresh dashboard data every 30 seconds
setInterval(() => {
    location.reload();
}, 30000);

// Initialize charts
document.addEventListener('DOMContentLoaded', function() {
    const queueCtx = document.getElementById('queueChart').getContext('2d');
    new Chart(queueCtx, {
        type: 'line',
        data: {
            labels: Array.from({length: 10}, (_, i) => i),
            datasets: [{
                label: 'Queue Length',
                data: queueData,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
