function updateQueueStats() {
    fetch('/api/queue-stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('queued-count').textContent = data.queued;
            document.getElementById('started-count').textContent = data.started;
            document.getElementById('finished-count').textContent = data.finished;
            document.getElementById('failed-count').textContent = data.failed;
        });
}

// Update stats every 5 seconds
setInterval(updateQueueStats, 5000);
