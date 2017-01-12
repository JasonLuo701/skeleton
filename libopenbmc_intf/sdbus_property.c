#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <dirent.h>
#include <systemd/sd-bus.h>

int
set_dbus_property(char *objpath, char *property_name, char *property_type, void *property_value)
{
	sd_bus *bus = NULL;
	sd_bus_error bus_error = SD_BUS_ERROR_NULL;
	sd_bus_message *response = NULL;
	int rc = 0;

	if (property_value == NULL || property_type == NULL || property_name==NULL || objpath == NULL)
		return 0;

	rc = sd_bus_open_system(&bus);
	if(rc < 0) {
		fprintf(stderr,"Error opening system bus.\n");
		return rc;
	}



	if (property_type[0] == 'i') {
		rc = sd_bus_call_method(bus,
					"org.openbmc.Sensors",
					objpath,
					"org.freedesktop.DBus.Properties",
					"Set",
					&bus_error,
					&response,
					"ssv",
					"org.openbmc.HwmonSensor", property_name, "i",
					*((int *) property_value)
				       );
	} else if (property_type[0] == 's') {
		rc = sd_bus_call_method(bus,
					"org.openbmc.Sensors",
					objpath,
					"org.freedesktop.DBus.Properties",
					"Set",
					&bus_error,
					&response,
					"ssv",
					"org.openbmc.HwmonSensor", property_name, "s",
					*((char **)property_value)
				       );
	} else
		rc = -1;

	if(rc < 0) {
		printf("%s, %d response message:[%s]\n", __FUNCTION__, __LINE__, strerror(-rc));
	}
	sd_bus_unref(bus);
	return rc;
}
