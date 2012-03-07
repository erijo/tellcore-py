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

import mocklib
import telldus.library
from telldus.constants import *

Library = telldus.library.Library
TelldusError = telldus.library.TelldusError
telldus.library.string_at = lambda x: x

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

        self.mocklib.tdGetErrorString = lambda x: x
        self.mocklib.tdReleaseString = lambda x: None

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
            released.append(pointer)
        self.mocklib.tdReleaseString = tdReleaseString

        def tdGetErrorString(error):
            return 0xdeadbeaf + error
        self.mocklib.tdGetErrorString = tdGetErrorString

        lib = Library()
        returned = []
        for i in range(-5, 0):
            returned.append(lib.tdGetErrorString(i))

        self.assertEqual(len(released), 5)
        self.assertEqual(returned, released)

    def test_callback_cleanup(self):
        registered_ids = []
        def tdRegisterEvent(*args):
            id_ = len(registered_ids) + 1
            registered_ids.append(id_)
            return id_
        self.mocklib.tdRegisterDeviceEvent = tdRegisterEvent
        self.mocklib.tdRegisterDeviceChangeEvent = tdRegisterEvent
        self.mocklib.tdRegisterRawDeviceEvent = tdRegisterEvent
        self.mocklib.tdRegisterSensorEvent = tdRegisterEvent
        self.mocklib.tdRegisterControllerEvent = tdRegisterEvent

        unregistered_ids = []
        def tdUnregisterCallback(id_):
            unregistered_ids.append(id_)
        self.mocklib.tdUnregisterCallback = tdUnregisterCallback

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
