import unittest
from furlat import limit


class TestRateLimiter(unittest.TestCase):
    def test_average_time(self):
        limiter = limit.RateLimiter(0.5)
        count = 100
        time_sum = 0

        for dummy in range(count):
            time_sum += limiter.delay_time()

        computed_average = time_sum / count

        self.assertAlmostEqual(0.5, 1.0 / computed_average, delta=0.1)
