import unittest
from furlat import job


class TestJobID(unittest.TestCase):
    def test_counter(self):
        job.JobID()
        c1 = job.JobID.counter
        job.JobID()
        c2 = job.JobID.counter

        self.assertNotEqual(c1, c2)

    def test_equality(self):
        j1 = job.JobID()
        j2 = job.JobID()

        self.assertNotEqual(j1, j2)

    def test_functions(self):
        self.assertIsInstance(str(job.JobID()), str)
        self.assertIsInstance(bytes(job.JobID()), bytes)
        self.assertIsInstance(hash(job.JobID()), int)
