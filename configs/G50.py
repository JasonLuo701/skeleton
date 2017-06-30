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
GPIO_CONFIG['UBB_SMB_RST_N'] = {'gpio_pin': 'C6', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['PDB_SMB_RST_N'] = {'gpio_pin': 'C7', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['BLADE_ATT_LED_N'] = {'gpio_pin': 'F0', 'direction': 'out', 'inverse': 'yes', 'data_reg_addr': 0x1e780020, 'offset': 8}
GPIO_CONFIG['PWR_BTN_N'] = {'gpio_pin': 'F1', 'direction': 'both'}
GPIO_CONFIG['PWR_STA_LED_N'] = {'gpio_pin': 'F2', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['UID_BTN_N'] = {'gpio_pin': 'F3', 'direction': 'both'}
GPIO_CONFIG['UID_LED_N'] = {'gpio_pin': 'F4', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['SYS_THROTTLE_N'] = {'gpio_pin': 'F5', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['FM_GPIO4'] = {'gpio_pin': 'F6', 'direction': 'out'}
GPIO_CONFIG['GPU_OVERT_N'] = {'gpio_pin': 'F7', 'direction': 'out'}
GPIO_CONFIG['RM_SYS_THROTTLE_N'] = {'gpio_pin': 'M0', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['FIO_RM_SYS_THROTTLE_N'] = {'gpio_pin': 'M1', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['PWR_ON_REQ_N'] = {'gpio_pin': 'M2', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['SYS_FORCE_PWR_OFF'] = {'gpio_pin': 'M3', 'direction': 'out'}
GPIO_CONFIG['SYS_READY_N'] = {'gpio_pin': 'M4', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['FM_GPIO1'] = {'gpio_pin': 'M5', 'direction': 'out'}
GPIO_CONFIG['FM_GPIO2'] = {'gpio_pin': 'M6', 'direction': 'out'}
GPIO_CONFIG['FM_GPIO3'] = {'gpio_pin': 'M7', 'direction': 'out'}
GPIO_CONFIG['BMC_BSC_ALT_N'] = {'gpio_pin': 'Q6', 'direction': 'in', 'inverse': 'yes'}
GPIO_CONFIG['BMC_SMB_4_RST_N'] = {'gpio_pin': 'Q7', 'direction': 'out', 'inverse': 'yes'}
GPIO_CONFIG['BMC_HB_LED'] = {'gpio_pin': 'R4', 'direction': 'out'}


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
        'positive_hysteresis': 2,
        'device_node': '/tmp/gpu/gpu%d_temp' % index,
        'object_path': 'sensors/gpu/gpu%d_temp' % index,
        'poll_interval': 5000,
        'reading_type': 0x01,
        'scale': 1,
        'sensor_name': 'GPU%d Temp' % index,
        'sensor_type': '0x01',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'C',
        'index': index,
        'value': -1
        }]
    configs.append(config)

def _add_fan_pwm_sensor(configs, index, sensornumber):
    config = ['/org/openbmc/control/fan/pwm%d' % index, {
        'device_node':
            '/sys/devices/platform/ast_pwm_tacho.0/pwm%d_falling' % index,
        'object_path': 'control/fan/pwm%d' % index,
        'warning_lower': 18,
        'poll_interval': 10000,
        'reading_type': 0x01,
        'scale': 1,
        'sensor_name': 'PWM %d' % index,
        'sensor_type': '0x04',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': '%',
        'value': -1,
        }]
    configs.append(config)

def _add_fan_tach_sensor(configs, index, sensornumber):
    config = ['/org/openbmc/sensors/fan/fan_tacho%d' % index, {
        'critical_lower': 3800,
        'device_node':
            '/sys/devices/platform/ast_pwm_tacho.0/tacho%d_rpm' % index,
        'object_path': 'sensors/fan/fan_tacho%d' % index,
        'poll_interval': 10000,
        'reading_type': 0x01,
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
        'positive_hysteresis': 2,
        'device_node': 'temp2_input',
        'object_path': 'sensors/pmbus/pmbus0%d/temp_02' % index,
        'poll_interval': 10000,
        'reading_type': 0x01,
        'scale': 1000,
        'sensor_name': 'PSU%d Temp 2' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'C',
        'value': -1,
        'firmware_update': 0, # 0: normal, 1:firmware_update working
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
        'reading_type': 0x01,
        'scale': 1000,
        'sensor_name': 'PSU%d Voltage Output' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'V',
        'value': -1,
        'index': index,
        'firmware_update': 0, # 0: normal, 1:firmware_update working
        }]
    configs.append(config)

def _add_psu_power_sensor(configs, index, sensornumber, bus_number):
    config = ['/org/openbmc/sensors/pmbus/pmbus0%d/Power_pout' % index, {
        'bus_number': bus_number,
        'critical_upper': 1760,
        'device_node': 'power2_input',
        'object_path': 'sensors/pmbus/pmbus0%d/Power_pout' % index,
        'poll_interval': 10000,
        'reading_type': 0x01,
        'scale': 1000000,
        'sensor_name': 'PSU%d Power Output' % index,
        'sensor_type': '0x09',
        'sensornumber': sensornumber,
        'standby_monitor': False,
        'units': 'W',
        'value': -1,
        'firmware_update': 0, # 0: normal, 1:firmware_update working
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
        'entity': 0x1F,
        'index': index,
        }]
    configs.append(config)

def _add_pex9797(configs, index, sensornumber):
    config = ['/org/openbmc/sensors/pex/pex%d' % index, {
        'device_node': '/tmp/pex/pex%d_temp' % index,
        'critical_upper': 111,
        'positive_hysteresis': 2,
        'object_path': 'sensors/pex/pex%d' % index,
        'poll_interval': 5000,
        'scale': 1,
        'sensornumber': sensornumber,
        'sensor_type': '0x01',
        'reading_type': 0x01,
        'sensor_name': 'PLX Switch %d Temp' % (index+1),
        'standby_monitor': False,
        'units': 'C',
        'index': index,
        }]
    configs.append(config)

def _add_bmc_health_sensor(configs, sensornumber):
    config = ['/org/openbmc/sensors/bmc_health', {
        'device_node': '',
        'object_path': 'sensors/bmc_health',
        'reading_type': 0x70,
        'sensor_name': 'BMC Health',
        'sensor_type': '0x28',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'value': 0,
        }]
    configs.append(config)

def _add_ntp_status_sensor(configs, sensornumber):
    config = ['/org/openbmc/sensors/ntp_status', {
        'device_node': '',
        'object_path': 'sensors/bmc_health',
        'reading_type': 0x71,
        'sensor_name': 'BMC Health',
        'sensor_type': '0x12',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'value': 0,
        }]
    configs.append(config)

def _add_psu_status_sensor(configs, index, sensornumber, bus_number):
    config = ['/org/openbmc/sensors/pmbus/pmbus0%d/status' % index, {
        'bus_number': bus_number,
        'device_node': 'pmbus_status_word',
        'object_path': 'sensors/pmbus/pmbus0%d/status' % index,
        'poll_interval': 5000,
        'reading_type': 0x6F,
        'scale': 1,
        'sensor_name': 'PSU%d Status' % index,
        'sensor_type': '0x08',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'units': '',
        'value': 0,
        'firmware_update': 0, # 0: normal, 1:firmware_update working
        }]
    configs.append(config)

def _add_entity_presence(configs, sensornumber):
    config = ['/org/openbmc/sensors/entity_presence', {
        'device_node': '',
        'object_path': 'sensors/entity_presence',
        'reading_type': 0x6F,
        'sensor_name': 'Entity Presence',
        'sensor_type': '0x25',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'value': 0,
        }]
    configs.append(config)

def _add_management_subsystem_health(configs, sensornumber):
    config = ['/org/openbmc/sensors/management_subsystem_health', {
        'device_node': '',
        'object_path': 'sensors/management_subsystem_health',
        'reading_type': 0x6F,
        'sensor_name': 'Management Subsystem Health',
        'sensor_type': '0x28',
        'sensornumber': sensornumber,
        'standby_monitor': True,
        'value': 0,
        }]
    configs.append(config)

def _add_pcie_slot(configs, index, gpio):
    config = ['/org/openbmc/control/pcie/slot%d' % index, {
        'device_node': '/sys/class/gpio/gpio%d/value' % gpio,
        'object_path': 'control/pcie/slot%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': True,
        'units': '',
        'entity': 0xB,
        'index': index,
        }]
    configs.append(config)

def _add_gpu_slot(configs, index, gpio):
    config = ['/org/openbmc/control/gpu/slot%d' % index, {
        'device_node': '/sys/class/gpio/gpio%d/value' % gpio,
        'object_path': 'control/gpu/slot%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': True,
        'units': '',
        'entity': 0x3,
        'index': index,
        }]
    configs.append(config)

def _add_powergood_gpio(configs, index, gpio):
    config = ['/org/openbmc/control/powergood/slot%d' % index, {
        'device_node': '/sys/class/gpio/gpio%d/value' % gpio,
        'object_path': 'control/powergood/slot%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': True,
        'units': '',
        'index': index,
        }]
    configs.append(config)

def _add_thermal_gpio(configs, index, gpio):
    config = ['/org/openbmc/control/thermal/slot%d' % index, {
        'device_node': '/sys/class/gpio/gpio%d/value' % gpio,
        'object_path': 'control/thermal/slot%d' % index,
        'poll_interval': 10000,
        'scale': 1,
        'standby_monitor': True,
        'units': '',
        'index': index,
        }]
    configs.append(config)

SENSOR_MONITOR_CONFIG = []
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 1, 0x41)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 2, 0x42)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 3, 0x43)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 4, 0x44)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 5, 0x45)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 6, 0x46)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 7, 0x47)
_add_gpu_temperature_sensor(SENSOR_MONITOR_CONFIG, 8, 0x48)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 1, 0x1D)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 2, 0x1E)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 3, 0x1F)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 4, 0x20)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 5, 0x21)
_add_fan_pwm_sensor(SENSOR_MONITOR_CONFIG, 6, 0x22)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 1, 0x11)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 2, 0x12)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 3, 0x13)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 4, 0x14)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 5, 0x15)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 6, 0x16)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 7, 0x17)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 8, 0x18)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 9, 0x19)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 10, 0x1A)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 11, 0x1B)
_add_fan_tach_sensor(SENSOR_MONITOR_CONFIG, 12, 0x1C)
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 1, 0x52, '8-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 1, 0x51, '8-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 1, 0x50, '8-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 2, 0x55, '9-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 2, 0x54, '9-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 2, 0x53, '9-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 3, 0x58, '10-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 3, 0x57, '10-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 3, 0x56, '10-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 4, 0x5B, '11-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 4, 0x5A, '11-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 4, 0x59, '11-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 5, 0x5E, '12-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 5, 0x5D, '12-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 5, 0x5C, '12-0058')
_add_psu_temperature_sensor(SENSOR_MONITOR_CONFIG, 6, 0x61, '13-0058')
_add_psu_voltage_sensor(SENSOR_MONITOR_CONFIG, 6, 0x60, '13-0058')
_add_psu_power_sensor(SENSOR_MONITOR_CONFIG, 6, 0x5F, '13-0058')
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
_add_pex9797(SENSOR_MONITOR_CONFIG, 0, 0x37)
_add_pex9797(SENSOR_MONITOR_CONFIG, 1, 0x38)
_add_pex9797(SENSOR_MONITOR_CONFIG, 2, 0x39)
_add_pex9797(SENSOR_MONITOR_CONFIG, 3, 0x3A)
_add_ntp_status_sensor(SENSOR_MONITOR_CONFIG, 0x81)
_add_bmc_health_sensor(SENSOR_MONITOR_CONFIG, 0x82)
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 1, 0x83, '8-0058')
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 2, 0x84, '9-0058')
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 3, 0x85, '10-0058')
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 4, 0x86, '11-0058')
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 5, 0x87, '12-0058')
_add_psu_status_sensor(SENSOR_MONITOR_CONFIG, 6, 0x88, '13-0058')
_add_entity_presence(SENSOR_MONITOR_CONFIG, 0x8A)
_add_management_subsystem_health(SENSOR_MONITOR_CONFIG, 0x89)
_add_pcie_slot(SENSOR_MONITOR_CONFIG, 1, 220)
_add_pcie_slot(SENSOR_MONITOR_CONFIG, 2, 221)
_add_pcie_slot(SENSOR_MONITOR_CONFIG, 3, 222)
_add_pcie_slot(SENSOR_MONITOR_CONFIG, 4, 223)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 1, 212)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 2, 213)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 3, 214)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 4, 215)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 5, 216)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 6, 217)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 7, 218)
_add_gpu_slot(SENSOR_MONITOR_CONFIG, 8, 219)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 1, 204)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 2, 205)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 3, 206)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 4, 207)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 5, 208)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 6, 209)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 7, 210)
_add_powergood_gpio(SENSOR_MONITOR_CONFIG, 8, 211)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 1, 196)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 2, 197)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 3, 198)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 4, 199)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 5, 200)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 6, 201)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 7, 202)
_add_thermal_gpio(SENSOR_MONITOR_CONFIG, 8, 203)

HWMON_CONFIG = {
    '0-0010' :  {
        'names' : {
            'in3_input' : {
                'object_path' : 'sensors/HSC/HSC1_VOUT',
                'poll_interval' : 5000,
                'scale' : 1000,
                'units' : 'V',
                'sensor_type' : '0x02',
                'sensornumber' : 0x23,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC1 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x24,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC1 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x25,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC2 STBY VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x26,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC2 STBY Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x27,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC3 GPU1 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x28,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC3 GPU1 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x29,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC4 GPU2 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2A,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC4 GPU2 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2B,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC5 GPU3 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2C,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC5 GPU3 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2D,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC6 GPU4 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2E,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC6 GPU4 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x2F,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC7 GPU5 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x30,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC7 GPU5 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x31,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC8 GPU6 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x32,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC8 GPU6 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x33,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC9 GPU7 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x34,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC9 GPU7 Temp',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x35,
                'critical_lower':10.6,
                'critical_upper':13.8,
                'sensor_name':'HSC10 GPU8 VOUT',
                'reading_type' : 0x01,
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
                'sensornumber' : 0x36,
                'critical_upper':125,
                'positive_hysteresis': 2,
                'sensor_name':'HSC10 GPU8 Temp',
                'reading_type' : 0x01,
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
                'reading_type' : 0x01,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'reading_type' : 0x01,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'reading_type' : 0x01,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'reading_type' : 0x01,
                'emergency_enabled' : True,
                'offset':-7,
                'standby_monitor': False,
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
                'sensornumber' : 0x01,
                'sensor_name':'Inlet Temp 5',
                'reading_type' : 0x01,
                'critical_upper' : 37,
                'positive_hysteresis': 2,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'sensornumber' : 0x02,
                'sensor_name':'Inlet Temp 6',
                'reading_type' : 0x01,
                'critical_upper' : 37,
                'positive_hysteresis': 2,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'sensornumber' : 0x03,
                'sensor_name':'Inlet Temp 7',
                'reading_type' : 0x01,
                'critical_upper' : 37,
                'positive_hysteresis': 2,
                'emergency_enabled' : True,
                'standby_monitor': False,
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
                'sensornumber' : 0x04,
                'sensor_name':'Inlet Temp 8',
                'reading_type' : 0x01,
                'critical_upper' : 37,
                'positive_hysteresis': 2,
                'emergency_enabled' : True,
                'standby_monitor': False,
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

BMC_LOGEVENT_CONFIG = {
	'BMC Health': {
	    'Record ID': 0,
	    'Record Type': 0x2,
	    'Timestamp': 0,
	    'Generator Id': 0x20,
	    'Evm Rev': 0x04,
	    'Event Type': 0x70,
	    'Event Data Table': {
			'Network Error': {
				'Severity': 'Critical',
				'Event Data Information': {
					'Link Down':	[0xA1, 0x1, None],
					'DHCP Failure':	[0xA1, 0x2, None],
				},
			},
			'Hardware WDT expired': {
				'Severity': 'Critical',
				'Event Data Information': {
					'Hardware WDT expired':	[0xA3, None, None],
				},
			},
			'I2C bus hang': {
				'Severity': 'Warning',
				'Event Data Information': {
					'I2C bus hang':	[0xAA, 'i2c_bus_id', 'i2c_error_code'],
				},
			},
			'Log Rollover': {
				'Severity': 'OK',
				'Event Data Information': {
					'Log Rollover':	[0xAB, 'log_rollover_count', None],
				},
			},
			'No MAC address programmed': {
				'Severity': 'Critical',
				'Event Data Information': {
					'No MAC address programmed':	[0xAC, None, None],
				},
			},
			'Firmware Update Started': {
				'Severity': 'OK',
				'Event Data Information': {
					'BMC Firmware Update Started':	[0xAD, 0x1, 'index'],
					'PSU Firmware Update Started':	[0xAD, 0x2, 'index'],
					'FPGA Firmware Update Started':	[0xAD, 0x3, 'index'],
				},
			},
			'Firmware Update completed': {
				'Severity': 'OK',
				'Event Data Information': {
					'BMC Firmware Update completed':	[0xAE, 0x1, 'index'],
					'PSU Firmware Update completed':	[0xAE, 0x2, 'index'],
					'FPGA Firmware Update completed':	[0xAE, 0x3, 'index'],
				},
			},
		},
	},
	'Entity Presence': {
		'Record ID': 0,
		'Record Type': 0x2,
		'Timestamp': 0,
		'Generator Id': 0x20,
		'Evm Rev': 0x04,
		'Event Type': 0x6F,
		'Event Data Table': {
			'Entity Presence': {
				'Severity': 'Critical',
				'Event Data Information': {
					'Entity Presence':	[0xA1, 'entity_device', 'entity_index'],
				},
			},
		},
	},
	'Management Subsystem Health': {
		'Record ID': 0,
		'Record Type': 0x2,
		'Timestamp': 0,
		'Generator Id': 0x20,
		'Evm Rev': 0x04,
		'Event Type': 0x6F,
		'Event Data Table': {
			'Management Subsystem Health': {
				'Severity': 'Critical',
				'Event Data Information': {
					'Management Subsystem Health':	['event_status', 'sensor_number', 0xFF],
				},
			},
		},
	},
}

