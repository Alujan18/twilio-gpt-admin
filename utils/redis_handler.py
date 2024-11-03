import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from redis import RedisError, ResponseError

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

def _decode_history_point(point) -> Dict:
    """Helper function to decode and validate history points"""
    if isinstance(point, bytes):
        point = point.decode('utf-8')
    try:
        data = json.loads(point)
        
        # Ensure all required fields exist with default values
        default_data = {
            'timestamp': datetime.utcnow().timestamp(),
            'queued': 0,
            'started': 0,
            'failed': 0,
            'finished': 0,
            'deferred': 0,
            'scheduled': 0
        }
        
        # Update defaults with actual data, ensuring numeric values
        for key in default_data:
            if key in data:
                try:
                    default_data[key] = float(data[key]) if key == 'timestamp' else int(data[key])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid value for {key} in history point, using default")
        
        return default_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in history point: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing history point: {str(e)}")
        raise

def get_queue_history(redis_conn, period_hours=24) -> List[Dict]:
    """Get queue history for the specified period with improved error handling"""
    if not redis_conn:
        logger.warning("Redis connection not available")
        return []

    max_retries = 3
    retry_delay = 1  # seconds
    current_retry = 0

    while current_retry < max_retries:
        try:
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
                    decoded_point = _decode_history_point(point)
                    history_data.append(decoded_point)
                except Exception as e:
                    logger.warning(f"Skipping malformed history point: {str(e)}")
                    continue
            
            # Sort by timestamp and ensure we have at least some valid points
            if history_data:
                history_data.sort(key=lambda x: x['timestamp'])
                logger.info(f"Successfully retrieved {len(history_data)} history points")
                return history_data
            return []

        except RedisError as e:
            current_retry += 1
            logger.warning(f"Redis error on attempt {current_retry}/{max_retries}: {str(e)}")
            if current_retry < max_retries:
                time.sleep(retry_delay)
                continue
            logger.error("Max retries reached for queue history fetch")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in queue history: {str(e)}")
            return []

def record_queue_stats(redis_conn, queue):
    """Record current queue statistics for historical tracking"""
    if not redis_conn:
        logger.warning("Redis connection not available - skipping stats recording")
        return

    try:
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
    except RedisError as e:
        logger.error(f"Redis error recording queue stats: {str(e)}")
    except Exception as e:
        logger.error(f"Error recording queue stats: {str(e)}")

def get_processing_stats(redis_conn) -> Dict:
    """Get message processing statistics"""
    if not redis_conn:
        logger.warning("Redis connection not available")
        return get_default_processing_stats()

    try:
        stats_key = "processing:stats"
        raw_stats = redis_conn.get(stats_key)
        
        if raw_stats:
            try:
                return json.loads(raw_stats)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding processing stats: {str(e)}")
                return get_default_processing_stats()
        return get_default_processing_stats()
    except RedisError as e:
        logger.error(f"Redis error getting processing stats: {str(e)}")
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
    if not redis_conn:
        logger.warning("Redis connection not available - skipping stats update")
        return

    try:
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
        
        # Update hourly volume with improved error handling
        current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
        volume_key = f"processing:volume:{current_hour}"
        
        try:
            redis_conn.incr(volume_key)
            redis_conn.expire(volume_key, 86400)  # Expire after 24 hours
        except RedisError as e:
            logger.error(f"Error updating volume stats: {str(e)}")
        
        # Get last 24 hours volume with improved error handling
        hourly_volume = []
        for i in range(24):
            try:
                hour_key = (datetime.utcnow() - timedelta(hours=i)).strftime('%Y-%m-%d-%H')
                count = redis_conn.get(f"processing:volume:{hour_key}")
                hourly_volume.append({
                    'hour': hour_key,
                    'count': int(count) if count else 0
                })
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing volume count: {str(e)}")
                hourly_volume.append({'hour': hour_key, 'count': 0})
            except RedisError as e:
                logger.error(f"Redis error fetching volume: {str(e)}")
                hourly_volume.append({'hour': hour_key, 'count': 0})
        
        stats['hourly_volume'] = hourly_volume
        
        # Save updated stats
        try:
            redis_conn.set(stats_key, json.dumps(stats))
        except RedisError as e:
            logger.error(f"Redis error saving processing stats: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating processing stats: {str(e)}")
