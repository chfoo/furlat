'''Rate limiting'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import random
import threading


class RateLimiter(object):
    def __init__(self, average_rate=1 / 5.0):
        self._average_rate = average_rate

    def delay_time(self):
        return random.uniform(0.0, 1.0 / self._average_rate * 2)


class ExponentialLimiter(object):
    def __init__(self, max_time=3600.0):
        self._time = 1.0
        self._max_time = max_time
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            t = self._time
            self._time *= 2.0
            self._time = min(self._time, self._max_time)

        return t

    def reset(self):
        with self._lock:
            self._time = 1.0
