
import unittest
from furlat import filtering


class TestFilter(unittest.TestCase):
    def test_html_filter(self):
        t = '''<div class="result">
Lorem ipsum <b>short.url</b>/abcdefg lorem ipsum dogs cats.
</div>
'''
        f = filtering.HTMLFilter()
        f.feed(t)

        s = f.get_text()

        self.assertIn('short.url/abcdefg', s)

        f.reset()
        self.assertFalse(f.get_text())
