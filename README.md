Python wrapper for Telldus Core
===============================

A [ctypes](http://docs.python.org/library/ctypes.html) wrapper around [Telldus
Core lib](http://developer.telldus.com/) with some extra classes to make it
more python-ish and easier to work with.

Features
--------

* Wraps the C-interface with a python interface (with classes and exceptions).
* Automatically frees memory for returned strings.
* Throws an exception (TelldusError) in case a library function returns an
  error.
* Supports python 3 with automatic handling of strings.
* Takes care of making callbacks from the library thread-safe.
* Unit tested.

Users
-----

* [Tellprox](https://github.com/p3tecracknell/tellprox/) - A local server to
  use in place of Tellstick Live

TODO
----

* Improve documentation.
