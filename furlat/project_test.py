
import unittest
from furlat import project
from furlat import job
from furlat import word
import time


class TestProject(unittest.TestCase):
    def test_test_job(self):
        l = []
        p = project.Project('example.com', word.TestWordList(),
            job_classes=[job.TestJob])

        def cb(job, result):
            l.append(result)

        p.job_result_callback = cb

        p.start()
        time.sleep(2)
        p.stop()
        p.join(2)

        self.assertFalse(p.is_alive())
        self.assertTrue(l)

        for item in l:
            self.assertEqual(item, 'Hello world!')

    def test_test_search_engine(self):
        p = project.Project('example.com', word.TestWordList(),
            job_classes=[job.TestSearchEngineSearch])

        def cb(job, result):
            pass

        p.job_result_callback = cb

        p.start()
        time.sleep(2)
        p.stop()
        p.join(60)

        self.assertFalse(p.is_alive())
