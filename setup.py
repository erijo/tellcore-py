from distutils.core import setup

setup(
    name='tellcore-py',
    version='0.1.0',
    author='Erik Johansson',
    author_email='erik@ejohansson.se',
    packages=['tellcore'],
    url='https://github.com/erijo/telldus-py',
    license='LICENSE.txt',
    description='Python wrapper for Telldus Core',
    long_description=open('README.rst').read(),
)
