# -*- coding: utf-8 -*-

# pylint: disable=attribute-defined-outside-init
# pylint: disable=missing-docstring

from os.path import join
from glob import glob

HOME_PATH = './'
CACHE_PATH = '/var/cache/obmc/'
FLASH_DOWNLOAD_PATH = "/tmp"
GPIO_BASE = 320
SYSTEM_NAME = "G50"

def find_gpio_base(path="/sys/class/gpio/"):
    pattern = "gpiochip*"
    for gpiochip in glob(join(path, pattern)):
        with open(join(gpiochip, "label")) as chipfile:
            label = chipfile.readline().strip()
        if label == "1e780000.gpio":
            with open(join(gpiochip, "base")) as chipfile:
                return int(chipfile.readline().strip())
    # trigger a file not found exception
    open(join(path, "gpiochip"))

GPIO_BASE = find_gpio_base()

## System states
##   state can change to next state in 2 ways:
##   - a process emits a GotoSystemState signal with state name to goto
##   - objects specified in EXIT_STATE_DEPEND have started
SYSTEM_STATES = [
    'BASE_APPS',
    'BMC_STARTING',
    'BMC_STARTING2',
    'BMC_READY',
    'HOST_POWERING_ON',
    'HOST_POWERED_ON',
    'HOST_BOOTING',
    'HOST_BOOTED',
    'HOST_POWERED_OFF',
]

EXIT_STATE_DEPEND = {
    'BASE_APPS' : {
        '/org/openbmc/sensors': 0,
    },
    'BMC_STARTING' : {
        '/org/openbmc/inventory/system/chassis/io_board' : 0,
    },
    'BMC_STARTING2' : {
        '/org/openbmc/control/chassis0': 0,
    },
}

## method will be called when state is entered
ENTER_STATE_CALLBACK = {
    'BMC_READY' : {
        'setBlinkSlow' : {
            'bus_name'   : 'org.openbmc.control.led',
            'obj_name'   : '/org/openbmc/control/led/heartbeat',
            'interface_name' : 'org.openbmc.Led',
        },
    }
}

APPS = {
    'startup_hacks' : {
        'system_state'    : 'BASE_APPS',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'startup_hacks.sh',
    },
    'inventory' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'inventory_items.py',
        'args'            : [SYSTEM_NAME]
    },
    'fan_control' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'fan_control.py',
    },
    'hwmon' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'hwmon.py',
        'args'            : [SYSTEM_NAME]
    },
    'sensor_manager' : {
        'system_state'    : 'BASE_APPS',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'sensor_manager2.py',
        'args'            : [SYSTEM_NAME]
    },
    'host_watchdog' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'host_watchdog.exe',
    },
    'power_control' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name' : 'power_control_sthelens.exe',
        'args' : ['3000', '10']
    },
    'power_button' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'button_power.exe',
    },
    'led_control' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'led_controller.exe',
    },
    'bmc_flash_control' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'bmc_update.py',
    },
    'download_manager' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'download_manager.py',
        'args'            : [SYSTEM_NAME]
    },
    'chassis_control' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'chassis_control.py',
    },
    'board_vpd' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'phosphor-read-eeprom',
        'args'            : [
            '--eeprom', '/sys/bus/i2c/devices/0-0050/eeprom', '--fruid', '64'],
    },
    'motherboard_vpd' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'phosphor-read-eeprom',
        'args'            : [
            '--eeprom', '/sys/bus/i2c/devices/4-0054/eeprom', '--fruid', '3'],
    },
    'exp_vpd' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'phosphor-read-eeprom',
        'args'            : [
            '--eeprom', '/sys/bus/i2c/devices/6-0051/eeprom', '--fruid', '65'],
    },
    'hdd_vpd' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'phosphor-read-eeprom',
        'args'            : [
            '--eeprom', '/sys/bus/i2c/devices/6-0055/eeprom', '--fruid', '66'],
    },
    'restore' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'discover_system_state.py',
    },
    'fan_algorithm' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'fan_algorithm.exe',
    },
    'bmc_control' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'control_bmc.exe',
    },
    'id_button' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'button_id.exe',
    },
    'cable_led' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'cable_led.exe',
    },
    'netman' : {
        'system_state'    : 'BMC_STARTING2',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'netman.py',
    },
    'sync_mac' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'sync_inventory_items.py',
        'args'            : [
            '-t', 'DAUGHTER_CARD', '-n', 'io_board', '-p', 'Custom Field 2',
            '-s', 'mac'],
    },
    'fan_ctl' : {
        'system_state'    : 'BMC_STARTING',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'fan_generic_obj.exe',
    },
    'gpu_core' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'gpu_core.exe',
    },
    'node_init_sthelens' : {
        'system_state'    : 'BASE_APPS',
        'start_process'   : True,
        'monitor_process' : False,
        'process_name'    : 'node_init_sthelens.exe',
    },
    'bmchealth_service' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'bmchealth_handler.py',
    },
    'pex_service' : {
        'system_state'    : 'BMC_READY',
        'start_process'   : True,
        'monitor_process' : True,
        'process_name'    : 'pex_core.exe',
    },
}

CACHED_INTERFACES = {
    "org.openbmc.InventoryItem" : True,
    "org.openbmc.control.Chassis" : True,
}
INVENTORY_ROOT = '/org/openbmc/inventory'

FRU_INSTANCES = {
    '<inventory_root>/system' : {
        'fru_type' : 'SYSTEM',
        'is_fru' : True,
        'present' : "True"
        },
    '<inventory_root>/system/misc' : {
        'fru_type' : 'SYSTEM',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis' : {
        'fru_type' : 'SYSTEM',
        'is_fru' : True,
        'present' : "True"
        },
    '<inventory_root>/system/chassis/motherboard' : {
        'fru_type' : 'MAIN_PLANAR',
        'is_fru' : True,
        },
    '<inventory_root>/system/systemevent'                  : {
        'fru_type' : 'SYSTEM_EVENT',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis/motherboard/refclock' : {
        'fru_type' : 'MAIN_PLANAR',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis/motherboard/pcieclock': {
        'fru_type' : 'MAIN_PLANAR',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis/motherboard/todclock' : {
        'fru_type' : 'MAIN_PLANAR',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis/motherboard/apss'     : {
        'fru_type' : 'MAIN_PLANAR',
        'is_fru' : False,
        },
    '<inventory_root>/system/chassis/motherboard/bmc' : {
        'fru_type' : 'BMC',
        'is_fru' : False,
        'manufacturer' : 'ASPEED'
        },
    '<inventory_root>/system/chassis/io_board' : {
        'fru_type' : 'DAUGHTER_CARD',
        'is_fru' : True,
        'Custom Field 2': '00:00:00:00:00:00',
        },
}

ID_LOOKUP = {
    'FRU' : {
        0x40 : '<inventory_root>/system/chassis/io_board',
    },
    'FRU_STR' : {
        'BOARD_100'  : '<inventory_root>/system/chassis/io_board',
    },
    'SENSOR' : {
    },
    'GPIO_PRESENT' : {
    }
}

GPIO_CONFIG = {}
GPIO_CONFIG['POWER_BUTTON'] = {'gpio_pin': 'F1', 'direction': 'both'}
GPIO_CONFIG['IDBTN'] = {'gpio_pin': 'F3', 'direction': 'both'}
GPIO_CONFIG['PGOOD'] = {'gpio_pin': 'M2', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['POWER_PIN'] = {'gpio_pin': 'M3', 'direction': 'out'}
GPIO_CONFIG['POWER_STATE_LED'] = {
    'gpio_pin': 'F2',
    'direction': 'out',
    'inverse': 'yes'
    }

def convertGpio(name):
    offset = int(filter(str.isdigit, name))
    port = filter(str.isalpha, name.upper())
    port_num = ord(port[-1]) - ord('A')
    if len(port) > 1:
        port_num += 26
    base = port_num * 8 + GPIO_BASE
    return base + offset

def _add_gpu_temperature_sensor(configs, index, sensornumber):
    config = ['/org/openbmc/sensors/gpu/gpu%d_temp' % index, {
        'critical_upper': 81,
        'device_node': '/tmp/gpu/gpu%d_temp' % index,
        'object_path': 'sensors/gpu/gpu%d_temp' % index,
        'poll_interval': 5000,
        'reading_type': '0x01',
        'scale': 1,
        'sensor_name': 'GPU%d Temp' % index,
        'sensor_type': '0x01',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'C',
        }]
    configs.append(config)

def _add_fan_pwm_sensor(configs, index, sensornumber):
    config = ['/org/openbmc/control/fan/pwm%d' % index, {
        'device_node':
            '/sys/devices/platform/ast_pwm_tacho.0/pwm%d_falling' % index,
        'object_path': 'control/fan/pwm%d' % index,
        'poll_interval': 10000,
        'reading_type': '0x01',
        'scale': 1,
        'sensor_name': 'PWM %d' % index,
        'sensor_type': '0x04',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': '%',
        'value': 0,
        }]
    configs.append(config)

def _add_fan_tach_sensor(configs, index, sensornumber):
    config = ['/org/openbmc/sensors/fan/fan_tacho%d' % index, {
        'critical_lower': 3800,
        'device_node':
            '/sys/devices/platform/ast_pwm_tacho.0/tacho%d_rpm' % index,
        'object_path': 'sensors/fan/fan_tacho%d' % index,
        'poll_interval': 10000,
        'reading_type': '0x01',
        'scale': 1,
        'sensor_name': 'Fan Tach %d' % index,
        'sensor_type': '0x04',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'rpm',
        'value': -1,
        }]
    configs.append(config)

def _add_psu_temperature_sensor(configs, index, sensornumber, bus_number):
    config = ['/org/openbmc/sensors/pmbus/pmbus0%d/temp_02' % index, {
        'bus_number': bus_number,
        'critical_upper': 95,
        'device_node': 'temp2_input',
        'object_path': 'sensors/pmbus/pmbus0%d/temp_02' % index,
        'poll_interval': 10000,
        'reading_type': '0x01',
        'scale': 1000,
        'sensor_name': 'PSU%d Temp 2' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'units': 'C',
        'value': 0,
        }]
    configs.append(config)

def _add_psu_voltage_sensor(configs, index, sensornumber, bus_number):
    config = ['/org/openbmc/sensors/pmbus/pmbus0%d/Voltage_vout' % index, {
        'bus_number': bus_number,
        'critical_lower': 10.5,
        'critical_upper': 14.25,
        'device_node': 'in2_input',
        'max_reading': '20',
        'min_reading': '0',
        'object_path': 'sensors/pmbus/pmbus0%d/Voltage_vout' % index,
        'poll_interval': 10000,
        'reading_type': '0x01',
        'scale': 1000,
        'sensor_name': 'PSU%d Voltage Output' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'units': 'V',
        'value': 0,
        }]
    configs.append(config)

def _add_psu_power_sensor(configs, index, sensornumber, bus_number):
    config = ['/org/openbmc/sensors/pmbus/pmbus0%d/Power_pout' % index, {
        'bus_number': bus_number,
        'critical_upper': 1760,
        'device_node': 'power2_input',
        'object_path': 'sensors/pmbus/pmbus0%d/Power_pout' % index,
        'poll_interval': 10000,
        'reading_type': '0x01',
        'scale': 1000000,
        'sensor_name': 'PSU%d Power Output' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'units': 'W',
        'value': 0,
        }]
    configs.append(config)

def _add_cable_led(configs, index, gpio):
    config = ['/org/openbmc/control/cable_led/led%d' % index, {
        'device_node': '/sys/class/gpio/gpio%d/value' % gpio,
        'object_path': 'control/cable_led/led%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': True,
        'units': '',
        }]
    configs.append(config)

def _add_pex9797(configs, index):
    config = ['/org/openbmc/sensors/pex/pex%d' % index, {
        'device_node': '/tmp/pex/pex%d_temp' % index,
        'object_path': 'sensors/pex/pex%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': False,
        'units': '',
        }]
    configs.append(config)

def _add_bmc_health_sensor(configs, sensornumber):
    config = ['/org/openbmc/sensors/bmc_health', {
        'device_node': '',
        'object_path': 'sensors/bmc_health',
        'reading_type': '0x70',
        'sensor_name': 'BMC Health',
        'sensor_type': '0x28',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'value': 0,
        }]
    configs.append(config)

SENSOR_MONITOR_CONFIG = []
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 1, '0x41')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 2, '0x42')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 3, '0x43')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 4, '0x44')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 5, '0x45')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 6, '0x46')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 7, '0x47')
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 8, '0x48')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 1, '0x1D')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 2, '0x1E')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 3, '0x1F')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 4, '0x20')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 5, '0x21')
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 6, '0x22')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 1, '0x11')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 2, '0x12')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 3, '0x13')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 4, '0x14')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 5, '0x15')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 6, '0x16')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 7, '0x17')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 8, '0x18')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 9, '0x19')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 10, '0x1A')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 11, '0x1B')
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 12, '0x1C')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 1, '0x52', '8-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 1, '0x51', '8-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 1, '0x50', '8-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 2, '0x55', '9-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 2, '0x54', '9-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 2, '0x53', '9-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 3, '0x58', '10-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 3, '0x57', '10-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 3, '0x56', '10-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 4, '0x5B', '11-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 4, '0x5A', '11-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 4, '0x59', '11-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 5, '0x5E', '12-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 5, '0x5D', '12-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 5, '0x5C', '12-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 6, '0x61', '13-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 6, '0x60', '13-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 6, '0x5F', '13-0058')
_add_cable_led(SENSOR_MONITOR_CONFIG, 0, 234)
_add_cable_led(SENSOR_MONITOR_CONFIG, 1, 235)
_add_cable_led(SENSOR_MONITOR_CONFIG, 2, 242)
_add_cable_led(SENSOR_MONITOR_CONFIG, 3, 243)
_add_cable_led(SENSOR_MONITOR_CONFIG, 4, 250)
_add_cable_led(SENSOR_MONITOR_CONFIG, 5, 251)
_add_cable_led(SENSOR_MONITOR_CONFIG, 6, 258)
_add_cable_led(SENSOR_MONITOR_CONFIG, 7, 259)
_add_cable_led(SENSOR_MONITOR_CONFIG, 8, 266)
_add_cable_led(SENSOR_MONITOR_CONFIG, 9, 267)
_add_cable_led(SENSOR_MONITOR_CONFIG, 10, 274)
_add_cable_led(SENSOR_MONITOR_CONFIG, 11, 275)
_add_cable_led(SENSOR_MONITOR_CONFIG, 12, 282)
_add_cable_led(SENSOR_MONITOR_CONFIG, 13, 283)
_add_cable_led(SENSOR_MONITOR_CONFIG, 14, 290)
_add_cable_led(SENSOR_MONITOR_CONFIG, 15, 291)
_add_pex9797(SENSOR_MONITOR_CONFIG, 0)
_add_pex9797(SENSOR_MONITOR_CONFIG, 1)
_add_pex9797(SENSOR_MONITOR_CONFIG, 2)
_add_pex9797(SENSOR_MONITOR_CONFIG, 3)
_add_bmc_health_sensor(SENSOR_MONITOR_CONFIG, '0x82')

HWMON_CONFIG = {
    '0-0010' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC1_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x23',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC1 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC1_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x24',
                'critical_upper':125,
                'sensor_name':'HSC1 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0011' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC2_STBY_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x25',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC2 STBY VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': True,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC2_STBY_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x26',
                'critical_upper':125,
                'sensor_name':'HSC2 STBY Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': True,
                },
        }
    },
    '0-0040' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC3_GPU1_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x27',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC3 GPU1 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC3_GPU1_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x28',
                'critical_upper':125,
                'sensor_name':'HSC3 GPU1 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0041' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC4_GPU2_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x29',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC4 GPU2 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC4_GPU2_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x2A',
                'critical_upper':125,
                'sensor_name':'HSC4 GPU2 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0042' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC5_GPU3_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x2B',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC5 GPU3 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC5_GPU3_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x2C',
                'critical_upper':125,
                'sensor_name':'HSC5 GPU3 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0043' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC6_GPU4_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x2D',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC6 GPU4 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC6_GPU4_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x2E',
                'critical_upper':125,
                'sensor_name':'HSC6 GPU4 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0044' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC7_GPU5_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x2F',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC7 GPU5 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC7_GPU5_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x30',
                'critical_upper':125,
                'sensor_name':'HSC7 GPU5 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0045' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC8_GPU6_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x31',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC8 GPU6 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC8_GPU6_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x32',
                'critical_upper':125,
                'sensor_name':'HSC8 GPU6 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0046' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC9_GPU7_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x33',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC9 GPU7 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC9_GPU7_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x34',
                'critical_upper':125,
                'sensor_name':'HSC9 GPU7 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '0-0047' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC10_GPU8_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : '0x35',
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC10 GPU8 VOUT',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
            'temp1_input' : {
                'object_path' : 'sensors/HSC/HSC10_GPU8_TMP',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x36',
                'critical_upper':125,
                'sensor_name':'HSC10 GPU8 Temp',
                'reading_type' : '0x01',
                'emergency_enabled' : False,
                'min_reading':'0',
                'max_reading':'20',
                'standby_monitor': False,
                },
        }
    },
    '21-0048' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP1',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '',
                'sensor_name':'',
                'reading_type' : '0x01',
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-0049' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP2',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '',
                'sensor_name':'',
                'reading_type' : '0x01',
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-004a' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP3',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '',
                'sensor_name':'',
                'reading_type' : '0x01',
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-004b' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP4',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '',
                'sensor_name':'',
                'reading_type' : '0x01',
                'emergency_enabled' : True,
                'offset':-7,
                'standby_monitor': True,
                }, #Thermal team suggest temp4 (-7) offset
        }
    },
    '21-004c' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP5',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x01',
                'sensor_name':'Inlet Temp 5',
                'reading_type' : '0x01',
                'critical_upper' : 37,
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-004d' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP6',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x02',
                'sensor_name':'Inlet Temp 6',
                'reading_type' : '0x01',
                'critical_upper' : 37,
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-004e' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP7',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x03',
                'sensor_name':'Inlet Temp 7',
                'reading_type' : '0x01',
                'critical_upper' : 37,
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
    '21-004f' :  {
        'names' : {
            'temp1_input' : {
                'object_path' : 'sensors/temperature/TMP8',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'C',
                'sensor_type' : '0x01',
                'sensornumber' : '0x04',
                'sensor_name':'Inlet Temp 8',
                'reading_type' : '0x01',
                'critical_upper' : 37,
                'emergency_enabled' : True,
                'standby_monitor': True,
                },
        }
    },
}

# Miscellaneous non-poll sensor with system specific properties.
# The sensor id is the same as those defined in ID_LOOKUP['SENSOR'].
MISC_SENSORS = {
}

# Set fan_algorithm config
#   FAN_DBUS_INTF_LOOKUP: {keys:[dbus bus name, dbus interface name]}
#   CHASSIS_POWER_STATE: set chassis power state object path
#   FAN_INPUT_OBJ: set fan input object path
#       - ["fan tach obj path", "pwm index mapping with fan tach"]
#   FAN_OUTPUT_OBJ: set fan out object path , eg: hwmon control fan speed or
#   directly use pwm control pwm
#   OPEN_LOOP_PARAM: set openloop parameter
#       - paramA
#       - paramB
#       - paramC
#       - Low_Amb
#       - Up_Amb
#       - Low_Speed
#       - High_Speed
#   OPEN_LOOP_GROUPS_1: set openloop object path
#   CLOSE_LOOP_PARAM_1: set closeloop parameter
#       - g_Kp
#       - g_Ki
#       - g_Kd
#       - g_CPUVariable
#       - g_DIMMVariable
#       - sensor_tracking
#       - highest warning temp
#   CLOSE_LOOP_GROUPS_1: set closeloop  group001 object path, eg: CPU0/CPU1
#   CLOSE_LOOP_PARAM_2: set closeloop parameter
#       - g_Kp
#       - g_Ki
#       - g_Kd
#       - g_CPUVariable
#       - g_DIMMVariable
#       - sensor_tracking
#       - highest warning temp
#   CLOSE_LOOP_GROUPS_2: set closeloop  group002 object path, eg: DIMM
#   FAN_LED_OFF: set fan led command: off
#   FAN_LED_PORT0_ALL_BLUE: set fan led port0 command: all blue
#   FAN_LED_PORT1_ALL_BLUE: set fan led port1 command: all blue
#   FAN_LED_PORT0_ALL_RED: set fan led port0 command: all red
#   FAN_LED_PORT1_ALL_RED: set fan led port1 command: all red
#   PORT0_FAN_LED_RED_MASK: set fan led port0 register mask with red
#   PORT0_FAN_LED_BLUE_MASK: set fan led port0 register mask with blue
#   PORT1_FAN_LED_RED_MASK: set fan led port1 register mask with red
#   PORT1_FAN_LED_BLUE_MASK: set fan led port1 register mask with blue
#   FAN_LED_I2C_BUS: set fan led i2c bus
#   FAN_LED_I2C_SLAVE_ADDRESS: set fan led i2c slave address
FAN_ALGORITHM_CONFIG = {
    'FAN_DBUS_INTF_LOOKUP':
    {
        'CHASSIS_POWER_STATE': [
            'org.openbmc.control.Chassis', 'org.openbmc.control.Chassis'],
        'FAN_INPUT_OBJ' : ['org.openbmc.Sensors', 'org.openbmc.SensorValue'],
        'FAN_OUTPUT_OBJ' : ['org.openbmc', 'org.openbmc.Fan'],
        'OPEN_LOOP_GROUPS_1' : [
            'org.openbmc.Sensors', 'org.openbmc.SensorValue'],
        'CLOSE_LOOP_GROUPS_1' : [
            'org.openbmc.Sensors', 'org.openbmc.SensorValue'],
        'CLOSE_LOOP_GROUPS_2' : [
            'org.openbmc.Sensors', 'org.openbmc.SensorValue'],
    },

    'CHASSIS_POWER_STATE': ['/org/openbmc/control/chassis0'],
    'FAN_INPUT_OBJ':
        [
            "/org/openbmc/sensors/fan/fan_tacho1", "pwm1",
            "/org/openbmc/sensors/fan/fan_tacho2", "pwm2",
            "/org/openbmc/sensors/fan/fan_tacho3", "pwm3",
            "/org/openbmc/sensors/fan/fan_tacho4", "pwm4",
            "/org/openbmc/sensors/fan/fan_tacho5", "pwm5",
            "/org/openbmc/sensors/fan/fan_tacho6", "pwm6",
            "/org/openbmc/sensors/fan/fan_tacho7", "pwm1",
            "/org/openbmc/sensors/fan/fan_tacho8", "pwm2",
            "/org/openbmc/sensors/fan/fan_tacho9", "pwm3",
            "/org/openbmc/sensors/fan/fan_tacho10", "pwm4",
            "/org/openbmc/sensors/fan/fan_tacho11", "pwm5",
            "/org/openbmc/sensors/fan/fan_tacho12", "pwm6",
        ],
    'FAN_OUTPUT_OBJ':
        [
            "/org/openbmc/control/fan/pwm1",
            "/org/openbmc/control/fan/pwm2",
            "/org/openbmc/control/fan/pwm3",
            "/org/openbmc/control/fan/pwm4",
            "/org/openbmc/control/fan/pwm5",
            "/org/openbmc/control/fan/pwm6",
        ],
    'OPEN_LOOP_PARAM':
        [
            '0',
            '2',
            '-60',
            '25',
            '35',
            '40',
            '100',
        ],
    'OPEN_LOOP_GROUPS_1':
        [
            "/org/openbmc/sensors/temperature/TMP4",
            #Thermal team only watch temp4 ambinet
        ],
    'CLOSE_LOOP_PARAM_1' :
        [
            '0.35',
            '-0.015',
            '0.4',
            '70',
            '85',
        ],
    'CLOSE_LOOP_GROUPS_1':
        [
            "/org/openbmc/sensors/gpu/gpu1_temp",
            "/org/openbmc/sensors/gpu/gpu2_temp",
            "/org/openbmc/sensors/gpu/gpu3_temp",
            "/org/openbmc/sensors/gpu/gpu4_temp",
            "/org/openbmc/sensors/gpu/gpu5_temp",
            "/org/openbmc/sensors/gpu/gpu6_temp",
            "/org/openbmc/sensors/gpu/gpu7_temp",
            "/org/openbmc/sensors/gpu/gpu8_temp",
        ],
    'CLOSE_LOOP_PARAM_2' :
        [
            '0.35',
            '-0.015',
            '0.4',
            '90',
            '85',
        ],
    'CLOSE_LOOP_GROUPS_2':
        [
            "/org/openbmc/sensors/pex/pex0",
            "/org/openbmc/sensors/pex/pex1",
            "/org/openbmc/sensors/pex/pex2",
            "/org/openbmc/sensors/pex/pex3",
        ],

    'FAN_LED_OFF': ["0xFF"],
    'FAN_LED_PORT0_ALL_BLUE': ["0xAA"],
    'FAN_LED_PORT1_ALL_BLUE': ["0x55"],
    'FAN_LED_PORT0_ALL_RED': ["0x55"],
    'FAN_LED_PORT1_ALL_RED': ["0xAA"],
    'PORT0_FAN_LED_RED_MASK': ["0x02"],
    'PORT0_FAN_LED_BLUE_MASK': ["0x01"],
    'PORT1_FAN_LED_RED_MASK': ["0x40"],
    'PORT1_FAN_LED_BLUE_MASK': ["0x80"],
    'FAN_LED_SPEED_LIMIT': ["30"],

    'FAN_LED_I2C_BUS': [],
    'FAN_LED_I2C_SLAVE_ADDRESS': [],
}



LOG_EVENT_CONFIG = [{
    'EVD1': 0x1,
    'EVD2':0x1,
    'EVD3':None,
    'health_indicator':'Network Error',
    'description':'Link down',
    'detail': '',
}, {
    'EVD1': 0x1,
    'EVD2':0x2,
    'EVD3':None,
    'health_indicator':'Network Error',
    'description':'DHCP failure',
    'detail': '',
}, {
    'EVD1': 0x3,
    'EVD2':None,
    'EVD3':None,
    'health_indicator':'Hardware WDT expired',
    'description':'',
    'detail': '',
}, {
    'EVD1': 0xA,
    'EVD2':None,
    'EVD3':None,
    'health_indicator':'I2C bus recovery',
    'description':'',
    'detail': '',
}, {
    'EVD1': 0xC,
    'EVD2':None,
    'EVD3':None,
    'health_indicator':'No MAC address programmed',
    'description':'',
    'detail': '',
}]
