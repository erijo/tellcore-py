from ctypes import c_int, c_char_p, c_ulong, string_at
import platform

class _Library:
    _lib = None
    _refcount = 0

    _functions = {
        'tdInit': [None, []],
        'tdClose': [None, []],
        'tdReleaseString': [None, [c_ulong]],
        'tdGetErrorString': [c_char_p, [c_int]],
        'tdGetNumberOfDevices': [c_int, []],
    }

    _private_functions = [ 'tdInit', 'tdClose', 'tdReleaseString' ]

    def _make_string_releaser(self, name):
        def caller(self, *args):
            pointer = _Library._lib[name](*args)
            string = string_at(pointer)
            _Library._lib.tdReleaseString(pointer)
            return string
        return caller

    def _setup_functions(self, lib):
        for name, signature in _Library._functions.iteritems():
            lib[name].restype = signature[0]
            lib[name].argtypes = signature[1]

            if name in _Library._private_functions:
                continue

            if signature[0] == c_char_p:
                lib[name].restype = c_ulong                        
                setattr(self.__class__, name,
                        self._make_string_releaser(name))
            else:
                setattr(self.__class__, name, lib[name])

    def __init__(self):
        if _Library._lib is None:
            assert _Library._refcount == 0

            if platform.system() == 'Windows':
                from ctypes import windll
                lib = windll.LoadLibrary('TelldusCore.dll')
            else:
                from ctypes import cdll
                lib = cdll.LoadLibrary('libtelldus-core.so.2')

            self._setup_functions(lib)
            lib.tdInit()
            _Library._lib = lib

        _Library._refcount += 1

    def __del__(self):
        assert _Library._refcount >= 1

        _Library._refcount -= 1
        if _Library._refcount == 0:
            _Library._lib.tdClose()
            _Library._lib = None
