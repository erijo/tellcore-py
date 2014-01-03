# Copyright (c) 2012-2013 Erik Johansson <erik@ejohansson.se>
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

from ctypes import c_char_p, c_int
import gc
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
        gc.collect()

    def event_tester(self, core, registrator, trigger, trigger_args):
        event_args = {}

        def callback(*args):
            # Strip away callback id
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
                        'datatypes': TELLSTICK_HUMIDITY},
                       {'protocol': b"proto_3", 'model': b"model_3", 'id': 3,
                        'datatypes': TELLSTICK_RAINRATE},
                       {'protocol': b"proto_4", 'model': b"model_4", 'id': 4,
                        'datatypes': TELLSTICK_RAINTOTAL},
                       {'protocol': b"proto_5", 'model': b"model_5", 'id': 5,
                        'datatypes': TELLSTICK_WINDDIRECTION},
                       {'protocol': b"proto_6", 'model': b"model_6", 'id': 6,
                        'datatypes': TELLSTICK_WINDAVERAGE},
                       {'protocol': b"proto_7", 'model': b"model_7", 'id': 7,
                        'datatypes': TELLSTICK_WINDGUST}]
            if self.sensor_index < len(sensors):
                sensor = sensors[self.sensor_index]
                self.sensor_index += 1

                protocol.value = sensor['protocol']
                model.value = sensor['model']
                try:
                    id._obj.value = sensor['id']
                    datatypes._obj.value = sensor['datatypes']
                except AttributeError:
                    # With pypy we must use contents instead of _obj
                    id.contents.value = sensor['id']
                    datatypes.contents.value = sensor['datatypes']
                return TELLSTICK_SUCCESS
            else:
                self.sensor_index = 0
                return TELLSTICK_ERROR_DEVICE_NOT_FOUND
        self.mocklib.tdSensor = tdSensor

        def tdSensorValue(protocol, model, id, datatype, value, v_len, times):
            if datatype == 1 << (id - 1):
                value.value = ("%d" % (id * 100 + datatype)).encode(
                    tellcore.library.Library.STRING_ENCODING)
                return TELLSTICK_SUCCESS
            else:
                return TELLSTICK_ERROR_METHOD_NOT_SUPPORTED
        self.mocklib.tdSensorValue = tdSensorValue

        core = TelldusCore()
        sensors = core.sensors()

        self.assertEqual(7, len(sensors))
        self.assertEqual(["proto_%d" % i for i in range(1, 8)],
                         [s.protocol for s in sensors])
        self.assertEqual(["model_%d" % i for i in range(1, 8)],
                         [s.model for s in sensors])
        self.assertEqual(list(range(1, 8)),
                         [s.id for s in sensors])
        self.assertEqual([TELLSTICK_TEMPERATURE, TELLSTICK_HUMIDITY,
                          TELLSTICK_RAINRATE, TELLSTICK_RAINTOTAL,
                          TELLSTICK_WINDDIRECTION, TELLSTICK_WINDAVERAGE,
                          TELLSTICK_WINDGUST],
                         [s.datatypes for s in sensors])

        self.assertEqual([False]*0 + [True] + [False]*6,
                         [s.has_temperature() for s in sensors])
        self.assertEqual([False]*1 + [True] + [False]*5,
                         [s.has_humidity() for s in sensors])
        self.assertEqual([False]*2 + [True] + [False]*4,
                         [s.has_rainrate() for s in sensors])
        self.assertEqual([False]*3 + [True] + [False]*3,
                         [s.has_raintotal() for s in sensors])
        self.assertEqual([False]*4 + [True] + [False]*2,
                         [s.has_winddirection() for s in sensors])
        self.assertEqual([False]*5 + [True] + [False]*1,
                         [s.has_windaverage() for s in sensors])
        self.assertEqual([False]*6 + [True] + [False]*0,
                         [s.has_windgust() for s in sensors])

        self.assertEqual("%d" % (100 + TELLSTICK_TEMPERATURE),
                         sensors[0].temperature().value)
        self.assertEqual("%d" % (200 + TELLSTICK_HUMIDITY),
                         sensors[1].humidity().value)
        self.assertEqual("%d" % (300 + TELLSTICK_RAINRATE),
                         sensors[2].rainrate().value)
        self.assertEqual("%d" % (400 + TELLSTICK_RAINTOTAL),
                         sensors[3].raintotal().value)
        self.assertEqual("%d" % (500 + TELLSTICK_WINDDIRECTION),
                         sensors[4].winddirection().value)
        self.assertEqual("%d" % (600 + TELLSTICK_WINDAVERAGE),
                         sensors[5].windaverage().value)
        self.assertEqual("%d" % (700 + TELLSTICK_WINDGUST),
                         sensors[6].windgust().value)

if __name__ == '__main__':
    unittest.main()
