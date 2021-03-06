'''Projects'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import furlat.job
import furlat.limit
import furlat.word
import logging
import os
import os.path
import queue
import random
import string
import threading
import time


_logger = logging.getLogger(__name__)


class Project(threading.Thread):
    ALL_JOBS = (
        furlat.job.GoogleSearch,
        furlat.job.BingSearch,
        furlat.job.YahooSearch,
        furlat.job.TwitterSearch,
    )
    SOURCE_NAME_MAP = {
        'google': furlat.job.GoogleSearch,
        'bing': furlat.job.BingSearch,
        'yahoo': furlat.job.YahooSearch,
        'twitter': furlat.job.TwitterSearch,
    }

    def __init__(self, domain_name, word_list, job_classes=ALL_JOBS,
    any_short_url=False, rate_per_second=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self._working_directory = os.path.join(os.getcwd(),
            ''.join(s for s in domain_name \
                if s in string.ascii_letters + string.digits))

        if any_short_url:
            self._url_pattern = furlat.source.AnyShortURLPattern(domain_name)
        else:
            self._url_pattern = furlat.source.ShortcodeURLPattern(domain_name)

        self._running = True
        self._future_acceptor_queue = queue.Queue()
        self._job_runner = furlat.job.JobRunner(self._future_acceptor_queue)
        self._job_classes = job_classes
        self._job_limiter = furlat.job.JobLimiter()
        self._word_queue = furlat.word.WordQueue(word_list)
        self._error_limiters = {}
        self._start_time = time.time()

        if rate_per_second:
            self._rate_limiter = furlat.limit.RateLimiter(
                average_rate=rate_per_second)
        else:
            self._rate_limiter = furlat.limit.RateLimiter()

        for job_class in self._job_classes:
            self._error_limiters[job_class] = \
                furlat.limit.AbsoluteExponentialLimiter()

    def run(self):
        _logger.info('Project started for ‘{name}’.'.format(
            name=self._url_pattern.domain_name))

        self._job_runner.start()

        job = None

        while self._running:
            self._check_stop_file()

            if not job:
                job = self._new_job()

            if job:
                try:
                    self._job_runner.add_job(job, timeout=0.25)
                    _logger.info('Job #{} ({}) started.'.format(job.job_id,
                        job.__class__.__name__))
                    job = None
                except queue.Full:
                    pass

            self._accept_job_future()

        _logger.debug('Exit main loop')
        self._job_runner.stop()
        self._job_runner.join()
        self._accept_job_future()
        furlat.job.SearchEngineJob.web_driver_cache.clear_all()
        _logger.debug('Project exiting')

    def stop(self):
        _logger.debug('Stopping job runner.')

        self._running = False
        self._job_runner.stop()

    @property
    def is_running(self):
        return self._running

    def _accept_job_future(self):
        while True:
            try:
                job, future = self._future_acceptor_queue.get(timeout=0.25)
            except queue.Empty:
                return

            job_class = job.__class__

            self._job_limiter.remove(job.__class__)

            try:
                results = future.result()
                _logger.info('Job #{} ({}) finished with {} results.'.format(
                job.job_id, job_class.__name__, len(results)))

                self.job_result_callback(job, results)
                self._error_limiters[job_class].reset()
            except Exception:
                _logger.exception('Job #{} ({}) finished with errors'.format(
                    job.job_id, job_class.__name__))

                self._error_limiters[job_class].increment()

    def _new_job(self):
        job_classes = list(self._job_classes)

        random.shuffle(job_classes)

        for job_class in job_classes:
            if self._error_limiters[job_class].time() < time.time() \
            and self._job_limiter.add(job_class):
                keywords = self._get_keywords()
                return job_class(self._url_pattern, keywords,
                    rate_limiter=self._rate_limiter)

    def _get_keywords(self):
        return ' OR '.join([self._word_queue.get(), self._word_queue.get()])

    def job_result_callback(self, job, result):
        if len(result) == 0:
            _logger.debug('Result is size 0. Not writing result file.')
            return

        os.makedirs(self._working_directory, exist_ok=True)
        file_path = os.path.join(self._working_directory, str(job.job_id))

        _logger.debug('Saving result into {}'.format(file_path))

        with open(file_path, 'wb') as f:
            for url in result:
                f.write(url.encode())
                f.write(b'\n')

    def _check_stop_file(self):
        if os.path.exists('STOP') \
        and os.path.getmtime('STOP') > self._start_time:
            self.stop()
