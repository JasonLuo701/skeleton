#!/usr/bin/python -u

import os
import sys
import gobject
import subprocess
import dbus
import dbus.service
import dbus.mainloop.glib
import obmc.dbuslib.propertycacher as PropertyCacher
from obmc.dbuslib.bindings import get_dbus, DbusProperties, DbusObjectManager
from obmc.sensors import HwmonSensor as HwmonSensor
from obmc.sensors import SensorThresholds as SensorThresholds
from obmc.events import EventManager, Event
import obmc_system_config as System
import time

import mac_guid

DBUS_NAME = 'org.openbmc.Sensors'
DBUS_INTERFACE = 'org.freedesktop.DBus.Properties'
SENSOR_VALUE_INTERFACE = 'org.openbmc.SensorValue'

g_bmchealth_obj_path = "/org/openbmc/sensors/bmc_health"
g_recovery_count = 0

_EVENT_MANAGER = EventManager()

def LogEventBmcHealthMessages(event_dir, evd1, evd2, evd3):
    bus = get_dbus()
    objpath = g_bmchealth_obj_path
    obj = bus.get_object(DBUS_NAME, objpath, introspect=False)
    intf = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
    sensortype = int(intf.Get(HwmonSensor.IFACE_NAME, 'sensor_type'), 16)
    sensor_number = int(intf.Get(HwmonSensor.IFACE_NAME, 'sensornumber'), 16)
    sensor_name = objpath.split('/').pop()

    logid = 0
    if 'LOG_EVENT_CONFIG' in dir(System):
        for log_item in System.LOG_EVENT_CONFIG:
            if (log_item['EVD1'] == None or log_item['EVD1'] == evd1) and \
               (log_item['EVD2'] == None or log_item['EVD2'] == evd2) and \
               (log_item['EVD3'] == None or log_item['EVD3'] == evd3):

                #prepare to send log event:
                #create & init new event class
                log = Event(Event.SEVERITY_INFO, sensortype, sensor_number)
                #add new event log
                logid=_EVENT_MANAGER.add_log(log)
                break

    if logid == 0:
        return False
    else:
        return True

def bmchealth_set_value_with_dbus(val):
    try:
        b_bus = get_dbus()
        b_obj= b_bus.get_object(DBUS_NAME, g_bmchealth_obj_path)
        b_interface = dbus.Interface(b_obj,  DBUS_INTERFACE)
        b_interface.Set(SENSOR_VALUE_INTERFACE, 'value', val)
    except:
        print "bmchealth_set_value Error!!!"
        return -1
    return 0

def bmchealth_set_value(val):
    retry = 20
    while(bmchealth_set_value_with_dbus(val)!=0):
        if (retry <=0):
            return -1
        time.sleep(1)
    return 0

def bmchealth_check_network():
    carrier_file_path = "/sys/class/net/eth0/carrier"
    operstate_file_path = "/sys/class/net/eth0/operstate"
    check_ipaddr_command ="ifconfig eth0"
    check_ipaddr_keywords = "inet addr"
    record_dhcp_file_path = "/tmp/bmchealth_record_dhcp_status.txt"
    record_down_file_path = "/tmp/bmchealth_record_down_status.txt"

    carrier = ""    #0 or 1
    operstate = ""  #up or down
    ipaddr = ""

    g_dhcp_status = 1
    g_net_down_status = 1

    try:
        with open(record_dhcp_file_path, 'r') as f:
            for line in f:
                g_dhcp_status = int(line.rstrip('\n'))
    except:
        pass
    try:
        with open(record_down_file_path, 'r') as f:
            for line in f:
                g_net_down_status = int(line.rstrip('\n'))
    except:
        pass

    org_dhcp_status = g_dhcp_status
    org_down_status = g_net_down_status
    try:
        cmd_data = subprocess.check_output(check_ipaddr_command, shell=True)
        if cmd_data.find(check_ipaddr_keywords) >=0:
            ipaddr = "1"
        else:
            ipaddr = "0"
    except:
        print "[bmchealth_check_network]Error conduct operstate!!!"
        return False

    try:
        with open(carrier_file_path, 'r') as f:
            for line in f:
                carrier = line.rstrip('\n')
    except:
        print "[bmchealth_check_network]Error conduct carrier!!!"
        return False

    try:
        with open(operstate_file_path, 'r') as f:
            for line in f:
                operstate = line.rstrip('\n')
    except:
        print "[bmchealth_check_network]Error conduct operstate!!!"
        return False

    #check dhcp fail status
    if ipaddr == "0" and carrier == "1" and operstate == "up":
        if g_dhcp_status == 1:
            print "bmchealth_check_network:  DHCP Fail"
            g_dhcp_status = 0
            bmchealth_set_value(0x1)
            LogEventBmcHealthMessages("Asserted", 0x1, 0x2, None )
    else:
        g_dhcp_status = 1

    #check network down
    if carrier == "0" and operstate=="down":
        if g_net_down_status == 1:
            print "bmchealth_check_network:  network down Fail"
            g_net_down_status = 0
            bmchealth_set_value(0x1)
            LogEventBmcHealthMessages("Asserted", 0x1, 0x1, None )
    else:
        g_net_down_status = 1

    if org_dhcp_status != g_dhcp_status:
        with open(record_dhcp_file_path, 'w') as f:
            f.write(str(g_dhcp_status))
    if org_down_status != g_net_down_status:
        with open(record_down_file_path, 'w') as f:
            f.write(str(g_net_down_status))
    return True

def bmchealth_fix_and_check_mac():
    print "fix-mac & fix-guid start"
    fix_mac_status = mac_guid.fixMAC()
    fix_guid_status = mac_guid.fixGUID()

    print "bmchealth: check mac status:" + str(fix_mac_status)
    print "bmchealth: check guid status:" + str(fix_guid_status)
    #check bmchealth macaddress
    ret = 0
    if fix_mac_status == 0 or fix_guid_status == 0:
        ret = bmchealth_set_value(0xC)
        LogEventBmcHealthMessages("Asserted", 0xC, None, None )
    print "bmchealth: bmchealth_fix_and_check_mac : " + str(ret)
    return ret

def bmchealth_check_watchdog():
    print "check watchdog timeout start"
    check_watchdog1_command = "devmem 0x1e785010"
    check_watchdog2_command = "devmem 0x1e785030"
    reboot_file_path = "/var/lib/obmc/check_reboot"
    watchdog1_event_counter_path = "/var/lib/obmc/watchdog1"
    watchdog2_event_counter_path = "/var/lib/obmc/watchdog2"
    watchdog1_exist_counter = 0
    watchdog2_exist_counter = 0

    #read event counters
    try:
        watchdog1_str_data = subprocess.check_output(check_watchdog1_command, shell=True)
        watchdog1_timeout_counter = (  int(watchdog1_str_data, 16) >> 8) & 0xff
    except:
        print "[bmchealth_check_watchdog]Error conduct operstate!!!"
        return False

    try:
        watchdog2_str_data = subprocess.check_output(check_watchdog2_command, shell=True)
        watchdog2_timeout_counter = ( int(watchdog2_str_data, 16) >> 8) & 0xff
    except:
        print "[bmchealth_check_watchdog]Error conduct operstate!!!"
        return False

    #check reboot timeout or WDT timeout
    if os.path.exists(reboot_file_path):
            os.remove(reboot_file_path)
            f = file(watchdog1_event_counter_path,"w")
            f.write(str(watchdog1_timeout_counter))
            f.close()
            f = file(watchdog2_event_counter_path,"w")
            f.write(str(watchdog2_timeout_counter))
            f.close()
            return True
    else:
        try:
            with open(watchdog1_event_counter_path, 'r') as f:
                for line in f:
                    watchdog1_exist_counter = int(line.rstrip('\n'))
        except:
            pass

        try:
            with open(watchdog2_event_counter_path, 'r') as f:
                for line in f:
                    watchdog2_exist_counter = int(line.rstrip('\n'))
        except:
            pass

    if watchdog1_timeout_counter > watchdog1_exist_counter or watchdog2_timeout_counter > watchdog2_exist_counter:
        f = file(watchdog1_event_counter_path,"w")
        f.write(str(watchdog1_timeout_counter))
        f.close()
        f = file(watchdog2_event_counter_path,"w")
        f.write(str(watchdog2_timeout_counter))
        f.close()
        print "Log watchdog expired event"
        bmchealth_set_value(0x3)
        LogEventBmcHealthMessages("Asserted", 0x3, None, None )
    return True

def bmchealth_check_i2c():
    i2c_recovery_check_path = "/proc/i2c_recovery"
    global g_recovery_count

    if os.path.exists(i2c_recovery_check_path):
        try:
            with open(i2c_recovery_check_path, 'r') as f:
                bus_id = int(f.readline())
                error_code = int(f.readline(), 16)
                current_recovery_count = int(f.readline())
                if current_recovery_count > g_recovery_count:
                    print "Log i2c recovery event"
                    bmchealth_set_value(0xA)
                    LogEventBmcHealthMessages("Asserted", 0xA, bus_id, error_code )
                    g_recovery_count = current_recovery_count
                else:
                    return True
        except:
            print "[bmchealth_check_i2c]exception !!!"
            return True
    else:
        return True
    return True

if __name__ == '__main__':
    mainloop = gobject.MainLoop()
    #set bmchealth default value
    bmchealth_set_value(0)
    bmchealth_fix_and_check_mac()
    bmchealth_check_watchdog()
    gobject.timeout_add(1000,bmchealth_check_network)
    gobject.timeout_add(1000,bmchealth_check_i2c)
    print "bmchealth_handler control starting"
    mainloop.run()

