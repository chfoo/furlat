'''Web sources like search engines and microblogs'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import abc
import logging
import re
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
import urllib.parse

import furlat.filtering


_logger = logging.getLogger(__name__)


class URLPattern(object, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def domain_name(self):
        pass

    @abc.abstractmethod
    def scrape(self, text):
        pass


class ShortcodeURLPattern(URLPattern):
    def __init__(self, domain_name, shortcode_pattern=r'[a-zA-Z0-9]+'):
        self._domain_name = domain_name
        self._shortcode_pattern = shortcode_pattern

    @property
    def domain_name(self):
        return self._domain_name

    @property
    def shortcode_pattern(self):
        return self._shortcode_pattern

    @property
    def re_pattern(self):
        return r'({domain}/{shortcode})'.format(
            domain=self._domain_name.replace('.', r'\.'),
            shortcode=self._shortcode_pattern)

    def scrape(self, text):
        for match in re.finditer(self.re_pattern, text, re.UNICODE):
            if match:
                yield match.group(1)


class AnyShortURLPattern(object):
    def __init__(self, domain_name):
        self._domain_name = domain_name
        self.re_pattern = r'([a-z0-9.-]*[a-z0-9-]+\.[a-z0-9]+/[a-zA-Z0-9]+)'

    @property
    def domain_name(self):
        return self._domain_name

    def scrape(self, text):
        for match in re.finditer(self.re_pattern, text, re.UNICODE):
            if match:
                yield match.group(1)


class BaseSearchEngine(object, metaclass=abc.ABCMeta):
    def __init__(self, driver, url_pattern, search_keyword):
        self._driver = driver
        self._url_pattern = url_pattern
        self._search_keyword = search_keyword
        self._html_filter = furlat.filtering.HTMLFilter()

    @abc.abstractproperty
    def query_url_template(self):
        pass

    @abc.abstractproperty
    def click_next_page(self):
        pass

    @abc.abstractproperty
    def wait_for_page_load(self):
        pass

    @abc.abstractproperty
    def site_search_operator(self):
        pass

    @property
    def driver(self):
        return self._driver

    @property
    def url_pattern(self):
        return self._url_pattern

    @property
    def search_keyword(self):
        return self._search_keyword

    def load_first_page(self):
        query_str = '{} ({})'.format(
            self.site_search_operator.format(
                site=self.url_pattern.domain_name),
            self.search_keyword)
        query_url = self.query_url_template.format(
            query=urllib.parse.quote_plus(query_str))

        _logger.debug('Fetch url={}'.format(query_url))
        self.driver.get(query_url)
        self.wait_for_page_load()

    def scrape_page(self):
        body_element = self.driver.find_element_by_tag_name('body')
        body_text = body_element.get_attribute('innerHTML')

        self._html_filter.reset()
        self._html_filter.feed(body_text)

        text = self._html_filter.get_text()

        return list(self.url_pattern.scrape(text))


class TestSearchEngine(BaseSearchEngine):
    def __init__(self, *args, **kwargs):
        super(TestSearchEngine, self).__init__(*args, **kwargs)
        self._count = 0

    @property
    def query_url_template(self):
        return 'http://example.com?q={query}'

    @property
    def site_search_operator(self):
        return '{site}'

    def click_next_page(self):
        return False

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.find_element_by_tag_name('body'))


class Google(BaseSearchEngine):
    @property
    def query_url_template(self):
        return 'https://www.google.com/search?q={query}'

    @property
    def site_search_operator(self):
        return 'site:{site}'

    def click_next_page(self):
        try:
            link = self.driver.find_element_by_id('pnnext')
        except NoSuchElementException:
            return False

        link.click()
        return True

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.find_element_by_id('foot'))


class Bing(BaseSearchEngine):
    @property
    def query_url_template(self):
        return 'http://www.bing.com/search?q={query}'

    @property
    def site_search_operator(self):
        return '"{site}"'

    def click_next_page(self):
        try:
            link = self.driver.find_element_by_class_name('sb_pagN')
        except NoSuchElementException:
            return False

        link.click()
        return True

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.find_element_by_id('sb_foot'))


class Yahoo(BaseSearchEngine):
    @property
    def query_url_template(self):
        return 'http://search.yahoo.com/search?p={query}'

    @property
    def site_search_operator(self):
        return '"{site}"'

    def click_next_page(self):
        try:
            link = self.driver.find_element_by_id('pg-next')
        except NoSuchElementException:
            return False

        link.click()
        return True

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.find_element_by_id('ft'))


class Twitter(BaseSearchEngine):
    @property
    def query_url_template(self):
        return 'https://twitter.com/search?q={query}&f=realtime'

    @property
    def site_search_operator(self):
        return '"{site}"'

    def click_next_page(self):
        content_element = self.driver.find_element_by_id('timeline')
        old_page_height = content_element.size['height']

        self.driver.execute_script('window.scrollByPages(10)')

        try:
            def height_changed(dummy):
                return content_element.size['height'] > old_page_height

            WebDriverWait(self.driver, 5).until(height_changed)
        except TimeoutException:
            _logger.debug(
                'Timeout, Old page height {}, new page height {}'.format(
                    old_page_height, content_element.size['height']))
            return False

        _logger.debug('Old page height {}, new page height {}'.format(
            old_page_height, content_element.size['height']))
        return True

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.find_element_by_id('timeline'))
