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
import obmc_system_config as System
import time
import bmclogevent_ctl

import mac_guid

DBUS_NAME = 'org.openbmc.Sensors'
DBUS_INTERFACE = 'org.freedesktop.DBus.Properties'
SENSOR_VALUE_INTERFACE = 'org.openbmc.SensorValue'

g_bmchealth_obj_path = "/org/openbmc/sensors/bmc_health"
g_event_count = [0,0,0,0,0,0,0,0]
g_reboot_flag = 0
g_watchdog_reset = 0
g_previous_log_rollover = -1
g_memory_utilization = -1

#light: 1, light on; 0:light off
def bmchealth_set_status_led(light):
    if 'GPIO_CONFIG' not in dir(System) or 'BLADE_ATT_LED_N' not in System.GPIO_CONFIG:
        return
    try:
        data_reg_addr = System.GPIO_CONFIG["BLADE_ATT_LED_N"]["data_reg_addr"]
        offset = System.GPIO_CONFIG["BLADE_ATT_LED_N"]["offset"]
        inverse = "no"
        if "inverse" in  System.GPIO_CONFIG["BLADE_ATT_LED_N"]:
            inverse = System.GPIO_CONFIG["BLADE_ATT_LED_N"]["inverse"]
        cmd_data = subprocess.check_output("devmem  " + hex(data_reg_addr) , shell=True)
        cmd_data = cmd_data.rstrip("\n")
        cur_data = int(cmd_data, 16)
        if (inverse == "yes"):
            if (light == 1):
                cur_data = cur_data & ~(1<<offset)
            else:
                cur_data = cur_data | (1<<offset)
        else:
            if (light == 1):
                cur_data = cur_data | (1<<offset)
            else:
                cur_data = cur_data & ~(1<<offset)

        set_led_cmd = "devmem  " + hex(data_reg_addr) + " 32 " + hex(cur_data)[:10]
        os.system(set_led_cmd)
    except:
        pass

def LogEventBmcHealthMessages(s_assert="", s_event_indicator="", \
                                         s_evd_desc="", data={}):
    try:
        result = bmclogevent_ctl.BmcLogEventMessages(g_bmchealth_obj_path, "BMC Health", \
                    s_assert,  s_event_indicator, s_evd_desc, data)
        if result['logid'] != 0:
            if s_assert == "Asserted":
                bmclogevent_ctl.bmclogevent_set_value(g_bmchealth_obj_path, 1, offset=(result['evd1']&0xf))
            elif s_assert == "Deasserted":
                bmclogevent_ctl.bmclogevent_set_value(g_bmchealth_obj_path, 0, offset=(result['evd1']&0xf))
    except:
        print "LogEventBmcHealthMessages error!! " + s_event_indicator

def bmchealth_check_status_led():
    try:
        val = bmclogevent_ctl.bmclogevent_get_value_with_dbus(g_bmchealth_obj_path)
        if (val == 0):
            bmchealth_set_status_led(0)
        else:
            bmchealth_set_status_led(1)
    except:
        print "bmchealth_check_status_led Error!!"
    return True

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
            LogEventBmcHealthMessages("Asserted", "Network Error", "DHCP Failure")
    else:
        if g_dhcp_status == 0:
            LogEventBmcHealthMessages("Deasserted", "Network Error", "DHCP Failure")
            time.sleep(60)
        g_dhcp_status = 1

    #check network down
    if carrier == "0" and operstate=="down":
        if g_net_down_status == 1:
            print "bmchealth_check_network:  network down Fail"
            g_net_down_status = 0
            LogEventBmcHealthMessages("Asserted", "Network Error", "Link Down")
    else:
        if g_net_down_status == 0:
            LogEventBmcHealthMessages("Deasserted", "Network Error", "Link Down")
            time.sleep(60)
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
        LogEventBmcHealthMessages("Asserted", "No MAC address programmed")
    return True

def reboot_check_flag():
    reboot_file_path = "/var/lib/obmc/check_reboot"
    global g_reboot_flag
    if os.path.exists(reboot_file_path):
        g_reboot_flag = 1
        os.remove(reboot_file_path)
    return True

def bmchealth_check_watchdog():
    global g_watchdog_reset
    print "check watchdog timeout start"
    check_watchdog1_command = "devmem 0x1e785010"
    check_watchdog2_command = "devmem 0x1e785030"
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
    if g_reboot_flag == 1:
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
        LogEventBmcHealthMessages("Asserted", "Hardware WDT expired")
        g_watchdog_reset = 1
    return True

def bmchealth_check_i2c():
    i2c_recovery_check_path = ["/proc/i2c_recovery_bus0","/proc/i2c_recovery_bus1","/proc/i2c_recovery_bus2","/proc/i2c_recovery_bus3","/proc/i2c_recovery_bus4","/proc/i2c_recovery_bus5","/proc/i2c_recovery_bus6","/proc/i2c_recovery_bus7"]
    global g_event_count

    for num in range(len(i2c_recovery_check_path)):
        if os.path.exists(i2c_recovery_check_path[num]):
            try:
                with open(i2c_recovery_check_path[num], 'r') as f:
                    bus_id = int(f.readline())
                    error_code = int(f.readline(), 16)
                    current_event_count = int(f.readline())
                    state = int(f.readline())
                    if current_event_count > g_event_count[num]:
                        if state == 1:
                            print "Log i2c hang event"
                            LogEventBmcHealthMessages("Asserted", "I2C bus hang", data={'i2c_bus_id':bus_id, 'i2c_error_code':0x1})
                            g_event_count[num] = current_event_count
                        if state == 0:
                            print "Log i2c recovery event"
                            LogEventBmcHealthMessages("Deasserted", "I2C bus hang", data={'i2c_bus_id':bus_id, 'i2c_error_code':0})
                            g_event_count[num] = current_event_count
            except:
                print "[bmchealth_check_i2c]exception !!!"

    return True

def bmchealth_check_fw_update_start():
    fw_update_start_check = "/var/lib/obmc/fw_update_start"
    psu_fw_update_start_check = "/var/lib/obmc/psu_fwupdate_record"
    fpga_fw_update_start_check =  "/var/lib/obmc/fpga_fwupdate_record"
    #check BMC fw update start
    if os.path.exists(fw_update_start_check):
        LogEventBmcHealthMessages("Asserted", "Firmware Update Started","BMC Firmware Update Started",data={'index':0x1})
        os.rename(fw_update_start_check, "/var/lib/obmc/fw_update_complete")
    #check PSU fw update start
    if os.path.exists(psu_fw_update_start_check):
        try:
            with open(psu_fw_update_start_check, 'r') as f:
                psu_id = int(f.readline())
                print"log psu_fwupdate_record psu_id = "+str(psu_id)
                LogEventBmcHealthMessages("Asserted", "Firmware Update Started","PSU Firmware Update Started",data={'index':psu_id})
                os.rename(psu_fw_update_start_check, "/var/lib/obmc/psu_fwupdate_complete")
        except:
                print "[bmchealth_check_fw_updata_complete]exception !!!"
    #check FPGA fw update start
    if os.path.exists(fpga_fw_update_start_check):
        try:
            with open(fpga_fw_update_start_check, 'r') as f:
                fpga_id = int(f.readline())
                print"log fpga_fwupdate_record fpga_id = "+str(fpga_id)
                LogEventBmcHealthMessages("Asserted", "Firmware Update Started","FPGA Firmware Update Started",data={'index':fpga_id})
                os.rename(fpga_fw_update_start_check, "/var/lib/obmc/fpga_fwupdate_complete")
        except:
                print "[bmchealth_check_fw_updata_complete]exception !!!"
    return True

def bmchealth_check_fw_update_complete():
    fw_update_complete_check = "/var/lib/obmc/fw_update_complete"
    psu_fw_update_complete_check = "/var/lib/obmc/psu_fwupdate_complete"
    fpga_fw_update_complete_check =  "/var/lib/obmc/fpga_fwupdate_complete"
    global g_reboot_flag
    #check BMC fw update complete
    if os.path.exists(fw_update_complete_check) and g_reboot_flag == 1:
        os.remove(fw_update_complete_check)
        LogEventBmcHealthMessages("Asserted", "Firmware Update completed","BMC Firmware Update completed",data={'index':0x1})
    #check PSU fw update complete
    if os.path.exists(psu_fw_update_complete_check) and g_reboot_flag == 1:
        try:
            with open(psu_fw_update_complete_check, 'r') as f:
                psu_id = int(f.readline())
                print"log psu_fwupdate_record psu_id = "+str(psu_id)
                LogEventBmcHealthMessages("Asserted", "Firmware Update completed","PSU Firmware Update completed",data={'index':psu_id})
        except:
                print "[bmchealth_check_fw_updata_complete]exception !!!"
        os.remove(psu_fw_update_complete_check)
    #check FPGA fw update complete
    if os.path.exists(fpga_fw_update_complete_check) and g_reboot_flag == 1:
        try:
            with open(fpga_fw_update_complete_check, 'r') as f:
                fpga_id = int(f.readline())
                print"log fpga_fwupdate_record fpga_id = "+str(fpga_id)
                LogEventBmcHealthMessages("Asserted", "Firmware Update completed","FPGA Firmware Update completed",data={'index':fpga_id})
        except:
                print "[bmchealth_check_fw_updata_complete]exception !!!"
        os.remove(fpga_fw_update_complete_check)
    return True

#To skip fwu case, it should be invoked before fw_update_complete removed
def bmchealth_check_bmc_reset():
    fw_update_complete_check = "/var/lib/obmc/fw_update_complete"
    reset_flag_file = '/var/lib/obmc/redfish_reset'
    check_scu3c_command = "devmem 0x1e6e203c 8"
    unlock_scu_command = "devmem 0x1e6e2000 32 0x1688a8a8"
    #lock_scu_command = "devmem 0x1e6e203c 32 0"
    reset_flag = redfish_reset = 0

    print "check system reset control/status register"

    if os.path.exists(reset_flag_file):
        redfish_reset = 1
        os.remove(reset_flag_file)

    try:
        scu3c_str_data = subprocess.check_output(check_scu3c_command, shell=True)
        reset_flag = int(scu3c_str_data, 16) & 0xe
        if g_watchdog_reset == 1:
            reset_flag = reset_flag & 0xc
        if reset_flag != 0:
            if os.path.exists(fw_update_complete_check):
                return True
            subprocess.check_output(unlock_scu_command, shell=True)
            clear_scu3c = "devmem 0x1e6e203c 32 %d" % (int(scu3c_str_data, 16) & 1)
            subprocess.check_output(clear_scu3c, shell=True)
            #subprocess.check_output(lock_scu_command, shell=True)
    except:
        print "[bmchealth_check_bmc_reset] exception!!!"
        return False

    if reset_flag == 0:
        return True;

    if redfish_reset == 1:
        LogEventBmcHealthMessages("Asserted", "BMC Reset", "Redfish Reset")
    else:
        LogEventBmcHealthMessages("Asserted", "BMC Reset", "Register/Pin Reset")
    return True

def bmchealth_check_log_rollover():
    current_log_rollover =  bmclogevent_ctl.bmclogevent_get_log_rollover()
    global g_previous_log_rollover
    if g_previous_log_rollover == -1:
        g_previous_log_rollover =0
    if current_log_rollover > g_previous_log_rollover:
        print "Log Log Rollover event"
        LogEventBmcHealthMessages("Asserted", "Log Rollover","Log Rollover",data={'log_rollover_count':current_log_rollover})
        g_previous_log_rollover = current_log_rollover
    if current_log_rollover == 0 and g_previous_log_rollover != 0:
        bmclogevent_ctl.bmclogevent_set_value("/org/openbmc/sensors/bmc_health", 0, offset=0xb)
        g_previous_log_rollover = current_log_rollover
    return True

def bmchealth_check_memory_utilization():
    meminfo_path = "/proc/meminfo"
    global g_memory_utilization
    if g_memory_utilization == -1:
        g_memory_utilization = 0
    try:
        with open(meminfo_path, 'r') as f:
            line1 = f.readline()
            line2 = f.readline()
            memory_total = float(line1.replace(' ', '').split(':')[1].split('k')[0])
            memory_free = float(line2.replace(' ', '').split(':')[1].split('k')[0])
            memory_used = memory_total - memory_free
            memory_usage = memory_used / memory_total
            memory_utilization = int(memory_usage*100)
            memory_utilization_in_MB = int(memory_used/1000)
            if memory_utilization >= 80 and g_memory_utilization == 0:
                print "Log Asserted memory utilization"
                LogEventBmcHealthMessages("Asserted", "BMC Memory utilization","BMC Memory utilization",data={'memory_utilization':memory_utilization_in_MB})
                g_memory_utilization = 1
            elif memory_utilization < 80 and g_memory_utilization == 1:
                print "Log Deasserted memory utilization"
                LogEventBmcHealthMessages("Deasserted", "BMC Memory utilization","BMC Memory utilization",data={'memory_utilization':memory_utilization_in_MB})
                g_memory_utilization = 0
                time.sleep(60)
    except:
            print "[bmchealth_check_memory_utilization]exception !!!"
    return True

if __name__ == '__main__':
    mainloop = gobject.MainLoop()
    #set bmchealth default value
    bmclogevent_ctl.bmclogevent_set_value(g_bmchealth_obj_path, 0)
    bmchealth_set_status_led(0)
    reboot_check_flag()
    bmchealth_fix_and_check_mac()
    bmchealth_check_watchdog()
    bmchealth_check_bmc_reset() # Before check fwu, after check watchdog
    bmchealth_check_fw_update_complete()
    gobject.timeout_add(1000,bmchealth_check_network)
    gobject.timeout_add(1000,bmchealth_check_fw_update_start)
    gobject.timeout_add(1000,bmchealth_check_i2c)
    gobject.timeout_add(1000,bmchealth_check_status_led)
    gobject.timeout_add(1000,bmchealth_check_log_rollover)
    gobject.timeout_add(1000,bmchealth_check_memory_utilization)
    print "bmchealth_handler control starting"
    mainloop.run()

