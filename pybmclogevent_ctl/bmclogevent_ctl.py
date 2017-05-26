#!/usr/bin/python -u

from obmc.events import EventManager, Event
import obmc_system_config as System
import os
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
import obmc.dbuslib.propertycacher as PropertyCacher
from obmc.dbuslib.bindings import get_dbus, DbusProperties, DbusObjectManager
from obmc.sensors import HwmonSensor as HwmonSensor

DBUS_NAME = 'org.openbmc.Sensors'
DBUS_INTERFACE = 'org.freedesktop.DBus.Properties'
SENSOR_VALUE_INTERFACE = 'org.openbmc.SensorValue'

_EVENT_MANAGER = EventManager()

def BmcLogEventMessages(objpath = "", s_event_identify="", s_assert="", \
                                    s_event_indicator="", s_evd_desc="", data={}):
    evd1 = 0
    evd2 = 0
    evd3 = 0
    serverity = Event.SEVERITY_INFO
    b_assert = 0
    event_dir = 0
    try:
        if 'BMC_LOGEVENT_CONFIG' not in dir(System) and \
          s_event_identify not in System.BMC_HEALTH_LOGEVENT_CONFIG:
            return False
        event_dir = System.BMC_LOGEVENT_CONFIG[s_event_identify]['Event Dir']

        if s_assert == "Deasserted":
            b_assert = (1<<7)

        evd_data = System.BMC_LOGEVENT_CONFIG[s_event_identify]['Event Data Table'][s_event_indicator]

        if (s_evd_desc == ""):
            s_evd_desc = s_event_indicator

        evd_data_info = evd_data['Event Data Information'][s_evd_desc]
        if evd_data_info[0] != None:
            evd1 =evd_data_info[0]
        if evd_data_info[1] != None:
            if isinstance(evd_data_info[1], basestring):
                if evd_data_info[1] in data:
                    evd2 =data[evd_data_info[1]]
            else:
                evd2 =evd_data_info[1]
        if evd_data_info[2] != None:
            if isinstance(evd_data_info[2], basestring):
                if evd_data_info[2] in data:
                    evd3 =data[evd_data_info[2]]
            else:
                evd3 =evd_data_info[2]
    except:
        return False

    bus = get_dbus()
    obj = bus.get_object(DBUS_NAME, objpath, introspect=False)
    intf = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
    sensortype = int(intf.Get(HwmonSensor.IFACE_NAME, 'sensor_type'), 16)
    sensor_number = int(intf.Get(HwmonSensor.IFACE_NAME, 'sensornumber'), 16)
    log = Event(serverity, sensortype, sensor_number, event_dir | b_assert, evd1, evd2, evd3)
    logid=_EVENT_MANAGER.add_log(log)
    if logid == 0:
        return False
    else:
        return True