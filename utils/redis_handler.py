def get_queue_stats(queue):
    return {
        'queued': len(queue),
        'failed': len(queue.failed_job_registry),
        'finished': len(queue.finished_job_registry),
        'started': len(queue.started_job_registry)
    }
