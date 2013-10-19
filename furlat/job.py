'''Item execution'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import abc
import base64
import collections
import concurrent.futures
import furlat.limit
import furlat.source
import logging
import os
import queue
import random
import selenium.webdriver
import threading
import time

_logger = logging.getLogger(__name__)


class JobRunner(threading.Thread):
    def __init__(self, future_acceptor_queue, max_job_count=5):
        threading.Thread.__init__(self)
        self.daemon = True
        self._max_job_count = max_job_count
        self._num_jobs_running = 0
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_job_count)
        self._queue = queue.Queue(maxsize=max_job_count)
        self._running = True
        self._future_acceptor_queue = future_acceptor_queue
        self._lock = threading.Lock()

    def run(self):
        _logger.debug('Job runner startup.')

        while self._running or self._queue.qsize():
            self._run_job()

        _logger.debug('Waiting for jobs to finish.')
        self._queue.join()
        _logger.debug('Queue finished.')

    def _run_job(self):
        if self._num_jobs_running >= self._max_job_count:
            _logger.debug('Too many jobs running.')
            time.sleep(0.5)
            return

        try:
            job = self._queue.get(timeout=0.5)
        except queue.Empty:
            return

        _logger.debug('Got job {} and submitting to executor'.format(
            str(job.job_id)))

        with self._lock:
            self._num_jobs_running += 1

        future = self._executor.submit(job)

        def job_done_callback(future):
            _logger.debug('Job {} finished.'.format(str(job.job_id)))

            with self._lock:
                self._num_jobs_running -= 1

            self._future_acceptor_queue.put((job, future))
            self._queue.task_done()

        future.add_done_callback(job_done_callback)

    def add_job(self, job, timeout=None):
        if not self._running or self._num_jobs_running >= self._max_job_count:
            raise queue.Full

        self._queue.put(job, timeout=timeout)

    def stop(self):
        _logger.debug('Job runner stopping.')
        self._running = False


class JobID(object):
    '''A unique job ID'''

    TIMESTAMP_SIZE = 4
    PROCESS_ID_SIZE = 4
    COUNTER_SIZE = 4
    counter = random.randint(0, 2 ** (8 * COUNTER_SIZE) - 1)

    def __init__(self):
        JobID.counter += 1
        JobID.counter %= 2 ** (8 * self.COUNTER_SIZE) - 1
        self._value = b''.join([
            self.timestamp_bytes(),
            self.process_id_bytes(),
            self.counter_bytes(),
        ])

    @classmethod
    def timestamp_bytes(cls):
        return int(time.time()).to_bytes(cls.TIMESTAMP_SIZE, 'big')

    @classmethod
    def process_id_bytes(cls):
        return (os.getpid() % (2 ** (8 * cls.PROCESS_ID_SIZE))).to_bytes(
            cls.PROCESS_ID_SIZE, 'big')

    @classmethod
    def counter_bytes(cls):
        return cls.counter.to_bytes(cls.COUNTER_SIZE, 'big')

    def __bytes__(self):
        return self._value

    def __str__(self):
        s = base64.b16encode(self._value).decode().lower()
        split1 = self.TIMESTAMP_SIZE * 2
        split2 = split1 + self.PROCESS_ID_SIZE * 2

        return '{}-{}-{}'.format(s[0:split1], s[split1:split2], s[split2:])

    def __eq__(self, other):
        return bytes(self) == bytes(other)

    def __ne__(self, other):
        return bytes(self) != bytes(other)

    def __hash__(self):
        return hash(bytes(self))


class JobLimiter(object):
    '''Rate limit jobs by their class'''

    def __init__(self):
        super(JobLimiter, self).__init__()
        self._lock = threading.Lock()
        self._job_counter = collections.Counter()

    def add(self, job_class):
        # TODO: not use hardcoded value
        with self._lock:
            if self._job_counter[job_class] < 1:
                self._job_counter[job_class] += 1
                return True

        return False

    def remove(self, job_class):
        with self._lock:
            self._job_counter[job_class] -= 1


class BaseJob(object, metaclass=abc.ABCMeta):
    def __init__(self, url_pattern, search_keyword):
        super(BaseJob, self).__init__()
        self._url_pattern = url_pattern
        self._search_keyword = search_keyword
        self._job_id = JobID()

    @property
    def job_id(self):
        return self._job_id

    def __call__(self):
        return self.run()

    @abc.abstractmethod
    def run(self):
        pass


class TestJob(BaseJob):
    def run(self):
        _logger.debug('Test job running')
        time.sleep(random.uniform(0.0, 1.0))
        return 'Hello world!'


class WebDriverCache(object):
    MAX_CYCLE_COUNT = 100

    def __init__(self):
        super(WebDriverCache, self).__init__()
        self._drivers = {}
        self._driver_run_count = collections.Counter()
        self._lock = threading.RLock()

    def get(self, driver_class, instance_id):
        key = (driver_class, instance_id)

        if self._driver_run_count[key] > self.MAX_CYCLE_COUNT:
            self.clear(driver_class, instance_id)

        with self._lock:
            if key not in self._drivers:
                self._drivers[key] = driver_class()
                self._driver_run_count[key] = 0

            self._driver_run_count[key] += 1

            return self._drivers[key]

    def clear(self, driver_class, instance_id):
        key = (driver_class, instance_id)

        with self._lock:
            if key in self._drivers:
                self._drivers[key].quit()
                del self._drivers[key]
                del self._driver_run_count[key]

    def clear_all(self):
        with self._lock:
            for driver_class, instance_id in list(self._drivers.keys()):
                self.clear(driver_class, instance_id)


class SearchEngineJob(BaseJob):
    web_driver_cache = WebDriverCache()
    RESULT_COUNT_DEQUE_SIZE = 3

    def __init__(self, *args, rate_limiter=None, **kwargs):
        super(SearchEngineJob, self).__init__(*args, **kwargs)
        self._urls = []
        self._result_count_deque = collections.deque(
            maxlen=self.RESULT_COUNT_DEQUE_SIZE)
        self._rate_limiter = rate_limiter or furlat.limit.RateLimiter()
        self._driver = None
        self._search_engine = None

    @abc.abstractproperty
    def search_engine_class(self, *args, **kwargs):
        pass

    def run(self):
        _logger.debug('{} Search domain {} {}'.format(
            self.search_engine_class.__name__,
            self._url_pattern.domain_name,
            self._search_keyword))

        self._driver = self.web_driver_cache.get(selenium.webdriver.Firefox,
            self.search_engine_class)
        self._search_engine = self.search_engine_class(self._driver,
            self._url_pattern, self._search_keyword)

        self._load_first_page()

        while True:
            found_urls = self._search_engine.scrape_page()

            _logger.debug('Found {} urls'.format(len(found_urls)))
            self._add_page_results(found_urls)

            if not self._is_continue_ok():
                break

            if not self._load_next_page():
                break

        urls = list(sorted(frozenset(self._urls)))

        _logger.debug('Job finished. Found total {} URLs'.format(len(urls)))

        return urls

    def _load_first_page(self):
        _logger.debug('Loading first page')
        self._search_engine.load_first_page()

        delay_time = self._rate_limiter.delay_time()

        _logger.debug('Sleep {} seconds'.format(delay_time))
        time.sleep(delay_time)

    def _load_next_page(self):
        if self._search_engine.click_next_page():
            self._search_engine.wait_for_page_load()

            delay_time = self._rate_limiter.delay_time()

            _logger.debug('Sleep {} seconds'.format(delay_time))
            time.sleep(delay_time)
            return True
        else:
            return False

    def _add_page_results(self, urls):
        self._urls.extend(urls)
        self._result_count_deque.append(len(urls))

    def _is_continue_ok(self):
        if len(self._result_count_deque) >= self.RESULT_COUNT_DEQUE_SIZE \
        and sum(self._result_count_deque) == 0:
            return False

        return True


class TestSearchEngineSearch(SearchEngineJob):
    @property
    def search_engine_class(self):
        return furlat.source.TestSearchEngine


class GoogleSearch(SearchEngineJob):
    @property
    def search_engine_class(self):
        return furlat.source.Google


class YahooSearch(SearchEngineJob):
    @property
    def search_engine_class(self):
        return furlat.source.Yahoo


class BingSearch(SearchEngineJob):
    @property
    def search_engine_class(self):
        return furlat.source.Bing


class TwitterSearch(SearchEngineJob):
    @property
    def search_engine_class(self):
        return furlat.source.Twitter
