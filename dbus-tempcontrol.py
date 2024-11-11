#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dbus
from gi.repository import GLib
import pprint
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from dbus.mainloop.glib import DBusGMainLoop
import collections
import optparse
import configparser # for config/ini file


# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService, VeDbusItemExport, VeDbusItemImport
from settingsdevice import SettingsDevice


def to_native_type(data):                                                                                                      
        # Transform dbus types into native types                                                                               
        if isinstance(data, dbus.Struct):                                                                                      
                return tuple(to_native_type(x) for x in data)                                                                  
        elif isinstance(data, dbus.Array):                                                                                     
                return [to_native_type(x) for x in data]                                                                       
        elif isinstance(data, dbus.Dictionary):                                                                                
                return dict((to_native_type(k), to_native_type(v)) for (k, v) in data.items())                                 
        elif isinstance(data, dbus.Double):                                                                                    
                return float(data)                                                                                             
        elif isinstance(data, dbus.Boolean):                                                                                   
                return bool(data)                                                                                              
        elif isinstance(data, (dbus.String, dbus.ObjectPath)):                                                                 
                return str(data)                                                                                               
        elif isinstance(data, dbus.Signature):                                                                                 
                return str(Signature(data))                                                                                    
        else:
                return int(data)  




class TempControl():
    def __init__(self, servicename, deviceinstance, id, mpptid, relayControl, offTemp, onTemp):
        logging.debug('Initialize Service...')


        _c = lambda p, v: (str(v) + 'C')
        self.settings = None 
        self.id = id
        self.mpptid = mpptid
        self.relayControl = relayControl
        self.offTemp = offTemp
        self.onTemp = onTemp
        self.deviceinstance = deviceinstance
        self.dbusConn = dbus.SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus(private=True)
        self.mppt01relay = VeDbusItemImport(self.dbusConn, id, '/Relay/0/State')
        self.mppt01tempObj = self.dbusConn.get_object(id, '/Devices/0/VregLink')
        self._init_device_settings(deviceinstance)
        self.readMppt01Temp()

        self._dbusserviceMppt01 = VeDbusService("{}.can_{:02d}".format(servicename, deviceinstance), bus=self.dbusConn, register=False)
        self._dbusserviceMppt01.add_path('/DeviceInstance', deviceinstance)
        self._dbusserviceMppt01.add_path('/FirmwareVersion', 'v1.0')
        self._dbusserviceMppt01.add_path('/DataManagerVersion', '1.0')
        self._dbusserviceMppt01.add_path('/Serial', '12345%s' % mpptid)
        self._dbusserviceMppt01.add_path('/Mgmt/Connection', 've.can')
        self._dbusserviceMppt01.add_path('/ProductName', 'MPPT Temperature')
        self._dbusserviceMppt01.add_path('/ProductId', 0) 
        self._dbusserviceMppt01.add_path('/CustomName', self.settings['/Customname'], writeable=True, onchangecallback=self.customnameChanged)
        self._dbusserviceMppt01.add_path('/Temperature', None, gettextcallback=_c)
        self._dbusserviceMppt01.add_path('/Status', 0)
        self._dbusserviceMppt01.add_path('/TemperatureType', self.settings['/TemperatureType'], writeable=True, onchangecallback=self.tempTypeChanged)

        self._dbusserviceMppt01.register()
        if self.relayControl:
            self.updateMppt01RelayMode()




    def _init_device_settings(self, deviceinstance):
        if self.settings:
            return

        path = '/Settings/MPPTTempCtrl/{}'.format(deviceinstance)

        SETTINGS = {
            '/Customname':  [path + '/CustomName', 'MPPT%02d Temperatur' % self.mpptid, 0, 0],
            '/TemperatureType': [path+'/TemperatureType', 2, 0, 0]
        }

        self.settings = SettingsDevice(self.dbusConn, SETTINGS, self._setting_changed)

    def tempTypeChanged(self, path, val):
        self.settings['/TemperatureType'] = val
        return True

    def customnameChanged(self, path, val):
        self.settings['/Customname'] = val
        return True
  
    def _setting_changed(self, setting, oldvalue, newvalue):
        logging.info("setting changed, setting: %s, old: %s, new: %s" % (setting, oldvalue, newvalue))

        if setting == '/Customname':
          self._dbusserviceMppt01['/CustomName'] = newvalue
        if setting == '/TemperatureType':
          self._dbusserviceMppt01['/TemperatureType'] = newvalue
    
    def updateMppt01RelayMode(self):
        args = [60889]
        ret = self.mppt01tempObj.get_dbus_method('GetVreg','com.victronenergy.VregLink')(*args)
        data = to_native_type(ret[1])
        logging.info("MPPT%02d Relay mode: %d" % (self.mpptid, data[0]))
        if ( data[0] != 255):
            args = [60889, [255,0,0,0] ]
            ret = self.mppt01tempObj.get_dbus_method('SetVreg','com.victronenergy.VregLink')(*args)
            logging.info("MPPT%02d Relay mode changed to external control" % self.mpptid)

    def readMppt01Temp(self):
        args = [60891]
        ret = self.mppt01tempObj.get_dbus_method('GetVreg','com.victronenergy.VregLink')(*args) 
        data = to_native_type(ret[1])
        self.mppt01temp = (data[1]*256+data[0])/100 
    
    def update(self):
        self.readMppt01Temp()
        self._dbusserviceMppt01['/Temperature'] = self.mppt01temp
        if ( self.relayControl ):
            logging.info("Check temp for MPPT%02d" % self.mpptid)
            if ( self.mppt01temp >= self.onTemp and self.mppt01relay.get_value() != 1):
               self.mppt01relay.set_value(1)
            elif ( self.mppt01temp <= self.offTemp and self.mppt01relay.get_value() != 0):
               self.mppt01relay.set_value(0)
        logging.info("MPPT%02d Temperature: %.02f" % (self.mpptid , self.mppt01temp))
        logging.info("MPPT%02d Relay State: %d" % (self.mpptid , self.mppt01relay.get_value()))
        return True

def getConfig():
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config;



def main():
        print (" *********************************************** ")
        print (" T E M P C O N T RO L   M A I N   S T A R T E D   ")
        print (" *********************************************** ")
        print (" ")
        logHandler = RotatingFileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__))), mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)

        logging.basicConfig( format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                             datefmt='%Y-%m-%d %H:%M:%S',
                             level=logging.INFO,
                             handlers=[
                                logHandler,
                                #logging.FileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))),
                                logging.StreamHandler()
                             ])

        config = getConfig()

        DBusGMainLoop(set_as_default=True)

        dbusservice = {}
     
        mainloop = GLib.MainLoop()

        mpptCount = int(config['DEFAULT']['mpptcount'])
        updateInterval = int(config['DEFAULT']['updateInterval'])
        logging.info("Found %d MPPT configs" % mpptCount)

        for x in range(1,mpptCount+1):
            mpptid = x
            deviceinstance = int(config['MPPT%02d' % x]['deviceinstance'])
            id = config['MPPT%02d' % x]['id']
            relayControl = config['MPPT%02d' % x]['relayControl'] == 'True'
            onTemp = float(config['MPPT%02d' % x]['onTemp'])
            offTemp = float(config['MPPT%02d' %x]['offTemp'])
            dbusservice['%02d' % x] = TempControl(mpptid=x, servicename='com.victronenergy.temperature',deviceinstance=deviceinstance,id=id,relayControl = relayControl,onTemp = onTemp, offTemp = offTemp)
            GLib.timeout_add(updateInterval, dbusservice['%02d' %x].update)
            dbusservice['%02d' % x].update()

        mainloop.run()

if __name__ == "__main__":
        main()

