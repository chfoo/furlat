
import unittest
from furlat import filtering


class TestFilter(unittest.TestCase):
    def test_html_filter(self):
        t = '''<div class="result">
Lorem ipsum <b>short.url</b>/abcdefg lorem ipsum dogs cats.
</div> <a href="http://short.url/asd34">puppies</a>
wolf. <span><b>short</b>.<b>url</b>/ajoier</span><div>kitten</div>
'''
        f = filtering.HTMLFilter()
        f.feed(t)

        s = f.get_text()

        self.assertIn('short.url/abcdefg', s)
        self.assertIn('short.url/asd34', s)
        self.assertIn('short.url/ajoier', s)
        self.assertNotIn('short.url/ajoierkitten', s)

        f.reset()
        self.assertFalse(f.get_text())
