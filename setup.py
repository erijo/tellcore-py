#!/usr/bin/env python

from distutils.core import setup

setup(
    name='tellcore-py',
    version='0.1.0',
    author='Erik Johansson',
    author_email='erik@ejohansson.se',
    packages=['tellcore'],
    url='https://github.com/erijo/tellcore-py',
    license='GPLv3',
    description='Python wrapper for Telldus Core',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Home Automation',
        ],
)
