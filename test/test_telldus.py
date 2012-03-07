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

import telldus.telldus

import mocklib

TelldusCore = telldus.telldus.TelldusCore
telldus.library.string_at = lambda x: x


class Test(unittest.TestCase):
    def setUp(self):
        self.mocklib = mocklib.MockTelldusCoreLib()

        self.mocklib.tdInit = lambda: None
        self.mocklib.tdClose = lambda: None
        self.mocklib.tdGetErrorString = lambda x: x
        self.mocklib.tdReleaseString = lambda x: None

        self.loader = mocklib.MockLibLoader(self.mocklib)
        telldus.library.DllLoader = self.loader

    def test_create(self):
        core = TelldusCore()

if __name__ == '__main__':
    unittest.main()
