from distutils.core import setup

import furlat.version

setup(name='furlat',
    version=furlat.version.__version__,
    description='Find URL Archiving Tool',
    author='Christopher Foo',
    author_email='chris.foo@gmail.com',
    url='https://github.com/chfoo/furlat',
    packages=['furlat'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Topic :: System :: Archiving',
    ],
)

