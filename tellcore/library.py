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

from ctypes import c_bool, c_char_p, c_int, c_ubyte, c_void_p
from ctypes import byref, cast, create_string_buffer, POINTER, sizeof
import platform
import threading

import tellcore.constants as const


if platform.system() == 'Windows':
    from ctypes import WINFUNCTYPE as FUNCTYPE, windll as DllLoader
    LIBRARY_NAME = 'TelldusCore.dll'
else:
    from ctypes import CFUNCTYPE as FUNCTYPE, cdll as DllLoader
    if platform.system() == 'Darwin':
        from ctypes.util import find_library
        LIBRARY_NAME = find_library('TelldusCore') or \
            '/Library/Frameworks/TelldusCore.framework/TelldusCore'
    else:
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
    """Error returned from Telldus Core API.

    Automatically raised when a function in the C API returns an error.

    Attributes:
        error: The error code constant (one of TELLSTICK_ERROR_* from
        :mod:`tellcore.constants`).
    """

    def __init__(self, error, lib=None):
        super(TelldusError, self).__init__()
        self.error = error
        self.lib = lib or Library()

    def __str__(self):
        """Return the human readable error string."""
        msg = self.lib.tdGetErrorString(self.error)
        return "%s (%d)" % (msg, self.error)


class BaseCallbackDispatcher(object):
    """Base callback dispatcher class.

    Inherit from this class and override the :func:`on_callback` method to
    change how callbacks are dispatched.
    """

    def on_callback(self, callback, *args):
        """Called from the callback thread when an event is received.

        :param callable callback: The callback function to call.
        :param args: The arguments to pass to the callback.
        """
        raise NotImplementedError


class DirectCallbackDispatcher(BaseCallbackDispatcher):
    """Dispatches callbacks directly.

    Since the callback is dispatched directly, the callback is called in the
    callback thread.
    """

    def on_callback(self, callback, *args):
        callback(*args)


class Library(object):
    """Wrapper around the Telldus Core C API.

    With the exception of tdInit, tdClose and tdReleaseString, all functions in
    the C API (see `Telldus Core documentation
    <http://developer.telldus.com/doxygen/group__core.html>`_) can be
    called. The parameters are the same as in the C API documentation. The
    return value are mostly the same as for the C API, except for functions
    with multiple out parameters.

    In addition, this class:
       * automatically frees memory for strings returned from the C API,
       * converts errors returned from functions into
         (:class:`TelldusError`) exceptions,
       * transparently converts between Python strings and C style strings.
    """

    STRING_ENCODING = 'utf-8'
    DECODE_STRINGS = True

    class c_string_p(c_char_p):
        def __init__(self, param):
            c_char_p.__init__(self, param.encode(Library.STRING_ENCODING))

        @classmethod
        def from_param(cls, param):
            if type(param) is str:
                return cls(param)
            try:
                if type(param) is unicode:
                    return cls(param)
            except NameError:
                pass  # The unicode type does not exist in python 3
            return c_char_p.from_param(param)

    # Must be a separate class (i.e. not part of Library), to avoid circular
    # references when saving the wrapper callback function in a class with a
    # destructor, as the destructor is not called in that case.
    class CallbackWrapper(object):
        def __init__(self, dispatcher):
            self._callbacks = {}
            self._lock = threading.Lock()
            self._dispatcher = dispatcher

        def get_callback_ids(self):
            with self._lock:
                return list(self._callbacks.keys())

        def register_callback(self, registrator, functype, callback):
            wrapper = functype(self._callback)
            with self._lock:
                cid = registrator(wrapper, None)
                self._callbacks[cid] = (wrapper, callback)
                return cid

        def unregister_callback(self, cid):
            with self._lock:
                del self._callbacks[cid]

        def _callback(self, *in_args):
            args = []
            # Convert all char* parameters (i.e. bytes) to proper python
            # strings
            for arg in in_args:
                if type(arg) is bytes:
                    args.append(arg.decode(Library.STRING_ENCODING))
                else:
                    args.append(arg)

            # Get the real callback and the dispatcher
            with self._lock:
                try:
                    # args[-2] is callback id
                    (wrapper, callback) = self._callbacks[args[-2]]
                except KeyError:
                    return
                dispatcher = self._dispatcher

            # Dispatch the callback, dropping the last parameter which is the
            # context and always None.
            try:
                dispatcher.on_callback(callback, *args[:-1])
            except:
                pass

    _lib = None
    _refcount = 0

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
        def check_int_result(result, func, args):
            if result < 0:
                raise TelldusError(result)
            return result

        def check_bool_result(result, func, args):
            if not result:
                raise TelldusError(const.TELLSTICK_ERROR_DEVICE_NOT_FOUND)
            return result

        def free_string(result, func, args):
            string = cast(result, c_char_p).value
            if string is not None:
                lib.tdReleaseString(result)
                if Library.DECODE_STRINGS:
                    string = string.decode(Library.STRING_ENCODING)
            return string

        for name, signature in Library._functions.items():
            try:
                func = getattr(lib, name)
                func.restype = signature[0]
                func.argtypes = signature[1]

                if func.restype == c_int:
                    func.errcheck = check_int_result
                elif func.restype == c_bool:
                    func.errcheck = check_bool_result
                elif func.restype == c_char_p:
                    func.restype = c_void_p
                    func.errcheck = free_string
            except AttributeError:
                # Older version of the lib don't have all the functions
                pass

    def __init__(self, name=None, callback_dispatcher=None):
        """Load and initialize the Telldus core library.

        The underlaying library is only initialized the first time this object
        is created. Subsequent instances uses the same underlaying library
        instance.

        :param str name: If None than the platform specific name of the
            Telldus library is used, but it can be e.g. an absolute path.

        :param callback_dispatcher: If callbacks are to be used, this parameter
            must refer to an instance of a class inheriting from
            :class:`BaseCallbackDispatcher`.

        """
        super(Library, self).__init__()

        if not Library._lib:
            assert Library._refcount == 0
            if name is None:
                name = LIBRARY_NAME

            lib = DllLoader.LoadLibrary(name)
            self._setup_functions(lib)
            lib.tdInit()
            Library._lib = lib

        Library._refcount += 1
        if callback_dispatcher is not None:
            self._callback_wrapper = Library.CallbackWrapper(
                callback_dispatcher)
        else:
            self._callback_wrapper = None

    def __del__(self):
        """Close and unload the Telldus core library.

        Any callback set up is removed.

        The underlaying library is only closed and unloaded if this is the last
        instance sharing the same underlaying library instance.
        """
        # Using self.__class__.* instead of Library.* here to avoid a
        # strange problem where Library could, in some runs, be None.

        # Happens if the LoadLibrary call fails
        if self.__class__._lib is None:
            assert self.__class__._refcount == 0
            return

        assert self.__class__._refcount >= 1
        self.__class__._refcount -= 1

        if self._callback_wrapper is not None:
            for cid in self._callback_wrapper.get_callback_ids():
                try:
                    self.tdUnregisterCallback(cid)
                except:
                    pass

        if self.__class__._refcount != 0:
            return

        # telldus-core before v2.1.2 (where tdController was added) does not
        # handle re-initialization after tdClose has been called (see Telldus
        # ticket 188).
        if hasattr(self.__class__._lib, "tdController"):
            self.__class__._lib.tdClose()
        self.__class__._lib = None

    def __getattr__(self, name):
        if name == 'callback_dispatcher':
            return self._callback_wrapper._dispatcher
        if name in Library._functions:
            return getattr(self._lib, name)
        raise AttributeError(name)

    def tdInit(self):
        raise NotImplementedError('should not be called explicitly')

    def tdClose(self):
        raise NotImplementedError('should not be called explicitly')

    def tdReleaseString(self, string):
        raise NotImplementedError('should not be called explicitly')

    def tdRegisterDeviceEvent(self, callback):
        assert(self._callback_wrapper is not None)
        return self._callback_wrapper.register_callback(
            self._lib.tdRegisterDeviceEvent, DEVICE_EVENT_FUNC, callback)

    def tdRegisterDeviceChangeEvent(self, callback):
        assert(self._callback_wrapper is not None)
        return self._callback_wrapper.register_callback(
            self._lib.tdRegisterDeviceChangeEvent, DEVICE_CHANGE_EVENT_FUNC,
            callback)

    def tdRegisterRawDeviceEvent(self, callback):
        assert(self._callback_wrapper is not None)
        return self._callback_wrapper.register_callback(
            self._lib.tdRegisterRawDeviceEvent, RAW_DEVICE_EVENT_FUNC,
            callback)

    def tdRegisterSensorEvent(self, callback):
        assert(self._callback_wrapper is not None)
        return self._callback_wrapper.register_callback(
            self._lib.tdRegisterSensorEvent, SENSOR_EVENT_FUNC, callback)

    def tdRegisterControllerEvent(self, callback):
        assert(self._callback_wrapper is not None)
        return self._callback_wrapper.register_callback(
            self._lib.tdRegisterControllerEvent, CONTROLLER_EVENT_FUNC,
            callback)

    def tdUnregisterCallback(self, cid):
        assert(self._callback_wrapper is not None)
        self._callback_wrapper.unregister_callback(cid)
        self._lib.tdUnregisterCallback(cid)

    def tdSensor(self):
        """Get the next sensor while iterating.

        :return: a dict with the keys: protocol, model, id, datatypes.
        """
        protocol = create_string_buffer(20)
        model = create_string_buffer(20)
        sid = c_int()
        datatypes = c_int()

        self._lib.tdSensor(protocol, sizeof(protocol), model, sizeof(model),
                           byref(sid), byref(datatypes))
        return {'protocol': self._to_str(protocol),
                'model': self._to_str(model),
                'id': sid.value, 'datatypes': datatypes.value}

    def tdSensorValue(self, protocol, model, sid, datatype):
        """Get the sensor value for a given sensor.

        :return: a dict with the keys: value, timestamp.
        """
        value = create_string_buffer(20)
        timestamp = c_int()

        self._lib.tdSensorValue(protocol, model, sid, datatype,
                                value, sizeof(value), byref(timestamp))
        return {'value': self._to_str(value), 'timestamp': timestamp.value}

    def tdController(self):
        """Get the next controller while iterating.

        :return: a dict with the keys: id, type, name, available.
        """
        cid = c_int()
        ctype = c_int()
        name = create_string_buffer(255)
        available = c_int()

        self._lib.tdController(byref(cid), byref(ctype), name, sizeof(name),
                               byref(available))
        return {'id': cid.value, 'type': ctype.value,
                'name': self._to_str(name), 'available': available.value}

    def tdControllerValue(self, cid, name):
        value = create_string_buffer(255)

        self._lib.tdControllerValue(cid, name, value, sizeof(value))
        return self._to_str(value)
