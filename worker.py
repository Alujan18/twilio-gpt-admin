import os
import logging
from rq import Worker, Queue
from utils.redis_helper import RedisHelper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_worker():
    redis_helper = RedisHelper()
    redis_conn = redis_helper.get_connection()
    
    if not redis_conn:
        logger.error("Failed to connect to Redis - worker cannot start")
        return None, None
        
    try:
        queue = Queue('messages', connection=redis_conn)
        worker = Worker([queue], connection=redis_conn)
        logger.info("Worker initialized successfully")
        return queue, worker
    except Exception as e:
        logger.error(f"Error initializing worker: {str(e)}")
        return None, None

if __name__ == '__main__':
    queue, worker = initialize_worker()
    if worker:
        try:
            logger.info("Starting worker...")
            worker.work()
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
    else:
        logger.error("Failed to start worker due to initialization errors")
