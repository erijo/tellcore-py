#!/usr/bin/env python

from distutils.core import setup
import os
import re

version_re = re.compile(r'__version__ = "(.*)"')
cwd = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(cwd, 'tellcore', '__init__.py')) as init:
    for line in init:
        match = version_re.search(line)
        if match:
            version = match.group(1)
            break
    else:
        raise Exception('Cannot find version in __init__.py')

setup(
    name='tellcore-py',
    version=version,
    author='Erik Johansson',
    author_email='erik@ejohansson.se',
    packages=['tellcore'],
    provides=['tellcore'],
    scripts=['bin/tellcore_tool', 'bin/tellcore_events',
             'bin/tellcore_controllers'],
    url='https://github.com/erijo/tellcore-py',
    license='GPLv3+',
    description='Python wrapper for Telldus\' home automation library',
    long_description=open('README.rst').read() + '\n\n' + \
        open('CHANGES.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
)
