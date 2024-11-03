import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_queue_stats(queue):
    """Get detailed queue statistics"""
    try:
        return {
            'queued': len(queue),
            'failed': len(queue.failed_job_registry),
            'finished': len(queue.finished_job_registry),
            'started': len(queue.started_job_registry),
            'deferred': len(queue.deferred_job_registry),
            'scheduled': len(queue.scheduled_job_registry)
        }
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        return {
            'queued': 0,
            'failed': 0,
            'finished': 0,
            'started': 0,
            'deferred': 0,
            'scheduled': 0
        }

def get_queue_history(redis_conn, period_hours=24) -> List[Dict]:
    """Get queue history for the specified period"""
    try:
        if not redis_conn:
            logger.warning("Redis connection not available")
            return []

        now = datetime.utcnow()
        start_time = now - timedelta(hours=period_hours)
        history_key = "queue:history"
        
        # Get all history points within the time range
        raw_history = redis_conn.zrangebyscore(
            history_key,
            start_time.timestamp(),
            now.timestamp()
        )
        
        if not raw_history:
            logger.info("No queue history data found for the specified period")
            return []
            
        history_data = []
        for point in raw_history:
            try:
                if isinstance(point, bytes):
                    point = point.decode('utf-8')
                data = json.loads(point)
                # Ensure all required fields exist
                required_fields = ['timestamp', 'queued', 'started', 'failed']
                if all(field in data for field in required_fields):
                    history_data.append(data)
                else:
                    logger.warning(f"Skipping malformed history point: missing required fields")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding history point: {str(e)}")
                continue
            except UnicodeDecodeError as e:
                logger.error(f"Error decoding bytes to string: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing history point: {str(e)}")
                continue
                
        return history_data
    except Exception as e:
        logger.error(f"Error fetching queue history: {str(e)}")
        return []

def record_queue_stats(redis_conn, queue):
    """Record current queue statistics for historical tracking"""
    try:
        if not redis_conn:
            logger.warning("Redis connection not available - skipping stats recording")
            return

        stats = get_queue_stats(queue)
        stats['timestamp'] = datetime.utcnow().timestamp()
        
        # Store in a sorted set with timestamp as score
        redis_conn.zadd(
            "queue:history",
            {json.dumps(stats): stats['timestamp']}
        )
        
        # Trim old entries (keep last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        redis_conn.zremrangebyscore(
            "queue:history",
            0,
            week_ago.timestamp()
        )
        logger.info("Queue stats recorded successfully")
    except Exception as e:
        logger.error(f"Error recording queue stats: {str(e)}")

def get_processing_stats(redis_conn) -> Dict:
    """Get message processing statistics"""
    try:
        if not redis_conn:
            logger.warning("Redis connection not available")
            return get_default_processing_stats()

        stats_key = "processing:stats"
        raw_stats = redis_conn.get(stats_key)
        
        if raw_stats:
            try:
                return json.loads(raw_stats)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding processing stats: {str(e)}")
                return get_default_processing_stats()
        return get_default_processing_stats()
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}")
        return get_default_processing_stats()

def get_default_processing_stats() -> Dict:
    """Return default processing stats structure"""
    return {
        'avg_processing_time': 0,
        'total_processed': 0,
        'success_rate': 100,
        'hourly_volume': []
    }

def update_processing_stats(redis_conn, processing_time: float, success: bool):
    """Update message processing statistics"""
    try:
        if not redis_conn:
            logger.warning("Redis connection not available - skipping stats update")
            return

        stats_key = "processing:stats"
        stats = get_processing_stats(redis_conn)
        
        # Update average processing time
        total_time = stats['avg_processing_time'] * stats['total_processed']
        stats['total_processed'] += 1
        stats['avg_processing_time'] = (total_time + processing_time) / stats['total_processed']
        
        # Update success rate
        success_count = (stats['success_rate'] / 100) * (stats['total_processed'] - 1)
        if success:
            success_count += 1
        stats['success_rate'] = (success_count / stats['total_processed']) * 100
        
        # Update hourly volume
        current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
        volume_key = f"processing:volume:{current_hour}"
        
        try:
            redis_conn.incr(volume_key)
            redis_conn.expire(volume_key, 86400)  # Expire after 24 hours
        except Exception as e:
            logger.error(f"Error updating volume stats: {str(e)}")
        
        # Get last 24 hours volume
        hourly_volume = []
        for i in range(24):
            hour_key = (datetime.utcnow() - timedelta(hours=i)).strftime('%Y-%m-%d-%H')
            try:
                count = redis_conn.get(f"processing:volume:{hour_key}")
                hourly_volume.append({
                    'hour': hour_key,
                    'count': int(count) if count else 0
                })
            except Exception as e:
                logger.error(f"Error fetching volume for hour {hour_key}: {str(e)}")
                hourly_volume.append({'hour': hour_key, 'count': 0})
        
        stats['hourly_volume'] = hourly_volume
        
        # Save updated stats
        try:
            redis_conn.set(stats_key, json.dumps(stats))
        except Exception as e:
            logger.error(f"Error saving processing stats: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating processing stats: {str(e)}")
