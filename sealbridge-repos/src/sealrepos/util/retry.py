# src/sealrepos/util/retry.py: Decorators for retrying operations.
# This module provides decorators that implement an exponential backoff strategy
# with jitter. These can be applied to functions that perform network requests
# or other operations prone to transient failures, making the application more
# resilient.

import time
import random
from functools import wraps

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def rwb(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    if x < retries:
                        sleep = (backoff_in_seconds * 2 ** x +
                                 random.uniform(0, 1))
                        time.sleep(sleep)
                        x += 1
                    else:
                        raise e
        return wrapper
    return rwb
