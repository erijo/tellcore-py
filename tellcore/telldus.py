# Copyright (c) 2012-2014 Erik Johansson <erik@ejohansson.se>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

try:
    import queue
except ImportError:
    # Fall back on old (python 2) variant
    import Queue as queue

import tellcore.constants as const
from tellcore.library import Library, TelldusError, BaseCallbackDispatcher

from datetime import datetime


class QueuedCallbackDispatcher(BaseCallbackDispatcher):
    """The default callback dispatcher used by :class:`TelldusCore`.

    Queues callbacks that arrive from Telldus Core. Then calls them in the main
    thread (or more precise: the thread calling :func:`process_callback`)
    instead of the callback thread used by Telldus Core. This way the
    application using :class:`TelldusCore` don't have to do any thread
    synchronization. Only make sure :func:`process_pending_callbacks` is called
    regularly.
    """

    def __init__(self):
        super(QueuedCallbackDispatcher, self).__init__()
        self._queue = queue.Queue()

    def on_callback(self, callback, *args):
        self._queue.put((callback, args))

    def process_callback(self, block=True):
        """Dispatch a single callback in the current thread.

        :param boolean block: If True, blocks waiting for a callback to come.
        :return: True if a callback was processed; otherwise False.
        """
        try:
            (callback, args) = self._queue.get(block=block)
            try:
                callback(*args)
            finally:
                self._queue.task_done()
        except queue.Empty:
            return False
        return True

    def process_pending_callbacks(self):
        """Dispatch all pending callbacks in the current thread."""
        while self.process_callback(block=False):
            pass


class AsyncioCallbackDispatcher(BaseCallbackDispatcher):
    """Dispatcher for use with the event loop available in Python 3.4+.

    Callbacks will be dispatched on the thread running the event loop. The loop
    argument should be a BaseEventLoop instance, e.g. the one returned from
    asyncio.get_event_loop().
    """
    def __init__(self, loop):
        super(AsyncioCallbackDispatcher, self).__init__()
        self._loop = loop

    def on_callback(self, callback, *args):
        self._loop.call_soon_threadsafe(callback, *args)


class TelldusCore(object):
    """The main class for tellcore-py.

    Has methods for adding devices and for enumerating controllers, devices and
    sensors. Also handles callbacks; both registration and making sure the
    callbacks are processed in the main thread instead of the callback thread.
    """

    def __init__(self, library_path=None, callback_dispatcher=None):
        """Create a new TelldusCore instance.

        Only one instance should be used per program.

        :param str library_path: Passed to the :class:`.library.Library`
            constructor.

        :param str callback_dispatcher: An instance implementing the
            :class:`.library.BaseCallbackDispatcher` interface (
            e.g. :class:`QueuedCallbackDispatcher` or
            :class:`AsyncioCallbackDispatcher`) A callback dispatcher must be
            provided if callbacks are to be used.

        """
        super(TelldusCore, self).__init__()
        self.lib = Library(library_path, callback_dispatcher)

    def __getattr__(self, name):
        if name == 'callback_dispatcher':
            return self.lib.callback_dispatcher
        raise AttributeError(name)

    def register_device_event(self, callback):
        """Register a new device event callback handler.

        See :ref:`event-example` for more information.

        :return: the callback id
        """
        return self.lib.tdRegisterDeviceEvent(callback)

    def register_device_change_event(self, callback):
        """Register a new device change event callback handler.

        See :ref:`event-example` for more information.

        :return: the callback id
        """
        return self.lib.tdRegisterDeviceChangeEvent(callback)

    def register_raw_device_event(self, callback):
        """Register a new raw device event callback handler.

        See :ref:`event-example` for more information.

        :return: the callback id
        """
        return self.lib.tdRegisterRawDeviceEvent(callback)

    def register_sensor_event(self, callback):
        """Register a new sensor event callback handler.

        See :ref:`event-example` for more information.

        :return: the callback id
        """
        return self.lib.tdRegisterSensorEvent(callback)

    def register_controller_event(self, callback):
        """Register a new controller event callback handler.

        See :ref:`event-example` for more information.

        :return: the callback id
        """
        return self.lib.tdRegisterControllerEvent(callback)

    def unregister_callback(self, cid):
        """Unregister a callback handler.

        :param int id: the callback id as returned from one of the
            register_*_event methods.
        """
        self.lib.tdUnregisterCallback(cid)

    def devices(self):
        """Return all known devices.

        :return: list of :class:`Device` or :class:`DeviceGroup` instances.
        """
        devices = []
        count = self.lib.tdGetNumberOfDevices()
        for i in range(count):
            device = DeviceFactory(self.lib.tdGetDeviceId(i), lib=self.lib)
            devices.append(device)
        return devices

    def sensors(self):
        """Return all known sensors.

        :return: list of :class:`Sensor` instances.
        """
        sensors = []
        try:
            while True:
                sensor = self.lib.tdSensor()
                sensors.append(Sensor(lib=self.lib, **sensor))
        except TelldusError as e:
            if e.error != const.TELLSTICK_ERROR_DEVICE_NOT_FOUND:
                raise
        return sensors

    def controllers(self):
        """Return all known controllers.

        Requires Telldus core library version >= 2.1.2.

        :return: list of :class:`Controller` instances.
        """
        controllers = []
        try:
            while True:
                controller = self.lib.tdController()
                del controller["name"]
                del controller["available"]
                controllers.append(Controller(lib=self.lib, **controller))
        except TelldusError as e:
            if e.error != const.TELLSTICK_ERROR_NOT_FOUND:
                raise
        return controllers

    def add_device(self, name, protocol, model=None, **parameters):
        """Add a new device.

        :return: a :class:`Device` or :class:`DeviceGroup` instance.
        """
        device = Device(self.lib.tdAddDevice(), lib=self.lib)
        try:
            device.name = name
            device.protocol = protocol
            if model:
                device.model = model
            for key, value in parameters.items():
                device.set_parameter(key, value)

            # Return correct type
            return DeviceFactory(device.id, lib=self.lib)
        except Exception:
            import sys
            exc_info = sys.exc_info()
            try:
                device.remove()
            except:
                pass

            if "with_traceback" in dir(Exception):
                raise exc_info[0].with_traceback(exc_info[1], exc_info[2])
            else:
                exec("raise exc_info[0], exc_info[1], exc_info[2]")

    def add_group(self, name, devices):
        """Add a new device group.

        :return: a :class:`DeviceGroup` instance.
        """
        device = self.add_device(name, "group")
        device.add_to_group(devices)
        return device

    def send_raw_command(self, command, reserved=0):
        """Send a raw command."""
        return self.lib.tdSendRawCommand(command, reserved)

    def connect_controller(self, vid, pid, serial):
        """Connect a controller."""
        self.lib.tdConnectTellStickController(vid, pid, serial)

    def disconnect_controller(self, vid, pid, serial):
        """Disconnect a controller."""
        self.lib.tdDisconnectTellStickController(vid, pid, serial)


def DeviceFactory(id, lib=None):
    """Create the correct device instance based on device type and return it.

    :return: a :class:`Device` or :class:`DeviceGroup` instance.
    """
    lib = lib or Library()
    if lib.tdGetDeviceType(id) == const.TELLSTICK_TYPE_GROUP:
        return DeviceGroup(id, lib=lib)
    return Device(id, lib=lib)


class Device(object):
    """A device that can be controlled by Telldus Core.

    Can be instantiated directly if the id is known, but using
    :func:`DeviceFactory` is recommended. Otherwise returned from
    :func:`TelldusCore.add_device` or :func:`TelldusCore.devices`.
    """

    PARAMETERS = ["devices", "house", "unit", "code", "system", "units",
                  "fade"]

    def __init__(self, id, lib=None):
        super(Device, self).__init__()

        lib = lib or Library()
        super(Device, self).__setattr__('id', id)
        super(Device, self).__setattr__('lib', lib)

    def remove(self):
        """Remove the device from Telldus Core."""
        return self.lib.tdRemoveDevice(self.id)

    def __getattr__(self, name):
        if name == 'name':
            func = self.lib.tdGetName
        elif name == 'protocol':
            func = self.lib.tdGetProtocol
        elif name == 'model':
            func = self.lib.tdGetModel
        elif name == 'type':
            func = self.lib.tdGetDeviceType
        else:
            raise AttributeError(name)
        return func(self.id)

    def __setattr__(self, name, value):
        if name == 'name':
            func = self.lib.tdSetName
        elif name == 'protocol':
            func = self.lib.tdSetProtocol
        elif name == 'model':
            func = self.lib.tdSetModel
        else:
            raise AttributeError(name)
        func(self.id, value)

    def parameters(self):
        """Get dict with all set parameters."""
        parameters = {}
        for name in self.PARAMETERS:
            try:
                parameters[name] = self.get_parameter(name)
            except AttributeError:
                pass
        return parameters

    def get_parameter(self, name):
        """Get a parameter."""
        default_value = "$%!)(INVALID)(!%$"
        value = self.lib.tdGetDeviceParameter(self.id, name, default_value)
        if value == default_value:
            raise AttributeError(name)
        return value

    def set_parameter(self, name, value):
        """Set a parameter."""
        self.lib.tdSetDeviceParameter(self.id, name, str(value))

    def turn_on(self):
        """Turn on the device."""
        self.lib.tdTurnOn(self.id)

    def turn_off(self):
        """Turn off the device."""
        self.lib.tdTurnOff(self.id)

    def bell(self):
        """Send "bell" command to the device."""
        self.lib.tdBell(self.id)

    def dim(self, level):
        """Dim the device.

        :param int level: The level to dim to in the range [0, 255].
        """
        self.lib.tdDim(self.id, level)

    def execute(self):
        """Send "execute" command to the device."""
        self.lib.tdExecute(self.id)

    def up(self):
        """Send "up" command to the device."""
        self.lib.tdUp(self.id)

    def down(self):
        """Send "down" command to the device."""
        self.lib.tdDown(self.id)

    def stop(self):
        """Send "stop" command to the device."""
        self.lib.tdStop(self.id)

    def learn(self):
        """Send "learn" command to the device."""
        self.lib.tdLearn(self.id)

    def methods(self, methods_supported):
        """Query the device for supported methods."""
        return self.lib.tdMethods(self.id, methods_supported)

    def last_sent_command(self, methods_supported):
        """Get the last sent (or seen) command."""
        return self.lib.tdLastSentCommand(self.id, methods_supported)

    def last_sent_value(self):
        """Get the last sent (or seen) value."""
        try:
            return int(self.lib.tdLastSentValue(self.id))
        except ValueError:
            return None


class DeviceGroup(Device):
    """Extends :class:`Device` with methods for managing a group

    E.g. when a group is turned on, all devices in that group are turned on.
    """

    def add_to_group(self, devices):
        """Add device(s) to the group."""
        ids = {d.id for d in self.devices_in_group()}
        ids.update(self._device_ids(devices))
        self._set_group(ids)

    def remove_from_group(self, devices):
        """Remove device(s) from the group."""
        ids = {d.id for d in self.devices_in_group()}
        ids.difference_update(self._device_ids(devices))
        self._set_group(ids)

    def devices_in_group(self):
        """Fetch list of devices in group."""
        try:
            devices = self.get_parameter('devices')
        except AttributeError:
            return []

        ctor = DeviceFactory
        return [ctor(int(x), lib=self.lib) for x in devices.split(',') if x]

    @staticmethod
    def _device_ids(devices):
        try:
            iter(devices)
        except TypeError:
            devices = [devices]

        ids = set()
        for device in devices:
            try:
                ids.add(device.id)
            except AttributeError:
                # Assume device is id
                ids.add(int(device))
        return ids

    def _set_group(self, ids):
        self.set_parameter('devices', ','.join([str(x) for x in ids]))


class Sensor(object):
    """Represents a sensor.

    Returned from :func:`TelldusCore.sensors`
    """

    DATATYPES = {"temperature": const.TELLSTICK_TEMPERATURE,
                 "humidity": const.TELLSTICK_HUMIDITY,
                 "rainrate": const.TELLSTICK_RAINRATE,
                 "raintotal": const.TELLSTICK_RAINTOTAL,
                 "winddirection": const.TELLSTICK_WINDDIRECTION,
                 "windaverage": const.TELLSTICK_WINDAVERAGE,
                 "windgust": const.TELLSTICK_WINDGUST}

    def __init__(self, protocol, model, id, datatypes, lib=None):
        super(Sensor, self).__init__()
        self.protocol = protocol
        self.model = model
        self.id = id
        self.datatypes = datatypes
        self.lib = lib or Library()

    def has_value(self, datatype):
        """Return True if the sensor supports the given data type.

        sensor.has_value(TELLSTICK_TEMPERATURE) is identical to calling
        sensor.has_temperature().
        """
        return (self.datatypes & datatype) != 0

    def value(self, datatype):
        """Return the :class:`SensorValue` for the given data type.

        sensor.value(TELLSTICK_TEMPERATURE) is identical to calling
        sensor.temperature().
        """
        value = self.lib.tdSensorValue(
            self.protocol, self.model, self.id, datatype)
        return SensorValue(datatype, value['value'], value['timestamp'])

    def __getattr__(self, name):
        typename = name.replace("has_", "", 1)
        if typename in Sensor.DATATYPES:
            datatype = Sensor.DATATYPES[typename]
            if name == typename:
                return lambda: self.value(datatype)
            else:
                return lambda: self.has_value(datatype)
        raise AttributeError(name)


class SensorValue(object):
    """Represents a single sensor value.

    Returned from :func:`Sensor.value`.
    """

    def __init__(self, datatype, value, timestamp):
        super(SensorValue, self).__init__()
        self.datatype = datatype
        self.value = value
        self.timestamp = timestamp

    def __getattr__(self, name):
        if name == "datetime":
            return datetime.fromtimestamp(self.timestamp)
        raise AttributeError(name)


class Controller(object):
    """Represents a Telldus controller.

    Returned from :func:`TelldusCore.controllers`
    """

    def __init__(self, id, type, lib=None):
        lib = lib or Library()

        super(Controller, self).__init__()
        super(Controller, self).__setattr__('id', id)
        super(Controller, self).__setattr__('type', type)
        super(Controller, self).__setattr__('lib', lib)

    def __getattr__(self, name):
        try:
            return self.lib.tdControllerValue(self.id, name)
        except TelldusError as e:
            if e.error == const.TELLSTICK_ERROR_METHOD_NOT_SUPPORTED:
                raise AttributeError(name)
            raise

    def __setattr__(self, name, value):
        try:
            self.lib.tdSetControllerValue(self.id, name, value)
        except TelldusError as e:
            if e.error == const.TELLSTICK_ERROR_SYNTAX:
                raise AttributeError(name)
            raise
