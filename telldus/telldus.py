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

from library import *

class TelldusCore(object):
    def __init__(self):
        object.__init__(self)
        self.lib = Library()

    def devices(self):
        devices = []
        count = self.lib.tdGetNumberOfDevices()
        for i in range(0, count):
            id_ = self.lib.tdGetDeviceId(i)
            devices.append(Device(id_))
        return devices

    def add_device(self, name, protocol, model=None, **parameters):
        device = Device(self.lib.tdAddDevice())
        device.name = name
        device.protocol = protocol
        if model is not None:
            device.model = model
        for key, value in parameters.iteritems():
            device.set_parameter(key, value)
        return device

class Device(object):
    def __init__(self, id_):
        object.__init__(self)
        object.__setattr__(self, 'id_', id_)
        object.__setattr__(self, 'lib', Library())

    def remove(self):
        return self.lib.tdRemoveDevice(self.id_)

    def __getattr__(self, name):
        if name == 'name':
            func = self.lib.tdGetName
        elif name == 'protocol':
            func = self.lib.tdGetProtocol
        elif name == 'model':
            func = self.lib.tdGetModel
        else:
            raise AttributeError(name)
        return func(self.id_)

    def __setattr__(self, name, value):
        if name == 'name':
            func = self.lib.tdSetName
        elif name == 'protocol':
            func = self.lib.tdSetProtocol
        elif name == 'model':
            func = self.lib.tdSetModel
        else:
            raise AttributeError(name)
        return func(self.id_, value)

    def __str__(self):
        desc = '/'.join([self.name, self.protocol, self.model])
        return "device-%d [%s]" % (self.id_, desc)

    def get_parameter(self, name, default_value):
        return self.lib.tdGetDeviceParameter(self.id_, name, default_value)

    def set_parameter(self, name, value):
        return self.lib.tdSetDeviceParameter(self.id_, name, value)

    def turn_on(self):
        self.lib.tdTurnOn(self.id_)

    def turn_off(self):
        self.lib.tdTurnOff(self.id_)

    def bell(self):
        self.lib.tdBell(self.id_)

    def dim(self, level):
        self.lib.tdDim(self.id_, level)

    def execute(self):
        self.lib.tdExecute(self.id_)

    def up(self):
        self.lib.tdUp(self.id_)

    def down(self):
        self.lib.tdDown(self.id_)

    def stop(self):
        self.lib.tdStop(self.id_)

    def learn(self):
        self.lib.tdLearn(self.id_)

    def methods(self, methods_supported):
        return self.lib.tdMethods(self.id_, methods_supported)

    def last_sent_command(self, methods_supported):
        return self.lib.tdLastSentCommand(self.id_, methods_supported)

    def last_sent_value(self):
        return self.lib.tdLastSentValue(self.id_)
