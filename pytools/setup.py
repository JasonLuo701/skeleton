from distutils.core import setup

setup(name='pytools',
      version='1.0',
      scripts=['obmcutil', 'gpioutil', 'mac_guid.py', 'ntp_eeprom.py', 'Liteon_FW_Update.sh', 'obmc_err_injection', \
              'set_hostname.sh'],
      )
