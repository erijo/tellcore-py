# Copyright (c) 2012 Erik Johansson <erik@ejohansson.se>
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

from .constants import *
from .library import *


class CallbackManager(object):
    def __init__(self):
        super(CallbackManager, self).__init__()
        self.lib = Library()
        self.callbacks = {}
        self.queue = queue.Queue()

    def __del__(self):
        assert len(self.callbacks) == 0

    def _callback(self, *in_args):
        args = []
        # Convert all char* parameters (i.e. bytes) to proper python strings
        for arg in in_args:
            if type(arg) is bytes:
                args.append(arg.decode(Library.STRING_ENCODING))
            else:
                args.append(arg)
        self.queue.put(args)

    def process(self, **kwargs):
        try:
            args = self.queue.get(**kwargs)
            try:
                # args[-2] is callback id
                callback = self.callbacks[args[-2]]
                # args[-1] is context which is always None
                callback(*args[:-1])
            except KeyError:
                pass
            finally:
                self.queue.task_done()
        except queue.Empty:
            return False
        return True

    def process_pending(self):
        while self.process(block=False):
            pass

    def _register(self, registrator, callback):
        id = registrator(self._callback)
        self.callbacks[id] = callback
        return id

    def register_device_event(self, callback):
        return self._register(self.lib.tdRegisterDeviceEvent, callback)

    def register_device_change_event(self, callback):
        return self._register(self.lib.tdRegisterDeviceChangeEvent, callback)

    def register_raw_device_event(self, callback):
        return self._register(self.lib.tdRegisterRawDeviceEvent, callback)

    def register_sensor_event(self, callback):
        return self._register(self.lib.tdRegisterSensorEvent, callback)

    def register_controller_event(self, callback):
        return self._register(self.lib.tdRegisterControllerEvent, callback)

    def unregister(self, id):
        del self.callbacks[id]
        self.lib.tdUnregisterCallback(id)

    def unregister_all(self):
        for id in list(self.callbacks.keys()):
            self.unregister(id)


class TelldusCore(object):
    def __init__(self, library_path=None, callback_manager=None):
        super(TelldusCore, self).__init__()
        self.callbacks = None

        if library_path is not None:
            self.lib = Library(library_path)
        else:
            self.lib = Library()

        if callback_manager is not None:
            self.callbacks = callback_manager
        else:
            self.callbacks = CallbackManager()

    def __del__(self):
        if self.callbacks is not None:
            self.callbacks.unregister_all()

    def register_device_event(self, callback):
        return self.callbacks.register_device_event(callback)

    def register_device_change_event(self, callback):
        return self.callbacks.register_device_change_event(callback)

    def register_raw_device_event(self, callback):
        return self.callbacks.register_raw_device_event(callback)

    def register_sensor_event(self, callback):
        return self.callbacks.register_sensor_event(callback)

    def register_controller_event(self, callback):
        return self.callbacks.register_controller_event(callback)

    def unregister_callback(self, id):
        return self.callbacks.unregister(id)

    def process_pending_callbacks(self):
        self.callbacks.process_pending()

    def devices(self):
        devices = []
        count = self.lib.tdGetNumberOfDevices()
        for i in range(count):
            id = self.lib.tdGetDeviceId(i)
            devices.append(Device(id))
        return devices

    def sensors(self):
        sensors = []
        try:
            while True:
                sensor = self.lib.tdSensor()
                sensors.append(Sensor(**sensor))
        except TelldusError as e:
            if e.error != TELLSTICK_ERROR_DEVICE_NOT_FOUND:
                raise
        return sensors

    def controllers(self):
        controllers = []
        try:
            while True:
                controller = self.lib.tdController()
                controllers.append(Controller(**controller))
        except TelldusError as e:
            if e.error != TELLSTICK_ERROR_NOT_FOUND:
                raise
        return controllers

    def add_device(self, name, protocol, model=None, **parameters):
        device = Device(self.lib.tdAddDevice())
        try:
            device.name = name
            device.protocol = protocol
            if model is not None:
                device.model = model
            for key, value in parameters.items():
                device.set_parameter(key, value)
            return device
        except Exception as e:
            try:
                device.remove()
            except:
                pass
            raise e

    def send_raw_command(self, command, reserved=0):
        return self.lib.tdSendRawCommand(command, reserved)

    def connect_controller(self, vid, pid, serial):
        self.lib.tdConnectTellStickController(vid, pid, serial)

    def disconnect_controller(self, vid, pid, serial):
        self.lib.tdDisconnectTellStickController(vid, pid, serial)


class Device(object):
    PARAMETERS = ["devices", "house", "unit", "code", "system", "units",
                  "fade"]

    def __init__(self, id):
        super(Device, self).__init__()
        super(Device, self).__setattr__('id', id)
        super(Device, self).__setattr__('lib', Library())

    def remove(self):
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
        return func(self.id, value)

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
        return self.lib.tdSetDeviceParameter(self.id, name, str(value))

    def turn_on(self):
        self.lib.tdTurnOn(self.id)

    def turn_off(self):
        self.lib.tdTurnOff(self.id)

    def bell(self):
        self.lib.tdBell(self.id)

    def dim(self, level):
        self.lib.tdDim(self.id, level)

    def execute(self):
        self.lib.tdExecute(self.id)

    def up(self):
        self.lib.tdUp(self.id)

    def down(self):
        self.lib.tdDown(self.id)

    def stop(self):
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
    def __init__(self, protocol, model, id, datatypes):
        super(Sensor, self).__init__()
        self.protocol = protocol
        self.model = model
        self.id = id
        self.datatypes = datatypes
        self.lib = Library()

    def value(self, datatype):
        value = self.lib.tdSensorValue(
            self.protocol, self.model, self.id, datatype)
        return SensorValue(value['value'], value['timestamp'])

    def has_temperature(self):
        return self.datatypes & TELLSTICK_TEMPERATURE != 0

    def has_humidity(self):
        return self.datatypes & TELLSTICK_HUMIDITY != 0

    def temperature(self):
        return self.value(TELLSTICK_TEMPERATURE)

    def humidity(self):
        return self.value(TELLSTICK_HUMIDITY)


class SensorValue(object):
    __slots__ = ["value", "timestamp"]

    def __init__(self, value, timestamp):
        super(SensorValue, self).__init__()
        self.value = value
        self.timestamp = timestamp


class Controller(object):
    def __init__(self, id, type, name, available):
        super(Controller, self).__init__()
        super(Controller, self).__setattr__('id', id)
        super(Controller, self).__setattr__('type', type)
        super(Controller, self).__setattr__('name', name)
        super(Controller, self).__setattr__('available', available)
        super(Controller, self).__setattr__('lib', Library())

    def __getattr__(self, name):
        try:
            return self.lib.tdControllerValue(self.id, name)
        except TelldusError as e:
            if e.error == TELLSTICK_ERROR_METHOD_NOT_SUPPORTED:
                raise AttributeError(name)
            raise

    def __setattr__(self, name, value):
        try:
            self.lib.tdSetControllerValue(self.id, name, value)
        except TelldusError as e:
            if e.error == TELLSTICK_ERROR_SYNTAX:
                raise AttributeError(name)
            raise
