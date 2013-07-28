import unittest
from furlat import source


class TestURLPattern(unittest.TestCase):
    def test_re_pattern(self):
        text = '''short.url/a3f
lorem ipsum short.url/abc123
short.url/93jd2
kittens puppies short.url/about.html wolf http://short.url/j3S0d
dogs cats https://short.url/dj3d
'''

        url_pattern = source.URLPattern('short.url')
        found_urls = list(url_pattern.scrape(text))

        self.assertSequenceEqual(
            ['short.url/a3f', 'short.url/abc123', 'short.url/93jd2',
            'short.url/about', 'short.url/j3S0d', 'short.url/dj3d'],
            found_urls
        )
