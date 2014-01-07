tellcore.telldus (module)
=========================

.. automodule:: tellcore.telldus

TelldusCore
-----------
.. autoclass:: TelldusCore
   :members:

   .. automethod:: __init__

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
