'''Rate limiting'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import random


class RateLimiter(object):
    def __init__(self, average_rate=1/5.0):
        self._average_rate = average_rate

    def delay_time(self):
        return random.uniform(0.0, 1.0 / self._average_rate * 2)
