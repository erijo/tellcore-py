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
from telldus.constants import *

import mocklib

TelldusCore = telldus.telldus.TelldusCore
telldus.library.string_at = lambda x: x


class Test(unittest.TestCase):
    def setUp(self):
        self.mocklib = mocklib.MockTelldusCoreLib()
        self.mockdispatcher = mocklib.MockEventDispatcher()

        self.mocklib.tdInit = lambda: None
        self.mocklib.tdClose = lambda: None
        self.mocklib.tdGetErrorString = lambda x: x
        self.mocklib.tdReleaseString = lambda x: None

        self.mockdispatcher.setup_lib_functions(self.mocklib)

        self.loader = mocklib.MockLibLoader(self.mocklib)
        telldus.library.DllLoader = self.loader

    def tearDown(self):
        self.mockdispatcher.stop()

    def event_tester(self, core, registrator, trigger, trigger_args):
        event_args = {}
        def callback(*args):
            event_args[args[-1]] = args[:-1]

        id1 = registrator(callback)
        id2 = registrator(callback)
        id3 = registrator(callback)
        id4 = registrator(callback)
        core.unregister_callback(id4)
        core.unregister_callback(id2)

        trigger(*trigger_args)
        core.process_pending_callbacks()

        self.assertEqual(event_args, { id1: trigger_args, id3: trigger_args })

    def test_device_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_device_event,
                          self.mockdispatcher.trigger_device_event,
                          (1, 2, b"foo"))

    def test_device_change_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_device_change_event,
                          self.mockdispatcher.trigger_device_change_event,
                          (3, 4, 5))

    def test_raw_device_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_raw_device_event,
                          self.mockdispatcher.trigger_raw_device_event,
                          (b"bar", 6))
        
    def test_sensor_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_sensor_event,
                          self.mockdispatcher.trigger_sensor_event,
                          (b"proto", b"model", 7, 8, b"value", 9))

    def test_controller_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_controller_event,
                          self.mockdispatcher.trigger_controller_event,
                          (10, 11, 12, b"new"))

    def test_sensors(self):
        self.sensor_index = 0
        def tdSensor(protocol, p_len, model, m_len, id_, datatypes):
            sensors = [{'protocol': b"proto_1", 'model': b"model_1", 'id': 1,
                        'datatypes': TELLSTICK_TEMPERATURE},
                       {'protocol': b"proto_2", 'model': b"model_2", 'id': 2,
                        'datatypes': TELLSTICK_TEMPERATURE},
                       {'protocol': b"proto_3", 'model': b"model_3", 'id': 3,
                        'datatypes': TELLSTICK_HUMIDITY}]
            if self.sensor_index < len(sensors):
                sensor = sensors[self.sensor_index]
                self.sensor_index += 1

                protocol.value = sensor['protocol']
                model.value = sensor['model']
                id_._obj.value = sensor['id']
                datatypes._obj.value = sensor['datatypes']
                return TELLSTICK_SUCCESS
            else:
                self.sensor_index = 0
                return TELLSTICK_ERROR_DEVICE_NOT_FOUND
        self.mocklib.tdSensor = tdSensor
        
        core = TelldusCore()
        sensors = core.sensors()

        self.assertEqual(3, len(sensors))
        self.assertEqual([b"proto_1", b"proto_2", b"proto_3"],
                         [s.protocol for s in sensors])
        self.assertEqual([b"model_1", b"model_2", b"model_3"],
                         [s.model for s in sensors])
        self.assertEqual([1, 2, 3], [s.id for s in sensors])
        self.assertEqual([TELLSTICK_TEMPERATURE, TELLSTICK_TEMPERATURE,
                          TELLSTICK_HUMIDITY],
                         [s.datatypes for s in sensors])

if __name__ == '__main__':
    unittest.main()
