from utils.redis_helper import get_next_message
from utils.message_handler import process_message
import time

def run_worker():
    while True:
        message_id = get_next_message()
        if message_id:
            try:
                process_message(message_id.decode('utf-8'))
            except Exception as e:
                print(f"Error processing message {message_id}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    run_worker()
