tellcore.telldus (module)
=========================

.. automodule:: tellcore.telldus

This module provides a high level Python interface to Telldus' C API.

Since most functions are Python-ified wrappers around the C API, please also
refer to the `Telldus Core documentation
<http://developer.telldus.com/doxygen/group__core.html>`_ for further
information.

The classes in this module all use the :class:`.library.Library` class under
the hood, and thus also has e.g. automatic memory manangement, exceptions
(:exc:`.library.TelldusError`) and transparent string conversion with full
Python 3 support.

Some example programs are included in the documentation to help understand how
to use the different classes:

* :ref:`tool-example`
* :ref:`event-example`

TelldusCore
-----------
.. autoclass:: TelldusCore
   :members:

   .. automethod:: __init__

   .. attribute:: callback_dispatcher

      The callback dispatcher used. Set when constructing the instance and
      should not be changed.

DeviceFactory
-------------
.. autofunction:: DeviceFactory

Device
------
.. autoclass:: Device
   :members:

   .. attribute:: name

      The name of the device (read/write).

   .. attribute:: protocol

      The protocol used for the device (read/write).

   .. attribute:: model

      The device's model (read/write).

   .. attribute:: type

      The device type (read only). One of the device type constants from
      :mod:`tellcore.constants`.

DeviceGroup
-----------
.. autoclass:: DeviceGroup
   :members:

Sensor
------
.. autoclass:: Sensor
   :members:

SensorValue
-----------
.. autoclass:: SensorValue
   :members:

   .. attribute:: datatype

      One of the sensor value type constants from :mod:`tellcore.constants`.

   .. attribute:: value

      The sensor value.

   .. attribute:: timestamp

      The time the sensor value was registered (in seconds since epoch).

Controller
----------
.. autoclass:: Controller
   :members:

   .. attribute:: id

   .. attribute:: type

      One of the controller type constants from :mod:`tellcore.constants`.

QueuedCallbackDispatcher
------------------------
.. autoclass:: QueuedCallbackDispatcher
   :members:

AsyncioCallbackDispatcher
-------------------------
.. autoclass:: AsyncioCallbackDispatcher
   :members:
