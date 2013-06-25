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

from tellcore.telldus import TelldusCore, TelldusError, Device
from tellcore.constants import *
import tellcore.library

from ctypes import c_char_p, c_int, create_string_buffer
import mocklib


class Test(unittest.TestCase):
    def setUp(self):
        self.mocklib = mocklib.MockTelldusCoreLib()
        self.mockdispatcher = mocklib.MockEventDispatcher()
        self.mockdispatcher.setup_lib_functions(self.mocklib)

        self.loader = mocklib.MockLibLoader(self.mocklib)
        tellcore.library.DllLoader = self.loader

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

        callback_args = []
        for arg in trigger_args:
            if type(arg.value) is bytes:
                callback_args.append(arg.value.decode(
                        tellcore.library.Library.STRING_ENCODING))
            else:
                callback_args.append(arg.value)
        callback_args = tuple(callback_args)

        self.assertEqual(event_args, {id1: callback_args, id3: callback_args})

    def test_device_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_device_event,
                          self.mockdispatcher.trigger_device_event,
                          (c_int(1), c_int(2), c_char_p(b"foo")))

    def test_device_change_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_device_change_event,
                          self.mockdispatcher.trigger_device_change_event,
                          (c_int(3), c_int(4), c_int(5)))

    def test_raw_device_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_raw_device_event,
                          self.mockdispatcher.trigger_raw_device_event,
                          (c_char_p(b"bar"), c_int(6)))
        
    def test_sensor_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_sensor_event,
                          self.mockdispatcher.trigger_sensor_event,
                          (c_char_p(b"proto"), c_char_p(b"model"), c_int(7),
                           c_int(8), c_char_p(b"value"), c_int(9)))

    def test_controller_event(self):
        core = TelldusCore()
        self.event_tester(core, core.register_controller_event,
                          self.mockdispatcher.trigger_controller_event,
                          (c_int(10), c_int(11), c_int(12), c_char_p(b"new")))

    def test_devices(self):
        devs = {0: {'protocol': b"proto_1", 'model': b"model_1"},
                3: {'protocol': b"proto_2", 'model': b"model_2"},
                6: {'protocol': b"proto_3", 'model': b"model_3"}}

        self.mocklib.tdGetNumberOfDevices = lambda: len(devs)
        self.mocklib.tdGetDeviceId = lambda index: index * 3
        self.mocklib.tdGetProtocol = lambda id: \
            c_char_p(devs[id]['protocol'])
        self.mocklib.tdGetModel = lambda id: \
            c_char_p(devs[id]['model'])

        core = TelldusCore()
        devices = core.devices()

        self.assertEqual(3, len(devices))
        self.assertEqual(['proto_1', 'proto_2', 'proto_3'],
                         [d.protocol for d in devices])
        self.assertEqual(['model_1', 'model_2', 'model_3'],
                         [d.model for d in devices])

    def test_device(self):
        def actor(id):
            if id == 3:
                return TELLSTICK_SUCCESS
            else:
                return TELLSTICK_ERROR_DEVICE_NOT_FOUND
        self.mocklib.tdTurnOn = actor
        self.mocklib.tdTurnOff = actor
        self.mocklib.tdBell = lambda id: TELLSTICK_ERROR_METHOD_NOT_SUPPORTED

        device = Device(3)
        device.turn_on()
        device.turn_off()
        self.assertRaises(TelldusError, device.bell)

        device = Device(4)
        self.assertRaises(TelldusError, device.turn_on)
        self.assertRaises(TelldusError, device.turn_off)
        self.assertRaises(TelldusError, device.bell)

    def test_sensors(self):
        self.sensor_index = 0
        def tdSensor(protocol, p_len, model, m_len, id, datatypes):
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
                id._obj.value = sensor['id']
                datatypes._obj.value = sensor['datatypes']
                return TELLSTICK_SUCCESS
            else:
                self.sensor_index = 0
                return TELLSTICK_ERROR_DEVICE_NOT_FOUND
        self.mocklib.tdSensor = tdSensor
        
        core = TelldusCore()
        sensors = core.sensors()

        self.assertEqual(3, len(sensors))
        self.assertEqual(["proto_1", "proto_2", "proto_3"],
                         [s.protocol for s in sensors])
        self.assertEqual(["model_1", "model_2", "model_3"],
                         [s.model for s in sensors])
        self.assertEqual([1, 2, 3], [s.id for s in sensors])
        self.assertEqual([TELLSTICK_TEMPERATURE, TELLSTICK_TEMPERATURE,
                          TELLSTICK_HUMIDITY],
                         [s.datatypes for s in sensors])

if __name__ == '__main__':
    unittest.main()
