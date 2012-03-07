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

import telldus.library

class MockLibLoader(object):
    def __init__(self, mocklib):
        object.__init__(self)
        self.load_count = 0
        self.mocklib = mocklib

    def LoadLibrary(self, name):
        self.load_count += 1
        return self.mocklib

class MockTelldusCoreLib(object):
    def __init__(self):
        object.__init__(self)
        self.initialized = False

        def tdInit():
            if self.initialized:
                raise RuntimeError("already initialized")
            self.initialized = True
        self.tdInit.implementation = tdInit

        def tdClose():
            if not self.initialized:
                raise RuntimeError("not initialized")
            self.initialized = False
        self.tdClose.implementation = tdClose

    def __getattr__(self, name):
        if name in telldus.library.Library._functions:
            func = MockCFunction(name, self)
            object.__setattr__(self, name, func)
            return func
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in telldus.library.Library._functions:
            func = getattr(self, name)
            func.implementation = value
        else:
            object.__setattr__(self, name, value)

class MockCFunction(object):
    def __init__(self, name, lib):
        object.__init__(self)
        self.name = name
        self.lib = lib
        self.implementation = None
        self.restype = None
        self.argtypes = None
        self.errcheck = None

    def __call__(self, *args):
        if self.implementation is None:
            raise NotImplementedError("%s is not implemented" % self.name)

        if self.argtypes is None:
            raise NotImplementedError("%s not configured" % self.name)

        if len(self.argtypes) != len(args):
            raise TypeError("%s() takes exactly %d argument(s) (%d given)" %
                            (self.name, len(self.argument), len(args)))

        # Verify that the arguments are of correct type
        for c_type, value in zip(self.argtypes, args):
            if type(value) is not c_type:
                c_value = c_type(value)

        res = self.implementation(*args)

        if self.errcheck is not None:
            res = self.errcheck(res, self, args)
        return res
