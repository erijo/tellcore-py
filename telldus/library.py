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
from ctypes import byref, cast, create_string_buffer, POINTER, sizeof
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
    STRING_ENCODING = 'utf-8'

    class c_string_p(c_char_p):
        def __init__(self, string):
            if type(string) is str or type(string) is unicode:
                string = string.encode(Library.STRING_ENCODING)
            c_char_p.__init__(self, string)

    _lib = None
    _refcount = 0
    _callbacks = {}

    _functions = {
        'tdInit': [None, []],
        'tdClose': [None, []],
        'tdReleaseString': [None, [c_void_p]],
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
        'tdSetName': [c_bool, [c_int, c_string_p]],
        'tdGetProtocol': [c_char_p, [c_int]],
        'tdSetProtocol': [c_bool, [c_int, c_string_p]],
        'tdGetModel': [c_char_p, [c_int]],
        'tdSetModel': [c_bool, [c_int, c_string_p]],

        'tdGetDeviceParameter': [c_char_p, [c_int, c_string_p, c_string_p]],
        'tdSetDeviceParameter': [c_bool, [c_int, c_string_p, c_string_p]],

        'tdAddDevice': [c_int, []],
        'tdRemoveDevice': [c_bool, [c_int]],

        'tdSendRawCommand': [c_int, [c_string_p, c_int]],

        'tdConnectTellStickController': [None, [c_int, c_int, c_string_p]],
        'tdDisconnectTellStickController': [None, [c_int, c_int, c_string_p]],

        'tdSensor': [c_int, [c_char_p, c_int, c_char_p, c_int,
                             POINTER(c_int), POINTER(c_int)]],
        'tdSensorValue': [c_int, [c_string_p, c_string_p, c_int, c_int,
                                  c_char_p, c_int, POINTER(c_int)]],

        'tdController': [c_int, [POINTER(c_int), POINTER(c_int),
                                 c_char_p, c_int, POINTER(c_int)]],
        'tdControllerValue': [c_int, [c_int, c_string_p, c_char_p, c_int]],
        'tdSetControllerValue': [c_int, [c_int, c_string_p, c_string_p]],
        'tdRemoveController': [c_int, [c_int]],
    }

    def _to_str(self, char_p):
        return char_p.value.decode(Library.STRING_ENCODING)

    def _setup_functions(self, lib):
        def check_result(result, func, args):
            if result < 0:
                raise TelldusError(result)
            return result

        def free_string(result, func, args):
            string = cast(result, c_char_p).value
            if string is not None:
                lib.tdReleaseString(result)
                string = string.decode(Library.STRING_ENCODING)
            return string

        for name, signature in self._functions.items():
            try:
                func = getattr(lib, name)
                func.restype = signature[0]
                func.argtypes = signature[1]

                if func.restype == c_int:
                    func.errcheck = check_result
                elif func.restype == c_char_p:
                    func.restype = c_void_p
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
        id = self._lib.tdRegisterDeviceEvent(func, None)
        self._callbacks[id] = func
        return id

    def tdRegisterDeviceChangeEvent(self, callback):
        func = DEVICE_CHANGE_EVENT_FUNC(callback)
        id = self._lib.tdRegisterDeviceChangeEvent(func, None)
        self._callbacks[id] = func
        return id

    def tdRegisterRawDeviceEvent(self, callback):
        func = RAW_DEVICE_EVENT_FUNC(callback)
        id = self._lib.tdRegisterRawDeviceEvent(func, None)
        self._callbacks[id] = func
        return id

    def tdRegisterSensorEvent(self, callback):
        func = SENSOR_EVENT_FUNC(callback)
        id = self._lib.tdRegisterSensorEvent(func, None)
        self._callbacks[id] = func
        return id

    def tdRegisterControllerEvent(self, callback):
        func = CONTROLLER_EVENT_FUNC(callback)
        id = self._lib.tdRegisterControllerEvent(func, None)
        self._callbacks[id] = func
        return id

    def tdUnregisterCallback(self, id):
        del self._callbacks[id]
        self._lib.tdUnregisterCallback(id)

    def tdSensor(self):
        protocol = create_string_buffer(20)
        model = create_string_buffer(20)
        id = c_int()
        datatypes = c_int()

        self._lib.tdSensor(protocol, sizeof(protocol), model, sizeof(model),
                           byref(id), byref(datatypes))
        return {'protocol': self._to_str(protocol),
                'model': self._to_str(model),
                'id': id.value, 'datatypes': datatypes.value}

    def tdSensorValue(self, protocol, model, id, datatype):
        value = create_string_buffer(20)
        timestamp = c_int()

        self._lib.tdSensorValue(protocol, model, id, datatype,
                                value, sizeof(value), byref(timestamp))
        return {'value': self._to_str(value), 'timestamp': timestamp.value}

    def tdController(self):
        id = c_int()
        type = c_int()
        name = create_string_buffer(255)
        available = c_int()

        self._lib.tdController(byref(id), byref(type), name, sizeof(name),
                               byref(available))
        return {'id': id.value, 'type': type.value,
                'name': self._to_str(name), 'available': available.value}

    def tdControllerValue(self, id, name):
        value = create_string_buffer(255)

        self._lib.tdControllerValue(id, name, value, sizeof(value))
        return self._to_str(value)
