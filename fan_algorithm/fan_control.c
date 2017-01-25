#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include "fan_control.h"

#define FAN_TACH_DBUS_OBJ_FORMAT "fan_tacho%d"

#define PWM_MAX_UNIT (255)
#define SYS_PWM_PATH "/sys/devices/platform/ast_pwm_tacho.0/"

static char g_pwm_cmd_map_sys_tab[][20] = {
	"_en",  //EM_FAN_CMD_EN --> "pwmX_en", X :mean pwm index eg: "pwm0_en"
	"_falling",  //EM_PWM_CMD_FALLING --> "pwmX_falling", X :mean pwm index eg: "pwm0_falling"
	"_rising",  //EM_PWM_CMD_RISING --> "pwmX_rising", X :mean pwm index eg: "pwm0_rising"
	"_type",  //EM_PWM_CMD_TYPE --> "pwmX_type", X :mean pwm index eg: "pwm0_type"
	"_rpm",  //EM_TACH_CMD_RPM --> "tachoX_rpm", X :mean pwm index eg: "tacho0_rpm"
	"_source",  //EM_TACH_CMD_SOURCE --> "tachoX_source", X :mean pwm index eg: "tacho0_source"
};

/*
 * ----------------------------------------------------------------
 * Router function for any FAN operations that come via dbus
 *----------------------------------------------------------------
 */
static int
get_fan_index(char *fan_name, char *format_s)
{
	int fan_index;
	sscanf(fan_name, format_s, &fan_index);
	return fan_index;
}


void
sys_pwm_write(int pwm_idex, EM_PWM_NODE_CMD pwm_cmd, int write_value, char*prefix)
{
	char sys_pwm_path[100];
	char sys_cmd[100];
	int rc;

	if (write_value > PWM_MAX_UNIT)
		write_value = PWM_MAX_UNIT;
	else if (write_value < 0)
		write_value = 0;

	rc = sprintf(sys_pwm_path , "%s%s%d%s", SYS_PWM_PATH, prefix, pwm_idex, g_pwm_cmd_map_sys_tab[pwm_cmd]);
	sprintf(sys_cmd, "echo %d > %s", write_value, sys_pwm_path);
	system(sys_cmd);
}

int
sys_pwm_read(int pwm_idex, EM_PWM_NODE_CMD pwm_cmd, char*prefix)
{
	char sys_pwm_path[100];
	FILE *fp;
	int retValue = -1;
	char buf[100] = {0};
	int ret_len;

	sprintf(sys_pwm_path , "%s%s%d%s", SYS_PWM_PATH, prefix, pwm_idex, g_pwm_cmd_map_sys_tab[pwm_cmd]);

	fp = fopen(sys_pwm_path,"r");
	if(fp == NULL) {
		fprintf(stderr,"Error:[%s] opening:[%s]\n",strerror(errno),sys_pwm_path);
		return -1;
	}
	ret_len = fread(buf, 1, 100, fp);
	sscanf(buf, "%d", &retValue);
	fclose(fp);

	return retValue;
}

int
fan_control_init(int reponse_len, char reponse_data[50][200])
{
	/* Generic error reporter. */
	int i;
	int fan_index;
	for (i = 0; i<reponse_len; i++) {
		if (i%2 == 0) {
			//Enable fan tach
			char *fan_name = NULL;
			fan_name = strrchr(reponse_data[i], '/');
			if(fan_name) {
				fan_name++;
			} else
				return 0;

			fan_index = get_fan_index(fan_name, FAN_TACH_DBUS_OBJ_FORMAT);
			sys_pwm_write(fan_index, EM_FAN_CMD_EN, 1, "tacho");
		} else {
			int pwm_source;
			sscanf(reponse_data[i], "pwm%d", &pwm_source);
			sys_pwm_write(fan_index, EM_TACH_CMD_SOURCE, pwm_source, "tacho");

		}
	}

	return 1;
}
