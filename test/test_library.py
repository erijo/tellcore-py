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

import unittest

import telldus.library
from telldus.constants import *

import ctypes
import mocklib

Library = telldus.library.Library
TelldusError = telldus.library.TelldusError


class Test(unittest.TestCase):
    def setUp(self):
        self.initialized = False
        self.mocklib = mocklib.MockTelldusCoreLib()

        def tdInit():
            if self.initialized:
                raise RuntimeError("already initialized")
            self.initialized = True
        self.mocklib.tdInit = tdInit

        def tdClose():
            if not self.initialized:
                raise RuntimeError("not initialized")
            self.initialized = False
        self.mocklib.tdClose = tdClose

        self.loader = mocklib.MockLibLoader(self.mocklib)
        telldus.library.DllLoader = self.loader

    def test_libloader(self):
        self.assertEqual(self.loader.load_count, 0)
        lib = Library()
        self.assertEqual(self.loader.load_count, 1)
        self.assertEqual(lib._lib, self.mocklib)

    def test_oneinstance(self):
        """Test that the singleton works"""
        lib1 = Library()
        lib2 = Library()
        self.assertEqual(self.loader.load_count, 1)

        lib1 = lib2 = None
        lib = Library()
        self.assertEqual(self.loader.load_count, 2)

    def test_initialized(self):
        self.assertFalse(self.initialized)
        lib1 = Library()
        self.assertTrue(self.initialized)
        lib2 = Library()
        self.assertTrue(self.initialized)

        lib1 = None
        self.assertTrue(self.initialized)
        lib2 = None
        self.assertFalse(self.initialized)

    def test_private_methods(self):
        lib = Library()
        self.assertRaises(NotImplementedError, lib.tdInit)
        self.assertRaises(NotImplementedError, lib.tdClose)
        self.assertRaises(NotImplementedError, lib.tdReleaseString, 0)

    def test_string_releaser(self):
        """Test that all strings returned from core lib are released"""
        released = []
        def tdReleaseString(pointer):
            released.append(pointer.value)
        self.mocklib.tdReleaseString = tdReleaseString

        returned = []
        def tdGetErrorString(error):
            string = ctypes.c_char_p(
                ("error %d" % error).encode(Library.STRING_ENCODING))
            void_pointer = ctypes.cast(string, ctypes.c_void_p)
            returned.append(void_pointer.value)
            return string
        self.mocklib.tdGetErrorString = tdGetErrorString

        lib = Library()
        for i in range(-5, 0):
            lib.tdGetErrorString(i)

        self.assertEqual(len(released), 5)
        self.assertEqual(returned, released)

    def test_string_parameter(self):
        def int_strings(ignore, string1, string2="defaultValue"):
            self.assertEqual(string1, b"aString")
            if string2 != "defaultValue":
                self.assertEqual(string2, b"aSecondString")
            return 0

        string_int = lambda s, i: int_strings(i, s)
        ints_string = lambda i1, i2, s: int_strings(i1, s)
        strings_ignore = lambda s1, s2, *args: int_strings(0, s1, s2)
        int_string_ignore = lambda i, s, *args: int_strings(i, s)

        self.mocklib.tdSetName = int_strings
        self.mocklib.tdSetProtocol = int_strings
        self.mocklib.tdSetModel = int_strings
        self.mocklib.tdSetDeviceParameter = int_strings
        self.mocklib.tdGetDeviceParameter = int_strings
        self.mocklib.tdSendRawCommand = string_int
        self.mocklib.tdConnectTellStickController = ints_string
        self.mocklib.tdDisconnectTellStickController = ints_string
        self.mocklib.tdSensorValue = strings_ignore
        self.mocklib.tdControllerValue = int_string_ignore
        self.mocklib.tdSetControllerValue = int_strings

        lib = Library()

        lib.tdSetName(1, "aString")
        lib.tdSetProtocol(1, "aString")
        lib.tdSetModel(1, "aString")
        lib.tdSetDeviceParameter(1, "aString", "aSecondString")
        lib.tdGetDeviceParameter(1, "aString", "aSecondString")
        lib.tdSendRawCommand("aString", 1)
        lib.tdConnectTellStickController(0, 0, "aString")
        lib.tdDisconnectTellStickController(0, 0, "aString")
        lib.tdSensorValue("aString", "aSecondString", 0, 0)
        lib.tdControllerValue(1, "aString")
        lib.tdSetControllerValue(1, "aString", "aSecondString")

    def test_unicode(self):
        def tdSetName(id, name):
            self.assertEqual(name, u"\xe5\xe4\xf6".encode(
                    Library.STRING_ENCODING))
        self.mocklib.tdSetName = tdSetName

        lib = Library()

        lib.tdSetName(1, u"\xe5\xe4\xf6")

    def setup_callback(self, registered_ids, unregistered_ids):
        def tdRegisterEvent(*args):
            id_ = len(registered_ids) + 1
            registered_ids.append(id_)
            return id_
        self.mocklib.tdRegisterDeviceEvent = tdRegisterEvent
        self.mocklib.tdRegisterDeviceChangeEvent = tdRegisterEvent
        self.mocklib.tdRegisterRawDeviceEvent = tdRegisterEvent
        self.mocklib.tdRegisterSensorEvent = tdRegisterEvent
        self.mocklib.tdRegisterControllerEvent = tdRegisterEvent

        def tdUnregisterCallback(id_):
            unregistered_ids.append(id_)
            return TELLSTICK_SUCCESS
        self.mocklib.tdUnregisterCallback = tdUnregisterCallback

    def test_callback_cleanup(self):
        registered_ids = []
        unregistered_ids = []
        self.setup_callback(registered_ids, unregistered_ids)

        def callback(*args): pass

        lib = Library()
        lib.tdRegisterDeviceEvent(callback)
        lib.tdRegisterDeviceChangeEvent(callback)
        lib.tdRegisterRawDeviceEvent(callback)
        lib.tdRegisterSensorEvent(callback)
        lib.tdRegisterControllerEvent(callback)

        self.assertEqual(len(registered_ids), 5)
        self.assertEqual(len(unregistered_ids), 0)
        lib = None
        self.assertEqual(registered_ids, unregistered_ids)

    def test_callback_shared(self):
        registered_ids = []
        unregistered_ids = []
        self.setup_callback(registered_ids, unregistered_ids)

        def callback(*args): pass

        lib = Library()
        id_ = lib.tdRegisterDeviceEvent(callback)
        self.assertEqual(len(registered_ids), 1)
        self.assertEqual(len(unregistered_ids), 0)

        lib_copy = Library()
        lib = None

        self.assertEqual(len(unregistered_ids), 0)
        lib_copy.tdUnregisterCallback(id_)
        self.assertEqual(len(unregistered_ids), 1)

    def test_exception_on_error(self):
        def tdGetNumberOfDevices():
            return TELLSTICK_ERROR_CONNECTING_SERVICE
        self.mocklib.tdGetNumberOfDevices = tdGetNumberOfDevices

        lib = Library()
        with self.assertRaises(TelldusError) as cm:
            lib.tdGetNumberOfDevices()
        self.assertEqual(cm.exception.error,
                         TELLSTICK_ERROR_CONNECTING_SERVICE)

if __name__ == '__main__':
    unittest.main()
