Changelog
=========

1.0.4 (2014-11-05)
------------------

* Made ``last_sent_value`` return an int instead of string.


1.0.3 (2014-02-02)
------------------

* Work around crash in Telldus Core (< v2.1.2) when re-initalizing the library
  after ``tdClose``.


1.0.2 (2014-01-28)
------------------

* Packaging fixes.


1.0.1 (2014-01-26)
------------------

* Added ``AsyncioCallbackDispatcher`` class for integrating callbacks with the
  new event loop available in Python 3.4 (asyncio).

* Include tools from bin/ when installing.


1.0.0 (2014-01-09)
------------------

* Added high level support for device groups in the form of the new class
  ``DeviceGroup``.

* More complete documentation.

* Removed the methods process_callback and process_pending_callbacks from
  ``TelldusCore``. Instead, callback_dispatcher is now a public attribute of
  ``TelldusCore`` and the default callback dispatcher
  ``QueuedCallbackDispatcher`` implements the two methods instead.


0.9.0 (2014-01-03)
------------------

* Telldus functions that used to return bool (``tdSetName``, ``tdSetProtocol``,
  ``tdSetModel``, ``tdSetDeviceParameter`` and ``tdRemoveDevice``) now raise an
  exception instead of returning False.

* Support for rain- and windsensors.

* Include data type in ``SensorValue``.


0.8.0 (2013-08-11)
------------------

* Improved callback handling to simplify integration with different event
  loops. Parameter conversion is now done in the library code and the
  adaptation to different event loops is done by a simple callback dispatch
  class. The default dispatcher (when using ``TelldusCore``) is still done
  using a queue.

* New documentation for parts of the package. Can be read online at
  https://tellcore-py.readthedocs.org/.

* Fix problem with strings and python 3 (issue #2).


0.1.0 (2013-06-26)
------------------

* First release.
