import time
from datetime import datetime, timedelta
from threading import Lock

class RateLimiter:
    def __init__(self, calls_per_minute=30):
        self.calls_per_minute = calls_per_minute
        self.minute_calls = []
        self.last_call_time = 0
        
    def wait_if_needed(self):
        """Wait if we're close to rate limits"""
        current_time = time.time()
        
        # Always wait at least 12 seconds between calls
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < 12:
            sleep_time = 12 - time_since_last_call
            print(f"Waiting {sleep_time:.1f} seconds between calls...")
            time.sleep(sleep_time)
        
        # Clean up old timestamps
        minute_ago = current_time - 60
        self.minute_calls = [t for t in self.minute_calls if t > minute_ago]
        
        # Check if we need to wait
        if len(self.minute_calls) >= (self.calls_per_minute - 5):  # Buffer of 5 calls
            sleep_time = 60 - (current_time - self.minute_calls[0])
            print(f"Rate limit approaching, waiting {sleep_time:.1f} seconds...")
            time.sleep(max(1, sleep_time))
        
        # Update tracking
        current_time = time.time()
        self.minute_calls.append(current_time)
        self.last_call_time = current_time

    def get_remaining_calls(self):
        current_time = datetime.now()
        minute_calls = len([call for call in self.minute_calls 
                          if call > current_time - timedelta(minutes=1)])
        month_calls = len([call for call in self.month_calls 
                         if call > current_time - timedelta(days=30)])
        
        return {
            'minute_remaining': self.calls_per_minute - minute_calls,
            'month_remaining': self.calls_per_month - month_calls
        } 