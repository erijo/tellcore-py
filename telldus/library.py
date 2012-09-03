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

from ctypes import c_bool, c_char_p, c_int, c_ubyte, c_ulong, c_void_p
from ctypes import byref, create_string_buffer, POINTER, sizeof, string_at
import platform


if platform.system() == 'Windows':
    from ctypes import WINFUNCTYPE as FUNCTYPE, windll as DllLoader
    LIBRARY_NAME = 'TelldusCore.dll'
else:
    from ctypes import CFUNCTYPE as FUNCTYPE, cdll as DllLoader
    LIBRARY_NAME = 'libtelldus-core.so.2'

DEVICE_EVENT_FUNC = FUNCTYPE(
    None, c_int, c_int, c_char_p, c_int, c_void_p)
DEVICE_CHANGE_EVENT_FUNC = FUNCTYPE(
    None, c_int, c_int, c_int, c_int, c_void_p)
RAW_DEVICE_EVENT_FUNC = FUNCTYPE(
    None, c_char_p, c_int, c_int, c_void_p)
SENSOR_EVENT_FUNC = FUNCTYPE(
    None, c_char_p, c_char_p, c_int, c_int, c_char_p, c_int, c_int, c_void_p)
CONTROLLER_EVENT_FUNC = FUNCTYPE(
    None, c_int, c_int, c_int, c_char_p, c_int, c_void_p)


class TelldusError(Exception):
    """Error returned from Telldus API.
    """
    def __init__(self, error):
        super(TelldusError, self).__init__()
        self.error = error

    def __str__(self):
        msg = Library().tdGetErrorString(self.error)
        return "%s (%d)" % (msg, self.error)


class Library(object):
    _lib = None
    _refcount = 0
    _callbacks = {}

    _functions = {
        'tdInit': [None, []],
        'tdClose': [None, []],
        'tdReleaseString': [None, [c_ulong]],
        'tdGetErrorString': [c_char_p, [c_int]],

        'tdRegisterDeviceEvent':
            [c_int, [DEVICE_EVENT_FUNC, c_void_p]],
        'tdRegisterDeviceChangeEvent':
            [c_int, [DEVICE_CHANGE_EVENT_FUNC, c_void_p]],
        'tdRegisterRawDeviceEvent':
            [c_int, [RAW_DEVICE_EVENT_FUNC, c_void_p]],
        'tdRegisterSensorEvent':
            [c_int, [SENSOR_EVENT_FUNC, c_void_p]],
        'tdRegisterControllerEvent':
            [c_int, [CONTROLLER_EVENT_FUNC, c_void_p]],
        'tdUnregisterCallback': [c_int, [c_int]],

        'tdTurnOn': [c_int, [c_int]],
        'tdTurnOff': [c_int, [c_int]],
        'tdBell': [c_int, [c_int]],
        'tdDim': [c_int, [c_int, c_ubyte]],
        'tdExecute': [c_int, [c_int]],
        'tdUp': [c_int, [c_int]],
        'tdDown': [c_int, [c_int]],
        'tdStop': [c_int, [c_int]],
        'tdLearn': [c_int, [c_int]],
        'tdMethods': [c_int, [c_int, c_int]],
        'tdLastSentCommand': [c_int, [c_int, c_int]],
        'tdLastSentValue': [c_char_p, [c_int]],

        'tdGetNumberOfDevices': [c_int, []],
        'tdGetDeviceId': [c_int, [c_int]],
        'tdGetDeviceType': [c_int, [c_int]],

        'tdGetName': [c_char_p, [c_int]],
        'tdSetName': [c_bool, [c_int, c_char_p]],
        'tdGetProtocol': [c_char_p, [c_int]],
        'tdSetProtocol': [c_bool, [c_int, c_char_p]],
        'tdGetModel': [c_char_p, [c_int]],
        'tdSetModel': [c_bool, [c_int, c_char_p]],

        'tdGetDeviceParameter': [c_char_p, [c_int, c_char_p, c_char_p]],
        'tdSetDeviceParameter': [c_bool, [c_int, c_char_p, c_char_p]],

        'tdAddDevice': [c_int, []],
        'tdRemoveDevice': [c_bool, [c_int]],

        'tdSendRawCommand': [c_int, [c_char_p, c_int]],

        'tdConnectTellStickController': [None, [c_int, c_int, c_char_p]],
        'tdDisconnectTellStickController': [None, [c_int, c_int, c_char_p]],

        'tdSensor': [c_int, [c_char_p, c_int, c_char_p, c_int,
                             POINTER(c_int), POINTER(c_int)]],
        'tdSensorValue': [c_int, [c_char_p, c_char_p, c_int, c_int,
                                  c_char_p, c_int, POINTER(c_int)]],

        'tdController': [c_int, [POINTER(c_int), POINTER(c_int),
                                 c_char_p, c_int, POINTER(c_int)]],
        'tdControllerValue': [c_int, [c_int, c_char_p, c_char_p, c_int]],
        'tdSetControllerValue': [c_int, [c_int, c_char_p, c_char_p]],
        'tdRemoveController': [c_int, [c_int]],
   }

    def _setup_functions(self, lib):
        def check_result(result, func, args):
            if result < 0:
                raise TelldusError(result)
            return result

        def free_string(result, func, args):
            if result != 0:
                string = string_at(result)
                lib.tdReleaseString(result)
                return string
            return None

        for name, signature in self._functions.items():
            try:
                func = getattr(lib, name)
                func.restype = signature[0]
                func.argtypes = signature[1]

                if func.restype == c_int:
                    func.errcheck = check_result
                elif func.restype == c_char_p:
                    func.restype = c_ulong
                    func.errcheck = free_string
            except AttributeError:
                # Older version of the lib don't have all the functions
                pass

    def __init__(self, name=LIBRARY_NAME):
        """Load and initialize the Telldus core library.

        The library is only initialized the first time this object is
        created. Subsequent instances uses the same library instance.
        """
        super(Library, self).__init__()

        if Library._lib is None:
            assert Library._refcount == 0

            lib = DllLoader.LoadLibrary(name)
            self._setup_functions(lib)
            lib.tdInit()
            Library._lib = lib

        Library._refcount += 1

    def __del__(self):
        """Close and unload the Telldus core library.

        Only closed and unloaded if this is the last instance sharing the same
        library instance.
        """
        # Happens if the LoadLibrary call fails
        if Library._lib is None:
            assert Library._refcount == 0
            return

        assert Library._refcount >= 1
        Library._refcount -= 1

        if Library._refcount == 0:
            for callback in list(self._callbacks.keys()):
                try:
                    self.tdUnregisterCallback(callback)
                except:
                    pass

            Library._lib.tdClose()
            Library._lib = None

    def __getattr__(self, name):
        if name in self._functions:
            return getattr(self._lib, name)
        raise AttributeError(name)

    def tdInit(self):
        raise NotImplementedError('should not be called explicitly')

    def tdClose(self):
        raise NotImplementedError('should not be called explicitly')

    def tdReleaseString(self, string):
        raise NotImplementedError('should not be called explicitly')

    def tdRegisterDeviceEvent(self, callback):
        func = DEVICE_EVENT_FUNC(callback)
        id_ = self._lib.tdRegisterDeviceEvent(func, None)
        self._callbacks[id_] = func
        return id_

    def tdRegisterDeviceChangeEvent(self, callback):
        func = DEVICE_CHANGE_EVENT_FUNC(callback)
        id_ = self._lib.tdRegisterDeviceChangeEvent(func, None)
        self._callbacks[id_] = func
        return id_

    def tdRegisterRawDeviceEvent(self, callback):
        func = RAW_DEVICE_EVENT_FUNC(callback)
        id_ = self._lib.tdRegisterRawDeviceEvent(func, None)
        self._callbacks[id_] = func
        return id_

    def tdRegisterSensorEvent(self, callback):
        func = SENSOR_EVENT_FUNC(callback)
        id_ = self._lib.tdRegisterSensorEvent(func, None)
        self._callbacks[id_] = func
        return id_

    def tdRegisterControllerEvent(self, callback):
        func = CONTROLLER_EVENT_FUNC(callback)
        id_ = self._lib.tdRegisterControllerEvent(func, None)
        self._callbacks[id_] = func
        return id_

    def tdUnregisterCallback(self, id_):
        del self._callbacks[id_]
        self._lib.tdUnregisterCallback(id_)

    def tdSensor(self):
        protocol = create_string_buffer(20)
        model = create_string_buffer(20)
        id_ = c_int()
        datatypes = c_int()

        self._lib.tdSensor(protocol, sizeof(protocol), model, sizeof(model),
                           byref(id_), byref(datatypes))
        return { 'protocol': protocol.value, 'model': model.value,
                 'id': id_.value, 'datatypes': datatypes.value }

    def tdSensorValue(self, protocol, model, id_, datatype):
        value = create_string_buffer(20)
        timestamp = c_int()

        self._lib.tdSensorValue(protocol, model, id_, datatype,
                                value, sizeof(value), byref(timestamp))
        return { 'value': value.value, 'timestamp': timestamp.value }

    def tdController(self):
        id_ = c_int()
        type_ = c_int()
        name = create_string_buffer(255)
        available = c_int()

        self._lib.tdController(byref(id_), byref(type_), name, sizeof(name),
                               byref(available))
        return { 'id': id_.value, 'type': type_.value,
                 'name': name.value, 'available': available.value}

    def tdControllerValue(self, id_, name):
        value = create_string_buffer(255)

        self._lib.tdControllerValue(id_, name, value, sizeof(value))
        return value.value
