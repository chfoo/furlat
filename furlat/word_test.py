import os.path
import unittest
from furlat import word


class TestLineWordList(unittest.TestCase):
    @unittest.skipIf(not os.path.exists('/usr/share/dict/words'),
        'System UNIX spell check dictionary not found')
    def test_unix_system_words(self):
        wl = word.LineWordList('/usr/share/dict/words')
        words = wl.get_random(num_words=5)

        self.assertEqual(5, len(words))


class TestWordQueue(unittest.TestCase):
    @unittest.skipIf(not os.path.exists('/usr/share/dict/words'),
        'System UNIX spell check dictionary not found')
    def test_unix_system_words(self):
        q = word.WordQueue(word.LineWordList('/usr/share/dict/words'), size=5)

        for dummy in range(50):
            q.get()
