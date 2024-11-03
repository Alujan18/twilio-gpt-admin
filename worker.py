import os
import redis
from rq import Worker, Queue

redis_conn = redis.Redis(host='0.0.0.0', port=6379)

if __name__ == '__main__':
    queue = Queue('messages', connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    worker.work()
