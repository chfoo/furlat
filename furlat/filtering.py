'''"Garbage" removal routines'''
import html.parser
import io


class HTMLFilter(html.parser.HTMLParser):
    BLOCK_ELEMENTS = frozenset(['div', 'dl', 'fieldset', 'form', 'hr',
        'noscript', 'p', 'pre', 'table', 'tfoot', 'ul'])

    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self._buffer = io.StringIO()

    def reset(self):
        html.parser.HTMLParser.reset(self)
        self._buffer = io.StringIO()

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK_ELEMENTS:
            self._buffer.write(' ')

        for dummy, value in attrs:
            self._buffer.write(' ')
            self._buffer.write(value)
            self._buffer.write(' ')

    def handle_data(self, data):
        self._buffer.write(data)

    def handle_entityref(self, name):
        c = chr(html.entities.name2codepoint[name])
        self._buffer.write(c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))

        self._buffer.write(c)

    def get_text(self):
        return self._buffer.getvalue()
