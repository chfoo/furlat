'''Word lists'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import abc
import gzip
import mimetypes
import random
import queue


class BaseWordList(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_random(self, num_words=1):
        pass


class ReservoirSamplingWordList(BaseWordList):
    @abc.abstractproperty
    def _iter(self):
        pass

    def get_random(self, num_words=1):
        # https://en.wikipedia.org/wiki/Reservoir_sampling
        words = []

        for index, line in enumerate(self._iter):
            if index < num_words:
                words.append(line)
            else:
                r = random.randint(0, index)

                if r < num_words:
                    words[r] = line

        words = [word.rstrip() for word in words]

        return words


class LineWordList(ReservoirSamplingWordList):
    def __init__(self, filename):
        super(LineWordList, self).__init__()

        if mimetypes.guess_type(filename)[1] == 'gzip':
            self._file = gzip.open(filename, 'rt')
        else:
            self._file = open(filename, 'rt')

    @property
    def _iter(self):
        self._file.seek(0)
        return self._file


class MediaWikiTitles(LineWordList):
    def get_words(self, num_words=1):
        words = super(MediaWikiTitles, self).get_words(num_words)
        words = [word for word in words if self.is_word(word)]
        words = [self.clean_title(word) for word in words]

        return words

    def is_word(self, s):
        if s == 'page_title':
            return False
        if s.startswith('-'):
            return False

        return True

    def clean_title(self, s):
        return s.replace('_', ' ')


class TestWordList(BaseWordList):
    def get_random(self, num_words=1):
        return ['hello'] * num_words


class WordQueue(object):
    def __init__(self, word_list, size=100):
        self._word_list = word_list
        self._queue = queue.Queue()
        self._size = size

    def get(self):
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            words = self._word_list.get_random(num_words=self._size)

            for word in words:
                self._queue.put(word)

        return self._queue.get_nowait()


if __name__ == '__main__':
    wd = WordQueue(LineWordList('/usr/share/dict/words'))

    for dummy in range(500):
        print(wd.get())
