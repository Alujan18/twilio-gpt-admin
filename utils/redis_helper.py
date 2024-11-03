import redis
from config import Config

redis_client = redis.from_url(Config.REDIS_URL)

def enqueue_message(message_id):
    redis_client.rpush('message_queue', message_id)

def get_next_message():
    return redis_client.lpop('message_queue')

def get_queue_length():
    return redis_client.llen('message_queue')

def get_queue_metrics():
    return {
        'queue_length': get_queue_length(),
        'processed_messages': redis_client.get('processed_messages') or 0,
        'failed_messages': redis_client.get('failed_messages') or 0
    }
