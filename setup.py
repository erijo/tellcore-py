#!/usr/bin/env python

from distutils.core import setup

setup(
    name='tellcore-py',
    version='1.0.1',
    author='Erik Johansson',
    author_email='erik@ejohansson.se',
    packages=['tellcore'],
    scripts=['bin/tellcore_tool', 'bin/tellcore_events',
             'bin/tellcore_controllers'],
    url='https://github.com/erijo/tellcore-py',
    license='GPLv3+',
    description='Python wrapper for Telldus\' home automation library',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Home Automation',
        ],
)
