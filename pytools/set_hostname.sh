#!/bin/sh

mac=$(ifconfig |grep eth0 |awk '{print $5}')
mac_byte4=${mac:9:2}
mac_byte5=${mac:12:2}
mac_byte6=${mac:15:2}

hostname g50@${mac_byte4}_${mac_byte5}_${mac_byte6}
