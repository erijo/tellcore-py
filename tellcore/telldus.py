# Copyright (c) 2012-2013 Erik Johansson <erik@ejohansson.se>
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


class QueuedCallbackDispatcher(BaseCallbackDispatcher):
    def __init__(self):
        super(QueuedCallbackDispatcher, self).__init__()
        self._queue = queue.Queue()

    def on_callback(self, callback, *args):
        self._queue.put((callback, args))

    def process_callback(self, block):
        try:
            (callback, args) = self._queue.get(block=block)
            try:
                callback(*args)
            finally:
                self._queue.task_done()
        except queue.Empty:
            return False
        return True


class TelldusCore(object):
    _callback_dispatcher = None

    def __init__(self, library_path=None, callback_dispatcher=None):
        super(TelldusCore, self).__init__()

        if library_path is not None:
            self.lib = Library(library_path)
        else:
            self.lib = Library()

        do_set_dispatcher = True
        if callback_dispatcher is not None:
            assert TelldusCore._callback_dispatcher is None
            TelldusCore._callback_dispatcher = callback_dispatcher
        elif TelldusCore._callback_dispatcher is None:
            TelldusCore._callback_dispatcher = QueuedCallbackDispatcher()
        else:
            do_set_dispatcher = False

        if do_set_dispatcher:
            self.lib.set_callback_dispatcher(TelldusCore._callback_dispatcher)

    def register_device_event(self, callback):
        return self.lib.tdRegisterDeviceEvent(callback)

    def register_device_change_event(self, callback):
        return self.lib.tdRegisterDeviceChangeEvent(callback)

    def register_raw_device_event(self, callback):
        return self.lib.tdRegisterRawDeviceEvent(callback)

    def register_sensor_event(self, callback):
        return self.lib.tdRegisterSensorEvent(callback)

    def register_controller_event(self, callback):
        return self.lib.tdRegisterControllerEvent(callback)

    def unregister_callback(self, id):
        self.lib.tdUnregisterCallback(id)

    def process_callback(self, block=True):
        """Dispatch a single callback in the current thread."""
        return TelldusCore._callback_dispatcher.process_callback(block=block)

    def process_pending_callbacks(self):
        """Dispatch all pending callbacks in the current thread."""
        while self.process_callback(block=False):
            pass

    def devices(self):
        """Return all known devices.

        :return: list of :class:`Device` instances.
        """
        devices = []
        count = self.lib.tdGetNumberOfDevices()
        for i in range(count):
            device = Device(self.lib.tdGetDeviceId(i), lib=self.lib)
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
        """Add a new device to Telldus Core."""
        device = Device(self.lib.tdAddDevice(), lib=self.lib)
        try:
            device.name = name
            device.protocol = protocol
            if model is not None:
                device.model = model
            for key, value in parameters.items():
                device.set_parameter(key, value)
            return device
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

    def send_raw_command(self, command, reserved=0):
        return self.lib.tdSendRawCommand(command, reserved)

    def connect_controller(self, vid, pid, serial):
        self.lib.tdConnectTellStickController(vid, pid, serial)

    def disconnect_controller(self, vid, pid, serial):
        self.lib.tdDisconnectTellStickController(vid, pid, serial)


class Device(object):
    """A device that can be controlled by Telldus Core.

    Can be instantiated directly if the id is known. Otherwise returned from
    :func:`TelldusCore.add_device` or :func:`TelldusCore.devices`.
    """

    PARAMETERS = ["devices", "house", "unit", "code", "system", "units",
                  "fade"]

    def __init__(self, id, lib=None):
        super(Device, self).__init__()

        lib = Library() if lib is None else lib
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
        parameters = {}
        for name in self.PARAMETERS:
            try:
                parameters[name] = self.get_parameter(name)
            except AttributeError:
                pass
        return parameters

    def get_parameter(self, name):
        default_value = "$%!)(INVALID)(!%$"
        value = self.lib.tdGetDeviceParameter(self.id, name, default_value)
        if value == default_value:
            raise AttributeError(name)
        return value

    def set_parameter(self, name, value):
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
        self.lib.tdLearn(self.id)

    def methods(self, methods_supported):
        return self.lib.tdMethods(self.id, methods_supported)

    def last_sent_command(self, methods_supported):
        return self.lib.tdLastSentCommand(self.id, methods_supported)

    def last_sent_value(self):
        return self.lib.tdLastSentValue(self.id)


class Sensor(object):
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
        self.lib = Library() if lib is None else lib

    def has_value(self, datatype):
        return (self.datatypes & datatype) != 0

    def value(self, datatype):
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
    __slots__ = ["datatype", "value", "timestamp"]

    def __init__(self, datatype, value, timestamp):
        super(SensorValue, self).__init__()
        self.datatype = datatype
        self.value = value
        self.timestamp = timestamp


class Controller(object):
    def __init__(self, id, type, lib=None):
        lib = Library() if lib is None else lib

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
