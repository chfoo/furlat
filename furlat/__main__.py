'''Main'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import argparse
import furlat.project
import furlat.word
import logging
import signal
import sys


def main():
    monkey_patch()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('name', help='The domain name of the URL')
    arg_parser.add_argument('--verbose', help='Enable information output',
        action='count')
    arg_parser.add_argument('--word-list', help='Line separated words',
        default='/usr/share/dict/words')
    arg_parser.add_argument('--wiki-word-list',
        help='Article titles from MediaWiki dumps such as Wiktionary or '
        'Wikipedia')

    args = arg_parser.parse_args()

    if args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.wiki_word_list:
        word_list = furlat.word.MediaWikiTitles(args.wiki_word_list)
    else:
        word_list = furlat.word.LineWordList(args.word_list)

    project = furlat.project.Project(args.name, word_list)

    def signal_handler(signal_number, stack_frame):
        print('Caught signal.', file=sys.stderr)

        if project.is_running:
            print('Stopping project.', file=sys.stderr)
            project.stop()
        else:
            sys.exit('Ungracefully exiting.')

    signal.signal(signal.SIGINT, signal_handler)
    project.start()
    project.join()


def monkey_patch():
    # Selenium issue #5701
    import selenium.webdriver.remote.errorhandler

    try:
        selenium.webdriver.remote.errorhandler.basestring
    except (NameError, AttributeError):
        selenium.webdriver.remote.errorhandler.basestring = str

if __name__ == '__main__':
    main()
