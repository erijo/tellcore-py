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

Library = telldus.library.Library
telldus.library.string_at = lambda x: x

class Test(unittest.TestCase):
    def setUp(self):
        self.mocklib = mocklib.MockTelldusCoreLib()
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
        self.assertFalse(self.mocklib.initialized)
        lib1 = Library()
        self.assertTrue(self.mocklib.initialized)
        lib2 = Library()
        self.assertTrue(self.mocklib.initialized)

        lib1 = None
        self.assertTrue(self.mocklib.initialized)
        lib2 = None
        self.assertFalse(self.mocklib.initialized)

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

if __name__ == '__main__':
    unittest.main()
