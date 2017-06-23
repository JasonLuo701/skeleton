#!/usr/bin/python -u

import sys
import os
import gobject
import glob
import dbus
import dbus.service
import dbus.mainloop.glib
import re
from obmc.dbuslib.bindings import get_dbus
from obmc.events import Event
from obmc.events import EventManager
from obmc.sensors import SensorValue as SensorValue
from obmc.sensors import HwmonSensor as HwmonSensor
from obmc.sensors import SensorThresholds as SensorThresholds
import obmc.sensor_data_record_pool as sdr_tool
import obmc_system_config as System
import bmclogevent_ctl
import traceback

SENSOR_BUS = 'org.openbmc.Sensors'
# sensors include /org/openbmc/sensors and /org/openbmc/control
SENSORS_OBJPATH = '/org/openbmc'
SENSOR_PATH = '/org/openbmc/sensors'
DIR_POLL_INTERVAL = 30000
HWMON_PATH = '/sys/class/hwmon'

## static define which interface each property is under
## need a better way that is not slow
IFACE_LOOKUP = {
	'units' : SensorValue.IFACE_NAME,
	'scale' : HwmonSensor.IFACE_NAME,
	'offset' : HwmonSensor.IFACE_NAME,
	'critical_upper' : SensorThresholds.IFACE_NAME,
	'warning_upper' : SensorThresholds.IFACE_NAME,
	'critical_lower' : SensorThresholds.IFACE_NAME,
	'warning_lower' : SensorThresholds.IFACE_NAME,
	'emergency_enabled' : SensorThresholds.IFACE_NAME,
	'sensornumber': HwmonSensor.IFACE_NAME,
	'sensor_name': HwmonSensor.IFACE_NAME,
	'sensor_type': HwmonSensor.IFACE_NAME,
	'reading_type': HwmonSensor.IFACE_NAME,
	'min_reading': HwmonSensor.IFACE_NAME,
	'max_reading': HwmonSensor.IFACE_NAME,
	'standby_monitor': HwmonSensor.IFACE_NAME,
	'firmware_update': HwmonSensor.IFACE_NAME,
}

# The bit is not supported if not mentioned
PMBUS_STATUS_BYTES = {
	0x8000: 0x01,
	0x4000: 0x01,
	0x2000: 0x01,
	0x0800: 0x04,
	0x0400: 0x01,
	0x40: 0x01,
	0x20: 0x01,
	0x10: 0x01,
	0x08: 0x01,
	0x04: 0x01,
	0x02: 0x01
}

class Hwmons():
	def __init__(self,bus):
		self.sensors = { }
		self.hwmon_root = { }
		self.threshold_state = {}
		self.psu_state = {}
		self.pgood_obj = bus.get_object('org.openbmc.control.Power', '/org/openbmc/control/power0', introspect=False)
		self.pgood_intf = dbus.Interface(self.pgood_obj,dbus.PROPERTIES_IFACE)
		self.path_mapping = {}
		self.event_manager = EventManager()
		self.check_entity_presence = {}
		self.check_subsystem_health = {}
		self.scanDirectory()
		gobject.timeout_add(DIR_POLL_INTERVAL, self.scanDirectory)

	def readAttribute(self,filename):
		val = "-1"
		try:
			with open(filename, 'r') as f:
				for line in f:
					val = line.rstrip('\n')
		except (OSError, IOError):
			if filename != "N/A":
				print "Cannot read attributes:", filename
		return val

	def writeAttribute(self,filename,value):
		with open(filename, 'w') as f:
			f.write(str(value)+'\n')

	def entity_presence_check(self,objpath,hwmon,raw_value):
		entity_presence_obj_path = "/org/openbmc/sensors/entity_presence"
		if objpath not in self.check_entity_presence:
			self.check_entity_presence[objpath] = 1
		if hwmon.has_key('entity'):
			if raw_value == 1 and self.check_entity_presence[objpath] == 1:
				bmclogevent_ctl.BmcLogEventMessages(entity_presence_obj_path, \
						"Entity Presence" ,"Asserted", "Entity Presence" , \
						data={'entity_device':hwmon['entity'], 'entity_index':hwmon['index']})
				bmclogevent_ctl.bmclogevent_set_value(entity_presence_obj_path ,1)
				self.check_entity_presence[objpath] = 0
			elif raw_value == 0:
				if self.check_entity_presence[objpath] == 0:
					bmclogevent_ctl.BmcLogEventMessages(entity_presence_obj_path, \
						"Entity Presence" ,"Deasserted", "Entity Presence" , \
						data={'entity_device':hwmon['entity'], 'entity_index':hwmon['index']})
					bmclogevent_ctl.bmclogevent_set_value(entity_presence_obj_path, 0)
				self.check_entity_presence[objpath] = 1
		return True

	def subsystem_health_check(self,objpath,hwmon,raw_value):
		check_subsystem_health_obj_path = "/org/openbmc/sensors/management_subsystem_health"
		if objpath not in self.check_subsystem_health:
			self.check_subsystem_health[objpath] = 1
		if hwmon.has_key('sensornumber'):
			if raw_value == -1 and self.check_subsystem_health[objpath] == 1:
				bmclogevent_ctl.BmcLogEventMessages(check_subsystem_health_obj_path, \
							"Management Subsystem Health" ,"Asserted", "Management Subsystem Health" , \
							data={'event_status':0xC4, 'sensor_number':hwmon['sensornumber']})
				bmclogevent_ctl.bmclogevent_set_value(check_subsystem_health_obj_path , 1)
				self.check_subsystem_health[objpath] = 0
			elif raw_value >= 0:
				if self.check_subsystem_health[objpath] == 0:
					bmclogevent_ctl.BmcLogEventMessages(check_subsystem_health_obj_path, \
					"Management Subsystem Health" ,"Deasserted", "Management Subsystem Health", \
					data={'event_status':0xC4, 'sensor_number':hwmon['sensornumber']})
					bmclogevent_ctl.bmclogevent_set_value(check_subsystem_health_obj_path, 0)
				self.check_subsystem_health[objpath] = 1
		return True

	def check_pmbus_state(self, objpath, attribute, hwmon):
		try:
			obj = bus.get_object(SENSOR_BUS,objpath,introspect=False)
			intf_p = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
			intf = dbus.Interface(obj,HwmonSensor.IFACE_NAME)
			evd1 = 0xA0
			if 'firmware_update' in hwmon:
				if intf_p.Get(HwmonSensor.IFACE_NAME,'firmware_update') == 1:
					return True
			raw_value = int(self.readAttribute(attribute), 16)
			self.entity_presence_check(objpath,hwmon,raw_value)
			self.subsystem_health_check(objpath,hwmon,raw_value)
			rtn = intf.setByPoll(raw_value)
			if raw_value == -1:
				return True

			if raw_value < 0 or raw_value > 0xFFFF:
				return True
			severity = Event.SEVERITY_OKAY
			event_dir = 0x0
			assertion_failure = False
			deassertion_failure = False
			assertion_power_lost = False
			deassertion_power_lost = False

			for bitmap, event_type in PMBUS_STATUS_BYTES.iteritems():
				if bitmap & (raw_value) & ((self.psu_state[objpath]) ^ 0xFFFF):
					if event_type == 0x04:
						assertion_power_lost = True
					else:
						assertion_failure = True
				elif (not(bitmap & (raw_value)) and (bitmap&self.psu_state[objpath])):
					if event_type == 0x04:
						deassertion_power_lost = True
					else:
						deassertion_failure = True
			if assertion_failure:
				event_dir = 0x0
				severity = Event.SEVERITY_CRIT
				self.LogThresholdEventMessages(objpath, severity, event_dir, hwmon['reading_type'], evd1|0x01, raw_value>>8, raw_value&0xF)
			if assertion_power_lost:
				event_dir = 0x0
				severity = Event.SEVERITY_CRIT
				self.LogThresholdEventMessages(objpath, severity, event_dir, hwmon['reading_type'], evd1|0x04, raw_value>>8, raw_value&0xF)
			if deassertion_failure:
				event_dir = 0x8
				self.LogThresholdEventMessages(objpath, severity, event_dir, hwmon['reading_type'], evd1|0x01, raw_value>>8, raw_value&0xF)
			if deassertion_power_lost:
				event_dir = 0x8
				self.LogThresholdEventMessages(objpath, severity, event_dir, hwmon['reading_type'], evd1|0x04, raw_value>>8, raw_value&0xF)
			self.psu_state[objpath] = raw_value

		except Exception as e:
			print str(e)
		return True

	def poll(self,objpath,attribute,hwmon):
		try:
			standby_monitor = True
			if hwmon.has_key('standby_monitor'):
				standby_monitor = hwmon['standby_monitor']
			# Skip monitor while DC power off if stand by monitor is False
			obj = bus.get_object(SENSOR_BUS,objpath,introspect=False)
			intf_p = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
			intf = dbus.Interface(obj,HwmonSensor.IFACE_NAME)
			if not standby_monitor:
				current_pgood = self.pgood_intf.Get('org.openbmc.control.Power', 'pgood')
				if  current_pgood == 0:
					rtn = intf.setByPoll(-1)
					if (rtn[0] == True):
						self.writeAttribute(attribute,rtn[1])
					return True

			if 'firmware_update' in hwmon:
				if intf_p.Get(HwmonSensor.IFACE_NAME,'firmware_update') == 1:
					return True

			# skip get sensor readings while dc on/off in progress
			dc_on_off = self.pgood_intf.Get('org.openbmc.control.Power', 'dc_on_off')
			if dc_on_off == 1:
				return True
			raw_value = int(self.readAttribute(attribute))
			rtn = intf.setByPoll(raw_value)
			if (rtn[0] == True):
				self.writeAttribute(attribute,rtn[1])

			self.entity_presence_check(objpath,hwmon,raw_value)
			self.subsystem_health_check(objpath,hwmon,raw_value)

			# do not check threshold while not reading
			if raw_value == -1:
				return True
			threshold_state = intf_p.Get(SensorThresholds.IFACE_NAME, 'threshold_state')
			if threshold_state != self.threshold_state[objpath]:
				severity = Event.SEVERITY_INFO
				event_type_code = 0x0
				origin_threshold_type = self.threshold_state[objpath]
				dc_on_off = self.pgood_intf.Get('org.openbmc.control.Power', 'dc_on_off')
				if dc_on_off == 1:
					intf_p.Set(SensorThresholds.IFACE_NAME, 'threshold_state', 'NORMAL')
					return True
				self.threshold_state[objpath]  = threshold_state

				if threshold_state.find("CRITICAL") != -1 or origin_threshold_type.find("CRITICAL") != -1:
					severity = Event.SEVERITY_CRIT
					if threshold_state.find("LOWER") != -1 or origin_threshold_type.find("LOWER") != -1:
						event_type_code = 0x02
						evd3 = intf_p.Get(SensorThresholds.IFACE_NAME,'critical_lower')
					else:
						event_type_code = 0x09
						evd3 = intf_p.Get(SensorThresholds.IFACE_NAME,'critical_upper')
				elif threshold_state.find("WARNING") != -1 or origin_threshold_type.find("WARNING") != -1:
					severity = Event.SEVERITY_WARN
					if threshold_state.find("LOWER") != -1 or origin_threshold_type.find("LOWER") != -1:
						event_type_code = 0x0
						evd3 = intf_p.Get(SensorThresholds.IFACE_NAME,'warning_lower')
					else:
						event_type_code = 0x07
						evd3 = intf_p.Get(SensorThresholds.IFACE_NAME,'warning_upper')
				# [7:6] Trigger reading, [5:4] trigger threshold value, [3:0] Event/Reading code
				scale = intf_p.Get(HwmonSensor.IFACE_NAME,'scale')
				evd1 = (0b0101 << 4)  | event_type_code
				evd2 = raw_value / scale

				sdr = sdr_tool.SDRS.get_by_sensor_number(hwmon['sensornumber'])
				evd2 = sdr.compress_raw_reading(evd2)
				evd3 = sdr.compress_raw_reading(evd3)
				if threshold_state == 'NORMAL':
					severity = Event.SEVERITY_OKAY
					event_dir = 0x80
				else:
					event_dir = 0x0
				self.LogThresholdEventMessages(objpath, severity, event_dir,
										hwmon['reading_type'], evd1, evd2, evd3)
		except:
			print "HWMON: Attibute no longer exists: "+attribute
			self.sensors.pop(objpath,None)
			return False
		return True

	def LogThresholdEventMessages(self, objpath, severity, event_dir, event_type, evd1, evd2=0xFF, evd3=0xFF):

		obj = bus.get_object(SENSOR_BUS, objpath, introspect=False)
		intf = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
		sensortype = int(intf.Get(HwmonSensor.IFACE_NAME, 'sensor_type'), 16)
		sensor_number = intf.Get(HwmonSensor.IFACE_NAME, 'sensornumber')
		sensor_name = intf.Get(HwmonSensor.IFACE_NAME, 'sensor_name')

		# Add event log
		log = Event.from_binary(severity, sensortype, sensor_number, event_dir | event_type, evd1, evd2, evd3)
		self.event_manager.create(log)

		return True

	def addObject(self,dpath,hwmon_path,hwmon):
		objsuf = hwmon['object_path']
		objpath = SENSORS_OBJPATH+'/'+objsuf

		if (self.sensors.has_key(objpath) == False):
			print "HWMON add: "+objpath+" : "+hwmon_path

			## register object with sensor manager
			obj = bus.get_object(SENSOR_BUS,SENSOR_PATH,introspect=False)
			intf = dbus.Interface(obj,SENSOR_BUS)
			intf.register("HwmonSensor",objpath)

			## set some properties in dbus object		
			obj = bus.get_object(SENSOR_BUS,objpath,introspect=False)
			intf = dbus.Interface(obj,dbus.PROPERTIES_IFACE)
			intf.Set(HwmonSensor.IFACE_NAME,'filename',hwmon_path)

			## check if one of thresholds is defined to know
			## whether to enable thresholds or not
			if (hwmon.has_key('critical_upper') or hwmon.has_key('critical_lower')):
				intf.Set(SensorThresholds.IFACE_NAME,'thresholds_enabled',True)

			for prop in hwmon.keys():
				if (IFACE_LOOKUP.has_key(prop)):
					intf.Set(IFACE_LOOKUP[prop],prop,hwmon[prop])
					print "Setting: "+prop+" = "+str(hwmon[prop])

			self.sensors[objpath]=True
			self.hwmon_root[dpath].append(objpath)
			self.threshold_state[objpath] = "NORMAL"

			gobject.timeout_add(hwmon['poll_interval'],self.poll,objpath,hwmon_path,hwmon)

	def addSensorMonitorObject(self):
		if "SENSOR_MONITOR_CONFIG" not in dir(System):
			return

		for i in range(len(System.SENSOR_MONITOR_CONFIG)):
			objpath = System.SENSOR_MONITOR_CONFIG[i][0]
			hwmon = System.SENSOR_MONITOR_CONFIG[i][1]

			if 'device_node' not in hwmon:
				print "Warnning[addSensorMonitorObject]: Not correct set [device_node]"
				continue

			if 'bus_number' in hwmon:
				if hwmon['bus_number'] in self.path_mapping:
					hwmon_path = self.path_mapping[hwmon['bus_number']] + hwmon['device_node']
				else:
					hwmon_path = 'N/A'
			else:
				hwmon_path = hwmon['device_node']
			if (self.sensors.has_key(objpath) == False):
				## register object with sensor manager
				obj = bus.get_object(SENSOR_BUS,SENSOR_PATH,introspect=False)
				intf = dbus.Interface(obj,SENSOR_BUS)
				intf.register("HwmonSensor",objpath)

				## set some properties in dbus object
				obj = bus.get_object(SENSOR_BUS,objpath,introspect=False)
				intf = dbus.Interface(obj,dbus.PROPERTIES_IFACE)
				intf.Set(HwmonSensor.IFACE_NAME,'filename',hwmon_path)
				# init value as
				val = -1
				if hwmon.has_key('value'):
					val = hwmon['value']
					intf_h = dbus.Interface(obj,HwmonSensor.IFACE_NAME)
					intf_h.setByPoll(val)

				## check if one of thresholds is defined to know
				## whether to enable thresholds or not
				if (hwmon.has_key('critical_upper') or hwmon.has_key('critical_lower')):
					intf.Set(SensorThresholds.IFACE_NAME,'thresholds_enabled',True)

				for prop in hwmon.keys():
					if (IFACE_LOOKUP.has_key(prop)):
						intf.Set(IFACE_LOOKUP[prop],prop,hwmon[prop])

				self.sensors[objpath]=True
				self.threshold_state[objpath] = "NORMAL"
				if 'sensornumber' in hwmon and hwmon['sensornumber'] >= 0x83 and hwmon['sensornumber'] <= 0x88:
					self.psu_state[objpath] = 0x0
					gobject.timeout_add(hwmon['poll_interval'],self.check_pmbus_state,objpath, hwmon_path, hwmon)
				else:
					if hwmon.has_key('poll_interval'):
						gobject.timeout_add(hwmon['poll_interval'],self.poll,objpath,hwmon_path,hwmon)

	def scanDirectory(self):
		check_subsystem_health_obj_path = "/org/openbmc/sensors/management_subsystem_health"
	 	devices = os.listdir(HWMON_PATH)
		found_hwmon = {}
		regx = re.compile('([a-z]+)\d+\_')
		self.path_mapping = {}
		obj_mapping = []
		for d in devices:
			dpath = HWMON_PATH+'/'+d+'/'
			found_hwmon[dpath] = True
			if (self.hwmon_root.has_key(dpath) == False):
				self.hwmon_root[dpath] = []
			## the instance name is a soft link
			instance_name = os.path.realpath(dpath+'device').split('/').pop()
			self.path_mapping[instance_name] = dpath
			if (System.HWMON_CONFIG.has_key(instance_name)):
				hwmon = System.HWMON_CONFIG[instance_name]
				if (hwmon.has_key('labels')):
					label_files = glob.glob(dpath+'/*_label')
					for f in label_files:
						label_key = self.readAttribute(f)
						if (hwmon['labels'].has_key(label_key)):
							namef = f.replace('_label','_input')
							self.addObject(dpath,namef,hwmon['labels'][label_key])
						else:
							pass
							#print "WARNING - hwmon: label ("+label_key+") not found in lookup: "+f

				if hwmon.has_key('names'):
					for attribute in hwmon['names'].keys():
						obj_mapping.append(hwmon['names'][attribute]['object_path'])
						self.addObject(dpath,dpath+attribute,hwmon['names'][attribute])

			else:
				print "WARNING - hwmon: Unhandled hwmon: "+dpath
		for dpath in System.HWMON_CONFIG:
			for attribute in System.HWMON_CONFIG[dpath]['names']:
				objpath = System.HWMON_CONFIG[dpath]['names'][attribute]['object_path']
				if objpath not in self.check_subsystem_health:
					self.check_subsystem_health[objpath] = 1
				if System.HWMON_CONFIG[dpath]['names'][attribute]['object_path'] not in obj_mapping:
					if self.check_subsystem_health[objpath] == 1:
						bmclogevent_ctl.BmcLogEventMessages(check_subsystem_health_obj_path, \
						"Management Subsystem Health" ,"Asserted", "Management Subsystem Health", \
						data={'event_status':0x4, 'sensor_number':System.HWMON_CONFIG[dpath]['names'][attribute]['sensornumber']})
						bmclogevent_ctl.bmclogevent_set_value(check_subsystem_health_obj_path, 1)
						self.check_subsystem_health[objpath] = 0

		self.addSensorMonitorObject()
		for k in self.hwmon_root.keys():
			if (found_hwmon.has_key(k) == False):
				## need to remove all objects associated with this path
				print "Removing: "+k
				for objpath in self.hwmon_root[k]:
					if (self.sensors.has_key(objpath) == True):
						print "HWMON remove: "+objpath
						self.sensors.pop(objpath,None)
						obj = bus.get_object(SENSOR_BUS,SENSOR_PATH,introspect=False)
						intf = dbus.Interface(obj,SENSOR_BUS)
						intf.delete(objpath)

				self.hwmon_root.pop(k,None)

		return True


if __name__ == '__main__':

	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	bus = get_dbus()
	root_sensor = Hwmons(bus)
	mainloop = gobject.MainLoop()

	print "Starting HWMON sensors"
	mainloop.run()

