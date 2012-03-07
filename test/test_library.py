#!/usr/bin/python

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
            released.append(pointer.value)
        self.mocklib.tdReleaseString.implementation = tdReleaseString

        def tdGetErrorString(error):
            return 0xdeadbeaf + error.value
        self.mocklib.tdGetErrorString.implementation = tdGetErrorString

        lib = Library()
        returned = []
        for i in range(-5, 0):
            returned.append(lib.tdGetErrorString(i))

        self.assertEqual(len(released), 5)
        self.assertEqual(returned, released)

if __name__ == '__main__':
    unittest.main()
