'''Main'''
# Copyright 2013 Christopher Foo <chris.foo@gmail.com>
# Licensed under GNU GPL v3. See COPYING.txt for details
import argparse
import furlat.project
import furlat.word
import logging
import itertools
import collections


def main():
    monkey_patch()

    arg_parser = argparse.ArgumentParser()
    sub_arg_parser = arg_parser.add_subparsers(help='Command', dest='command')

    analyze_arg_parser = sub_arg_parser.add_parser('analyze',
        help='Print statistics about the URL shortcodes')
    analyze_arg_parser.add_argument('filename', nargs='+',
        help='The path of the file')
    analyze_arg_parser.add_argument('--common', action='store_true',
        help='Order by most common')

    find_arg_parser = sub_arg_parser.add_parser('find',
        help='Launch a find URL project')
    find_arg_parser.add_argument('name', help='The domain name of the URL')
    find_arg_parser.add_argument('--verbose', help='Enable information output',
        action='count')
    find_arg_parser.add_argument('--word-list', help='Line separated words',
        default='/usr/share/dict/words')
    find_arg_parser.add_argument('--wiki-word-list',
        help='Article titles from MediaWiki dumps such as Wiktionary or '
        'Wikipedia')
    find_arg_parser.add_argument('--source', nargs='*',
        help='Instead of using all sources, use given source name. Can be'
            'specified multiple times.')

    sort_arg_parser = sub_arg_parser.add_parser('sort',
        help='Sort the URLs by length, then value')
    sort_arg_parser.add_argument('filename', nargs='+',
        help='The path of the file')

    args = arg_parser.parse_args()

    command_function = commands.get(args.command)

    if command_function:
        command_function(args)
    else:
        arg_parser.print_help()


def monkey_patch():
    # Selenium issue #5701
    import selenium.webdriver.remote.errorhandler

    try:
        selenium.webdriver.remote.errorhandler.basestring
    except (NameError, AttributeError):
        selenium.webdriver.remote.errorhandler.basestring = str


def find_command(args):
    if args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.wiki_word_list:
        word_list = furlat.word.MediaWikiTitles(args.wiki_word_list)
    else:
        word_list = furlat.word.LineWordList(args.word_list)

    job_classes = furlat.project.Project.ALL_JOBS

    if args.source:
        job_classes = []
        for source_name in args.source:
            job_classes.append(
                furlat.project.Project.SOURCE_NAME_MAP[source_name])

    project = furlat.project.Project(args.name, word_list, job_classes)

    project.start()
    project.join()


def sort_command(args):
    files = [open(p, 'r') for p in args.filename]
    sort_key = lambda v: (len(v), v)

    prev_line = None
    for line in sorted(itertools.chain(*files), key=sort_key):
        if line != prev_line:
            print(line.strip())
            prev_line = line


def analyze_command(args):
    files = [open(p, 'r') for p in args.filename]
    char_counter = collections.Counter()
    length_counter = collections.Counter()
    num_lines = 0

    prev_line = None
    for line in itertools.chain(*files):
        if line != prev_line:
            shortcode = line.strip().split('/', 1)[-1]

            for letter in shortcode:
                char_counter[letter] += 1

            length_counter[len(shortcode)] += 1
            num_lines += 1

    print('Number of shortcodes:\t', num_lines)

    length_sum = sum(length_counter.values())
    print('Number of string lengths:\t', len(length_counter))

    counter_iter = sorted(length_counter.items(), key=lambda v: v[0])
    for key, value in counter_iter:
        percent = '{:>7.3f}%'.format(value / length_sum * 100)
        print(key, '\t', value, '\t', percent)

    character_sum = sum(char_counter.values())
    print('Number of unique characters:\t', len(char_counter))
    print('Number of characters used:\t', character_sum)

    if args.common:
        counter_iter = char_counter.most_common()
    else:
        counter_iter = sorted(char_counter.items(), key=lambda v: v[0])

    for key, value in counter_iter:
        percent = '{:>7.3f}%'.format(value / character_sum * 100)
        print(key, '\t', value, '\t', percent)


commands = {
    'find': find_command,
    'sort': sort_command,
    'analyze': analyze_command,
}


if __name__ == '__main__':
    main()
