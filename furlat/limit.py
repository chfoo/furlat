'''Rate limiting'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import random
import threading
import time


class RateLimiter(object):
    FIVE_PER_MINUTE = 5 / 60.0

    def __init__(self, average_rate=FIVE_PER_MINUTE):
        super(RateLimiter, self).__init__()
        self._average_rate = average_rate

    def delay_time(self):
        return random.uniform(0.0, 1.0 / self._average_rate * 2)


class ExponentialLimiter(object):
    def __init__(self, max_time=3600.0):
        super(ExponentialLimiter, self).__init__()
        self._time = 1.0
        self._max_time = max_time
        self._lock = threading.RLock()

    def increment(self):
        with self._lock:
            t = self._time
            self._time *= 2.0
            self._time = min(self._time, self._max_time)

        return t

    def reset(self):
        with self._lock:
            self._time = 1.0


class AbsoluteExponentialLimiter(ExponentialLimiter):
    def __init__(self, max_time=3600.0):
        super(AbsoluteExponentialLimiter, self).__init__(max_time=max_time)
        self._abs_time = 0.0

    def increment(self):
        with self._lock:
            self._abs_time = time.time()

            super(AbsoluteExponentialLimiter, self).increment()

        return self._time + self._abs_time

    def reset(self):
        with self._lock:
            self._abs_time = 0.0
            super(AbsoluteExponentialLimiter, self).reset()

    def time(self):
        return self._time + self._abs_time
