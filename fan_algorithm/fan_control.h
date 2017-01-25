#ifndef __FAN_CONTROL_H__
#define __FAN_CONTROL_H__

typedef enum {
	EM_FAN_CMD_EN = 0, //set pwm & tach enable
	EM_PWM_CMD_FALLING, //set pwm duty falling
	EM_PWM_CMD_RISING, //set pwm duty rising
	EM_PWM_CMD_TYPE, //set pwm type (M/N/O)
	EM_TACH_CMD_RPM, //set fan tach rpm
	EM_TACH_CMD_SOURCE, //set fan tach source
} EM_PWM_NODE_CMD;

extern int fan_control_init(int reponse_len, char reponse_data[50][200]);
extern int sys_pwm_read(int pwm_idex, EM_PWM_NODE_CMD pwm_cmd, char*prefix);
extern void sys_pwm_write(int pwm_idex, EM_PWM_NODE_CMD pwm_cmd, int write_value, char*prefix);

#endif
