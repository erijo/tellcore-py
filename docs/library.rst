tellcore.library (module)
=========================

The classes in this module are not meant to be used directly. They are mostly
support classes for the higher level API described in :doc:`telldus`.

.. automodule:: tellcore.library

Library
-------
.. autoclass:: Library(name=LIBRARY_NAME)
   :members:

   .. automethod:: __init__(name=LIBRARY_NAME)

   .. automethod:: __del__

TelldusError
------------
.. autoexception:: TelldusError
   :members:

   .. automethod:: __str__

BaseCallbackDispatcher
----------------------
.. autoclass:: BaseCallbackDispatcher
   :members:

DirectCallbackDispatcher
------------------------
.. autoclass:: DirectCallbackDispatcher
   :members:
