#!/usr/bin/python -u

import sys
import subprocess32
import gobject
import dbus
import dbus.service
import dbus.mainloop.glib
import os
import time
import obmc.dbuslib.propertycacher as PropertyCacher
from obmc.dbuslib.bindings import DbusProperties, DbusObjectManager, get_dbus
import obmc.enums
import obmc_system_config as System
import traceback

DBUS_NAME = 'org.openbmc.managers.System'
OBJ_NAME = '/org/openbmc/managers/System'
HEARTBEAT_CHECK_INTERVAL = 20000
STATE_START_TIMEOUT = 10
INTF_SENSOR = 'org.openbmc.SensorValue'
INTF_ITEM = 'org.openbmc.InventoryItem'
INTF_CONTROL = 'org.openbmc.Control'


class SystemManager(DbusProperties,DbusObjectManager):
	def __init__(self,bus,obj_name):
		DbusProperties.__init__(self)
		DbusObjectManager.__init__(self)
		dbus.service.Object.__init__(self,bus,obj_name)

		bus.add_signal_receiver(self.NewObjectHandler,
			signal_name = "InterfacesAdded", sender_keyword = 'bus_name')
		bus.add_signal_receiver(self.SystemStateHandler,signal_name = "GotoSystemState")

		self.Set(DBUS_NAME,"current_state","")
		self.system_states = {}
		self.bus_name_lookup = {}
		self.bin_path = os.path.dirname(os.path.realpath(sys.argv[0]))

		for name in System.APPS.keys():
			sys_state = System.APPS[name]['system_state']
			if (self.system_states.has_key(sys_state) == False):
				self.system_states[sys_state] = []
			self.system_states[sys_state].append(name)
	
		## replace symbolic path in ID_LOOKUP
		for category in System.ID_LOOKUP:
			for key in System.ID_LOOKUP[category]:
				val = System.ID_LOOKUP[category][key]
				new_val = val.replace("<inventory_root>",System.INVENTORY_ROOT)
				System.ID_LOOKUP[category][key] = new_val
	
		self.SystemStateHandler(System.SYSTEM_STATES[0])

		if not os.path.exists(PropertyCacher.CACHE_PATH):
			print "Creating cache directory: "+PropertyCacher.CACHE_PATH
   			os.makedirs(PropertyCacher.CACHE_PATH)

		self.InterfacesAdded(obj_name,self.properties)
		print "SystemManager Init Done"


	def SystemStateHandler(self,state_name):
		## clearing object started flags
		current_state = self.Get(DBUS_NAME,"current_state")
		try:
			for obj_path in System.EXIT_STATE_DEPEND[current_state]:
				System.EXIT_STATE_DEPEND[current_state][obj_path] = 0
		except:
			pass

		print "Running System State: "+state_name
		if (self.system_states.has_key(state_name)):
			for name in self.system_states[state_name]:
				self.start_process(name)
		
		if (state_name == "BMC_INIT"):
			## Add poll for heartbeat
	    		gobject.timeout_add(HEARTBEAT_CHECK_INTERVAL, self.heartbeat_check)
		
		try:	
			cb = System.ENTER_STATE_CALLBACK[state_name]
			for methd in cb.keys():
				obj = bus.get_object(cb[methd]['bus_name'],cb[methd]['obj_name'],introspect=False)
				method = obj.get_dbus_method(methd,cb[methd]['interface_name'])
				method()
		except:
			pass

		self.Set(DBUS_NAME,"current_state",state_name)

	def gotoNextState(self):
		s = 0
		current_state = self.Get(DBUS_NAME,"current_state")
		for i in range(len(System.SYSTEM_STATES)):
			if (System.SYSTEM_STATES[i] == current_state):
				s = i+1
	
		if (s == len(System.SYSTEM_STATES)):
			print "ERROR SystemManager: No more system states"
		else:
			new_state_name = System.SYSTEM_STATES[s]
			print "SystemManager Goto System State: "+new_state_name
			self.SystemStateHandler(new_state_name)
	
	
	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='s')
	def getSystemState(self):
		return self.Get(DBUS_NAME,"current_state")

	def doObjectLookup(self,category,key):
		bus_name = ""
		obj_path = ""
		intf_name = INTF_ITEM
		try:
			obj_path = System.ID_LOOKUP[category][key]
			bus_name = self.bus_name_lookup[obj_path]
			parts = obj_path.split('/')
			if (parts[3] == 'sensors'):
				intf_name = INTF_SENSOR
		except Exception as e:
			print "ERROR SystemManager: "+str(e)+" not found in lookup"

		return [bus_name,obj_path,intf_name]

	@dbus.service.method(DBUS_NAME,
		in_signature='ss', out_signature='(sss)')
	def getObjectFromId(self,category,key):
		return self.doObjectLookup(category,key)

	@dbus.service.method(DBUS_NAME,
		in_signature='sy', out_signature='(sss)')
	def getObjectFromByteId(self,category,key):
		byte = int(key)
		return self.doObjectLookup(category,byte)

	@dbus.service.method(DBUS_NAME,
		in_signature='s', out_signature='s')
	def getFanControlParams(self, key):
		if ('FAN_ALGORITHM_CONFIG' not in dir(System) or key == None):
			return ""
		s_params = ""
		try:
			if key == "INVENTORY_FAN":
				for inventory_obj_path in System.FRU_INSTANCES:
					if inventory_obj_path.find("fan") >= 0:
						data = inventory_obj_path.replace("<inventory_root>", System.INVENTORY_ROOT)
						s_params+=data + ";"
				return s_params

			if key.find("FAN_DBUS_INTF_LOOKUP") >= 0:
				key_array = key.split("#")
				if len(key_array) != 2:
					return ""
				key_name = key_array[0]
				key_prefix = key_array[1]
				if key_name not in System.FAN_ALGORITHM_CONFIG:
					return ""
				if key_prefix not in System.FAN_ALGORITHM_CONFIG[key_name]:
					return ""
				for i in range(len(System.FAN_ALGORITHM_CONFIG[key_name][key_prefix])):
					s_params+=System.FAN_ALGORITHM_CONFIG[key_name][key_prefix][i] + ";"
				return s_params

			if key not in System.FAN_ALGORITHM_CONFIG:
				return ""

			for i in range(len(System.FAN_ALGORITHM_CONFIG[key])):
				s_params+=System.FAN_ALGORITHM_CONFIG[key][i] + ";"
		except:
			return ""
		return s_params

	# Get the FRU area names defined in ID_LOOKUP table given a fru_id.
	# If serval areas are defined for a fru_id, the areas are returned
	# together as a string with each area name seperated with ','.
	# If no fru area defined in ID_LOOKUP, an empty string will be returned.
	@dbus.service.method(DBUS_NAME,
		in_signature='y', out_signature='s')
	def getFRUArea(self,fru_id):
		ret_str = ''
		fru_id = '_' + str(fru_id)
		area_list = [area for area in System.ID_LOOKUP['FRU_STR'].keys() \
				if area.endswith(fru_id)]
		for area in area_list:
			ret_str = area + ',' + ret_str
		# remove the last ','
		return ret_str[:-1]

	def start_process(self,name):
		if (System.APPS[name]['start_process'] == True):
			app = System.APPS[name]
			process_name = self.bin_path+"/"+app['process_name']
			cmdline = [ ]
			cmdline.append(process_name)
			if (app.has_key('args')):
				for a in app['args']:
					cmdline.append(a)
			try:
				print "Starting process: "+" ".join(cmdline)+": "+name
				if (app['monitor_process'] == True):
					app['popen'] = subprocess32.Popen(cmdline)
				else:
					subprocess32.Popen(cmdline)
					
			except Exception as e:
				## TODO: error
				print "ERROR: starting process: "+" ".join(cmdline)

	def heartbeat_check(self):
		for name in System.APPS.keys():
			app = System.APPS[name]
			if (app['start_process'] == True and app.has_key('popen')):
				##   make sure process is still alive
				p = app['popen']
				p.poll()
				if (p.returncode != None):
					print "Process for "+name+" appears to be dead"
					self.start_process(name)
	
		return True

	def NewObjectHandler(self, obj_path, iprops, bus_name = None):
		current_state = self.Get(DBUS_NAME,"current_state")
		if (self.bus_name_lookup.has_key(obj_path)):
			if (self.bus_name_lookup[obj_path] == bus_name):
				return
		self.bus_name_lookup[obj_path] = bus_name
		print "New object: "+obj_path+" ("+bus_name+")"
		try:
			if (System.EXIT_STATE_DEPEND[current_state].has_key(obj_path) == True):
				System.EXIT_STATE_DEPEND[current_state][obj_path] = 1
			## check if all required objects are started to move to next state
			state = 1
			for obj_path in System.EXIT_STATE_DEPEND[current_state]:
				if (System.EXIT_STATE_DEPEND[current_state][obj_path] == 0):
					state = 0
			## all required objects have started so go to next state
			if (state == 1):
				print "All required objects started for "+current_state
				self.gotoNextState()
		except:
			pass


	@dbus.service.method(DBUS_NAME,
		in_signature='s', out_signature='siss')
	def gpioInit(self,name):
		gpio_path = ''
		gpio_num = -1
		r = ['',gpio_num,'','']
		if (System.GPIO_CONFIG.has_key(name) == False):
			# TODO: Error handling
			print "ERROR: "+name+" not found in GPIO config table"
		else:
			
			gpio_num = -1
			gpio = System.GPIO_CONFIG[name]
			if (System.GPIO_CONFIG[name].has_key('gpio_num')):
				gpio_num = gpio['gpio_num']
			else:
				if (System.GPIO_CONFIG[name].has_key('gpio_pin')):
					gpio_num = System.convertGpio(gpio['gpio_pin'])
				else:
					print "ERROR: SystemManager - GPIO lookup failed for "+name

				if not (System.GPIO_CONFIG[name].has_key('inverse')):
					print "Inverse:"+name+" not in config table, set inverse to default no"
					System.GPIO_CONFIG[name]['inverse'] = 'no'
					gpio['inverse'] = 'no'
		
			if (gpio_num != -1):
				r = [obmc.enums.GPIO_DEV, gpio_num, gpio['direction'], gpio['inverse']]
		return r

def wait_redfish():
    while True:
        try:
            lines = []
            with open('/proc/net/tcp') as tcp_file:
                lines = tcp_file.readlines()
                lines = lines[1:]
            for line in lines:
                fields = line.strip().split()
                local_address = fields[1]
                _, port = local_address.split(':')
                if int(port, 16) == 443:
                    return
        except StandardError as err:
            traceback.print_exc(err)
        time.sleep(1)

if __name__ == '__main__':
    os.system("ln -s /usr/lib/python2.7/site-packages/subprocess32.py /usr/lib/python2.7/site-packages/subprocess.py")
    wait_redfish()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = get_dbus()
    name = dbus.service.BusName(DBUS_NAME,bus)
    obj = SystemManager(bus,OBJ_NAME)
    mainloop = gobject.MainLoop()

    print "Running SystemManager"
    mainloop.run()

