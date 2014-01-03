.. _event-example:

Event handling (example)
========================

The example below illustrates how event callbacks are registered and processed
using the default :class:`.telldus.QueuedCallbackDispatcher` dispatcher.

For more information regarding the arguments to the callback functions, please
refere to the official `Telldus Core documentation
<http://developer.telldus.com/doxygen/group__core.html>`_ (see the callback
typedefs). Please note that the context mentioned there is not included in
tellcore-py.

.. literalinclude:: ../bin/td_event_tracer
