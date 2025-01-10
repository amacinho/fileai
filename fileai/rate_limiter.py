from collections import deque
import time
import logging

class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls  # Maximum calls allowed in the time window
        self.time_window = time_window  # Time window in seconds
        self.calls = deque()  # Queue to track timestamps of calls

    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit"""
        now = time.time()

        # Remove timestamps older than our time window
        while self.calls and now - self.calls[0] >= self.time_window:
            self.calls.popleft()

        current_calls = len(self.calls)
        logging.info(f"Rate limit status: {
                     current_calls}/{self.max_calls} calls in the last {self.time_window} seconds")

        # If we've hit our limit, wait until enough time has passed
        if current_calls >= self.max_calls:
            wait_time = self.calls[0] + self.time_window - now
            if wait_time > 0:
                logging.warning(f"Rate limit reached. Waiting {
                                wait_time:.2f} seconds before next call")
                time.sleep(wait_time)
                # After waiting, remove old timestamps again
                now = time.time()
                while self.calls and now - self.calls[0] >= self.time_window:
                    self.calls.popleft()
                logging.info(f"Resuming after wait. Current usage: {
                             len(self.calls)}/{self.max_calls} calls")

        # Add the current timestamp
        self.calls.append(now)
