#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <systemd/sd-bus.h>
#include <linux/i2c-dev-user.h>
#include <log.h>
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>



#define I2C_CLIENT_PEC          0x04    /* Use Packet Error Checking */
#define I2C_M_RECV_LEN          0x0400  /* length will be first received byte */

#define MAX_PATH_LEN 70
#define MAX_SENSOR_NUM 40
#define SAMPLING_N  20

#define CMD_OUTPUT_PORT_0 2

#define FAN_SHM_KEY  (4320)
#define FAN_SHM_PATH "skeleton/fan_algorithm"
#define MAX_WAIT_TIMEOUT  (50000)

struct st_closeloop_obj_data {
    int index;
	int sensor_tracking;
	int warning_temp;
	int sensor_reading;
	int interal_Err[100];
	int intergral_i;
	int last_error;
	double Kp;
	double Ki;
	double Kd;
};

struct st_fan_obj_path_info {
	char service_bus[MAX_PATH_LEN];
	char service_inf[MAX_PATH_LEN];
	char path[MAX_SENSOR_NUM][MAX_PATH_LEN];
	int size;
	void *obj_data;
	struct st_fan_obj_path_info *next;
};

struct st_fan_closeloop_par {
	double Kp;
	double Ki;
	double Kd;
	int sensor_tracking;
	int warning_temp;
	int pid_value;
	int closeloop_speed;
	int closeloop_sensor_reading;
	int sample_n;
};

struct st_fan_parameter {
	int flag_closeloop; //0: init ; 1:do nothing ; 2: changed; 3:lock waiting
	int closeloop_count;
	struct st_fan_closeloop_par closeloop_param[5];

	int flag_openloop; //0: init ; 1:do nothing ; 2: changed; 3:lock waiting
	float g_ParamA;
	float g_ParamB;
	float g_ParamC;
	int g_LowAmb;
	int g_UpAmb;
	int g_LowSpeed;
	int g_HighSpeed;
	int openloop_speed;
	int openloop_sensor_reading;
	int openloop_sensor_offset;

	int current_speed;
	int max_fanspeed;
	int min_fanspeed;
};



static struct st_fan_obj_path_info g_FanInputObjPath = {0};
static struct st_fan_obj_path_info g_CloseloopG1_ObjPath = {0};
static struct st_fan_obj_path_info g_CloseloopG3_ObjPath = {0};
static struct st_fan_obj_path_info g_CloseloopG2_ObjPath = {0};
static struct st_fan_obj_path_info g_AmbientObjPath = {0};
static struct st_fan_obj_path_info g_FanSpeedObjPath = {0};
static struct st_fan_obj_path_info g_FanModuleObjPath = {0};
static struct st_fan_obj_path_info g_PowerObjPath = {0};
static struct st_fan_obj_path_info *g_Closeloop_Header = NULL;
static struct st_fan_obj_path_info *g_Openloop_Header = NULL;

static struct st_fan_parameter *g_fan_para_shm = NULL;
static int g_shm_id;
static char *g_shm_addr = NULL;


//OpenLoop config parameters
static float g_ParamA= 0;
static float g_ParamB= 0;
static float g_ParamC= 0;
static int g_LowAmb = 0;
static int g_UpAmb = 0;
static int g_LowSpeed = 0;
static int g_HighSpeed = 0;

//Fan LED command & register mask
static int FAN_LED_OFF   =  0;
static int FAN_LED_PORT0_ALL_BLUE = 0;
static int FAN_LED_PORT1_ALL_BLUE = 0;
static int FAN_LED_PORT0_ALL_RED = 0;
static int FAN_LED_PORT1_ALL_RED = 0;
static int PORT0_FAN_LED_RED_MASK = 0;
static int PORT0_FAN_LED_BLUE_MASK = 0;
static int PORT1_FAN_LED_RED_MASK = 0;
static int PORT1_FAN_LED_BLUE_MASK = 0;
static int g_fanled_speed_limit = 0;

//Fan LED I2C bus
static char g_FanLed_I2CBus [MAX_PATH_LEN] = {0};
//Fan LED I2C Slave Address
static unsigned char g_FanLed_SlaveAddr = 0;

static int g_FanSpeed = 0;
static int g_Openloopspeed = 0;
static int g_Closeloopspeed = 0;
static unsigned int closeloop_first_time = 0;

static int initial_fan_config(sd_bus *bus);

static int push_fan_obj(struct st_fan_obj_path_info **header, struct st_fan_obj_path_info *item)
{
	struct st_fan_obj_path_info *t_header;

	if (*header == NULL) {
		*header = item;
		return 1;
	}

	t_header = *header;
	while (t_header->next != NULL)
		t_header = t_header->next;

	t_header->next = item;
	return 1;
}

static int freeall_fan_obj(struct st_fan_obj_path_info **header)
{
	struct st_fan_obj_path_info *t_header = NULL, *t_next = NULL;
	t_header = *header;
	while(t_header != NULL) {
		if (t_header->obj_data != NULL)
			free(t_header->obj_data);
		t_next = t_header->next;
		free(t_header);
		t_header = t_next;
	}
}

static int set_fanled(uint8_t port0, uint8_t port1, int use_pec)
{
	struct i2c_rdwr_ioctl_data data;
	struct i2c_msg msg[1];
	uint8_t write_bytes[3];
	int fd = -1;

	if (strlen(g_FanLed_I2CBus)<=0)
		return -1;

	fd = open(g_FanLed_I2CBus, O_RDWR);
	if (fd != -1) {
		LOG_ERR(errno, "Failed to open i2c device %s", g_FanLed_I2CBus);
		close(fd);
		return -1;
	}

	memset(&msg, 0, sizeof(msg));

	write_bytes[0] = CMD_OUTPUT_PORT_0;
	write_bytes[1] = port0;
	write_bytes[2] = port1;

	msg[0].addr = g_FanLed_SlaveAddr;
	msg[0].flags = (use_pec) ? I2C_CLIENT_PEC : 0;
	msg[0].len = sizeof(write_bytes);
	msg[0].buf = write_bytes;

	data.msgs = msg;
	data.nmsgs = 1;
	if (ioctl(fd, I2C_RDWR, &data) < 0) {
		LOG_ERR(errno, "Failed to do raw io");
		close(fd);
		return -1;
	}

	return 0;
}

static int calculate_closeloop(struct st_closeloop_obj_data *sensor_data, int current_fanspeed)
{
	int total_integral_error;
	int i;
	int pid_value;
	int pwm_speed;
	double Kp = 0, Ki = 0, Kd = 0;
	int cur_interal_Err = 0;
	static int closeloop_fanspeed = 0;
	int sample_n = 0;
	int index;

	if (sensor_data == NULL)
		return 0;

	if (sensor_data->sensor_reading <=0) {
		g_Closeloopspeed = 0;
		return 0;
	}

	Kp = sensor_data->Kp;
	Ki = sensor_data->Ki;
	Kd = sensor_data->Kd;

	index = sensor_data->index;

	if (g_fan_para_shm != NULL)
		sample_n = g_fan_para_shm->closeloop_param[index].sample_n;
	else
		sample_n = SAMPLING_N;

	printf("[FAN_ALGORITHM][%s, %d] [PID value] kp:%f, Ki:%f, Kd:%f, target: %d\n", __FUNCTION__, __LINE__, Kp, Ki, Kd, sensor_data->sensor_tracking);

	cur_interal_Err =(int) (sensor_data->sensor_reading - sensor_data->sensor_tracking);
	sensor_data->intergral_i = sensor_data->intergral_i % sample_n;
	sensor_data->interal_Err[sensor_data->intergral_i] = cur_interal_Err;
	sensor_data->intergral_i=(sensor_data->intergral_i+1) % sample_n;
	total_integral_error = 0;

	for(i=0; i<sample_n; i++)
		total_integral_error += sensor_data->interal_Err[i] ;

	pid_value = (int)((double) Kp * cur_interal_Err +  (double)Ki * total_integral_error + (double)Kd * (cur_interal_Err - sensor_data->last_error));
	//pwm_speed = pid_value + g_FanSpeed;

	if (closeloop_first_time <= 10) {
		if (current_fanspeed == 100)
			current_fanspeed = 40;
		else {
			closeloop_first_time +=1;
		}
	}

	pwm_speed = pid_value + current_fanspeed;

	g_fan_para_shm->closeloop_param[index].pid_value = pid_value;
	g_fan_para_shm->closeloop_param[index].closeloop_speed = pwm_speed;

	printf("[FAN_ALGORITHM][%s, %d] [Closeloop pid_value] %d; [Closeloop Calculate Fan Speed]: %d\n", __FUNCTION__, __LINE__, pid_value, pwm_speed);

	if(pwm_speed > 100)
		pwm_speed = 100;

	if(pwm_speed < 0)
		pwm_speed = 0;

	sensor_data->last_error = (int) cur_interal_Err;

	//if (g_Closeloopspeed < pwm_speed)
	//	g_Closeloopspeed = pwm_speed;
	g_Closeloopspeed = pwm_speed;
	closeloop_fanspeed = pwm_speed;

	if (sensor_data->sensor_reading>=sensor_data->warning_temp)
		g_Closeloopspeed = 100;

	return 1;
}

static int calculate_openloop (int sensorreading)
{
	int speed = 0;

	if (sensorreading<=0) {
		g_Openloopspeed = 0;
		return 0;
	}

	sensorreading=sensorreading+g_fan_para_shm->openloop_sensor_offset;
	sensorreading+=7; //because temp4 getsensors reading already offset (-7)


	if (sensorreading >= g_UpAmb) {
		speed = g_HighSpeed;
	} else if (sensorreading <= g_LowAmb) {
		speed = g_LowSpeed;
	} else {
		speed = ( g_ParamA * sensorreading * sensorreading ) + ( g_ParamB * sensorreading ) + g_ParamC;
		speed = (speed > g_HighSpeed)? g_HighSpeed : ((speed < g_LowSpeed)? g_LowSpeed : speed);
	}

	g_fan_para_shm->openloop_speed = speed;

	printf("[FAN_ALGORITHM][%s, %d] [Openloop Parameters: g_UpAmb, g_LowAmb, A, B, C] %d ,%d, %f, %f, %f; [Openloop Calculate Fan Speed]: %d\n", __FUNCTION__, __LINE__,
	       g_UpAmb, g_LowAmb, g_ParamA, g_ParamB, g_ParamC, speed);

	g_Openloopspeed = speed;
	return 1;
}

static int get_sensor_reading(sd_bus *bus, char *obj_path, int *sensor_reading, struct st_fan_obj_path_info *fan_obj)
{
	sd_bus_error bus_error = SD_BUS_ERROR_NULL;
	sd_bus_message *response = NULL;
	int rc;

	*sensor_reading = 0;

	if (strlen(fan_obj->service_bus) <= 0 || strlen(fan_obj->service_inf) <= 0 || strlen(obj_path) <= 0)
		return -1;

	rc = sd_bus_call_method(bus,
				fan_obj->service_bus,
				obj_path,
				fan_obj->service_inf,
				"getValue",
				&bus_error,
				&response,
				NULL);

	if(rc < 0) {
		fprintf(stderr, "obj_path: %s Failed to get temperature from dbus: %s\n", obj_path, bus_error.message);
	} else {
		rc = sd_bus_message_read(response,"v", "i", sensor_reading);
		if (rc < 0)
			fprintf(stderr, "obj_path: %s Failed to parse response message:[%s]\n",obj_path, strerror(-rc));
	}

	sd_bus_error_free(&bus_error);
	response = sd_bus_message_unref(response);

	return rc;
}

static int get_max_sensor_reading(sd_bus *bus, struct st_fan_obj_path_info *fan_obj)
{
	int i;
	int rc;
	int sensor_reading;
	int max_value = 0;

	for(i=0; i<fan_obj->size; i++) {
		rc = get_sensor_reading(bus, fan_obj->path[i], &sensor_reading, fan_obj);
		if (rc >= 0)
			max_value = (max_value < sensor_reading)? sensor_reading : max_value;
	}

	return max_value;
}


static int get_sensor_reading_Fan(sd_bus *bus, char *obj_path, int *sensor_reading, struct st_fan_obj_path_info *fan_obj)
{
	sd_bus_error bus_error = SD_BUS_ERROR_NULL;
	sd_bus_message *response = NULL;
	int rc;

	*sensor_reading = 0;

	if (strlen(fan_obj->service_bus) <= 0 || strlen(fan_obj->service_inf) <= 0 || strlen(obj_path) <= 0)
		return -1;

	rc = sd_bus_call_method(bus,
				fan_obj->service_bus,
				obj_path,
				fan_obj->service_inf,
				"getValue_Fan",
				&bus_error,
				&response,
				NULL);


	if(rc < 0) {
		fprintf(stderr, "obj_path: %s Failed to get temperature from dbus: %s\n", obj_path, bus_error.message);
	} else {
		rc = sd_bus_message_read(response, "i", sensor_reading);
		if (rc < 0)
			fprintf(stderr, "obj_path: %s Failed to parse response message:[%s]\n",obj_path, strerror(-rc));
	}

	sd_bus_error_free(&bus_error);
	response = sd_bus_message_unref(response);

	return rc;
}

static int get_max_sensor_reading_Fan(sd_bus *bus, struct st_fan_obj_path_info *fan_obj)
{
	int i;
	int rc;
	int sensor_reading;
	int max_value = 0;

	for(i=0; i<fan_obj->size; i++) {
		rc = get_sensor_reading_Fan(bus, fan_obj->path[i], &sensor_reading, fan_obj);
		if (rc >= 0)
			max_value = (max_value < sensor_reading)? sensor_reading : max_value;
	}

	return max_value;
}

static void check_change_closeloop_params(struct st_closeloop_obj_data *sensor_data)
{
	int wait_times = 0;
	int index;

	if (g_fan_para_shm == NULL)
		return ;

	if (g_fan_para_shm->flag_closeloop == 1)
		return ; //do nothing

	while (g_fan_para_shm->flag_closeloop == 3 && wait_times<MAX_WAIT_TIMEOUT)
		wait_times++;

	if (g_fan_para_shm->flag_closeloop == 2) {
		index = sensor_data->index;
		sensor_data->Kp = g_fan_para_shm->closeloop_param[index].Kp;
		sensor_data->Ki = g_fan_para_shm->closeloop_param[index].Ki;
		sensor_data->Kd = g_fan_para_shm->closeloop_param[index].Kd;
		sensor_data->sensor_tracking = g_fan_para_shm->closeloop_param[index].sensor_tracking;
		sensor_data->warning_temp = g_fan_para_shm->closeloop_param[index].warning_temp;
		g_fan_para_shm->flag_closeloop = 1;
	}
}

static void check_change_openloop_params()
{
	int wait_times = 0;

	if (g_fan_para_shm == NULL)
		return ;

	if (g_fan_para_shm->flag_openloop == 1)
		return ; //do nothing

	while (g_fan_para_shm->flag_openloop == 3 && wait_times<MAX_WAIT_TIMEOUT)
		wait_times++;

	if (g_fan_para_shm->flag_openloop == 2) {
		g_ParamA = g_fan_para_shm->g_ParamA;
		g_ParamB = g_fan_para_shm->g_ParamB;
		g_ParamC = g_fan_para_shm->g_ParamC;
		g_LowAmb = g_fan_para_shm->g_LowAmb;
		g_UpAmb = g_fan_para_shm->g_UpAmb;
		g_LowSpeed = g_fan_para_shm->g_LowSpeed;
		g_HighSpeed = g_fan_para_shm->g_HighSpeed;
		g_fan_para_shm->flag_openloop = 1;
	}
}


static int fan_control_algorithm_monitor(void)
{
	sd_bus *bus = NULL;
	sd_bus_error bus_error = SD_BUS_ERROR_NULL;
	sd_bus_message *response = NULL;
	int rc = 0, i = 0, offset = 0;
	int Fan_tach, FinalFanSpeed = 255;
	int Power_state = 0, fan_led_port0 = 0xFF, fan_led_port1 = 0xFF;
	char fan_presence[MAX_SENSOR_NUM] = {0}, fan_presence_previous[MAX_SENSOR_NUM] = {0};
	struct st_fan_obj_path_info *t_header = NULL;
	struct st_closeloop_obj_data *t_closeloop_data = NULL;
	int closeloop_reading = 0, openloop_reading = 0;
	int current_fanspeed = 0;
	int first_time_set = 0;

	do {
		/* Connect to the user bus this time */
		rc = sd_bus_open_system(&bus);
		if(rc < 0) {
			fprintf(stderr, "Failed to connect to system bus for fan_algorithm: %s\n", strerror(-rc));
			bus = sd_bus_flush_close_unref(bus);
			sleep(1);
		}
	} while (rc < 0);

	initial_fan_config(bus);

	while (1) {
		rc = sd_bus_call_method(bus,
					g_PowerObjPath.service_bus,
					g_PowerObjPath.path[0],
					g_PowerObjPath.service_inf,
					"getPowerState",
					&bus_error,
					&response,
					NULL);
		if(rc < 0) {
			fprintf(stderr, "Failed to get power state from dbus: %s\n", bus_error.message);
			goto finish;
		}

		rc = sd_bus_message_read(response, "i", &Power_state);
		if (rc < 0 ) {
			fprintf(stderr, "Failed to parse GetPowerState response message:[%s]\n", strerror(-rc));
			goto finish;
		}
		sd_bus_error_free(&bus_error);
		response = sd_bus_message_unref(response);

		if (Power_state == 1 ) {

			current_fanspeed = get_max_sensor_reading_Fan(bus, &g_FanSpeedObjPath);
			g_fan_para_shm->current_speed = current_fanspeed;
			printf("[FAN_ALGORITHM][Current FanSpeed value] :%d\n", current_fanspeed);
			if (current_fanspeed <0)
				current_fanspeed = 0;
			else {
				current_fanspeed = current_fanspeed*100;
				current_fanspeed =(int) current_fanspeed / 255;
			}
			if (current_fanspeed > 100)
				current_fanspeed = 100;

			closeloop_reading = 0;
			t_header = g_Closeloop_Header;
			while (t_header != NULL) {
				t_closeloop_data = (struct st_closeloop_obj_data *) t_header->obj_data;

				if (t_closeloop_data != NULL) {
					t_closeloop_data->sensor_reading = get_max_sensor_reading(bus, t_header);
					g_fan_para_shm->closeloop_param[t_closeloop_data->index].closeloop_sensor_reading = t_closeloop_data->sensor_reading;
					if (t_closeloop_data->sensor_reading == 0)
						t_closeloop_data->sensor_reading = 30;
					check_change_closeloop_params(t_closeloop_data);
					calculate_closeloop(t_closeloop_data, current_fanspeed);
					closeloop_reading = (closeloop_reading<t_closeloop_data->sensor_reading)? t_closeloop_data->sensor_reading:closeloop_reading;
					if (closeloop_reading == 0)
						closeloop_reading = 30;
				}
				t_header = t_header->next;
			}

			check_change_openloop_params();
			openloop_reading = 0;
			t_header = g_Openloop_Header;
			while (t_header != NULL) {
				int t_reaing;
				t_reaing = get_max_sensor_reading(bus, t_header);
				g_fan_para_shm->openloop_sensor_reading = t_reaing;
				calculate_openloop(t_reaing);
				openloop_reading = (openloop_reading<t_reaing? t_reaing:openloop_reading);
				t_header = t_header->next;
			}

			if (closeloop_reading > 0 && openloop_reading > 0) {
				if(g_Openloopspeed > g_Closeloopspeed) {
					g_FanSpeed = g_Openloopspeed;
				} else {
					g_FanSpeed = g_Closeloopspeed;
				}

				if (first_time_set == 0 && g_Openloopspeed>0 && g_Closeloopspeed>0) {
					if (g_Closeloopspeed == 100)
						g_FanSpeed = g_Openloopspeed;
					first_time_set = 1;
				}


				FinalFanSpeed = g_FanSpeed * 255;
				FinalFanSpeed = FinalFanSpeed / 100;

				if(g_FanSpeed > g_fanled_speed_limit) {
					fan_led_port0 = FAN_LED_PORT0_ALL_BLUE;
					fan_led_port1 = FAN_LED_PORT1_ALL_BLUE;
				} else {
					fan_led_port0 = FAN_LED_PORT0_ALL_RED;
					fan_led_port1 = FAN_LED_PORT1_ALL_RED;
				}
			} else {
				FinalFanSpeed = 255;
				fan_led_port0 = FAN_LED_PORT0_ALL_BLUE;
				fan_led_port1 = FAN_LED_PORT1_ALL_BLUE;
			}
			for(i=0; i<g_FanInputObjPath.size; i++) {
				rc = get_sensor_reading(bus, g_FanInputObjPath.path[i], &Fan_tach, &g_FanInputObjPath);
				printf("[FAN_ALGORITHM][Fan Tach: %d] value:%d\n", i,  Fan_tach);
				if (rc < 0)
					Fan_tach = 0;

				if (Fan_tach == 0) {
					FinalFanSpeed = 255;
					if (i <= 3) { //FAN 1 & 2
						offset = i / 2 * 2;
						fan_led_port1 &= ~(PORT1_FAN_LED_RED_MASK >> offset); //turn on red led
						fan_led_port1 |= PORT1_FAN_LED_BLUE_MASK >> offset; //turn off blue led
					} else { //FAN 3~6
						offset = (i - 4) / 2 * 2;
						fan_led_port0 &= ~(PORT0_FAN_LED_RED_MASK << offset); //turn on red led
						fan_led_port0 |= PORT0_FAN_LED_BLUE_MASK << offset; //turn off blue led
					}
				} else {
					fan_presence[i/2] = 1;
				}
			}
		} else {
			FinalFanSpeed = 255;
			closeloop_first_time = 0;
			first_time_set = 0;
			fan_led_port0 = FAN_LED_OFF;
			fan_led_port1 = FAN_LED_OFF;
		}

		set_fanled(fan_led_port0,fan_led_port1, 0);

		if (g_fan_para_shm != NULL) {
			if (FinalFanSpeed < g_fan_para_shm->min_fanspeed)
				FinalFanSpeed = g_fan_para_shm->min_fanspeed;
			else if (FinalFanSpeed > g_fan_para_shm->max_fanspeed)
				FinalFanSpeed = g_fan_para_shm->max_fanspeed;
		}

		printf("[FAN_ALGORITHM][Set FanSpeed value] :%d\n", FinalFanSpeed);
		for(i=0; i<g_FanSpeedObjPath.size; i++) {
			rc = sd_bus_call_method(bus,
						g_FanSpeedObjPath.service_bus,
						g_FanSpeedObjPath.path[i],			// Object path
						g_FanSpeedObjPath.service_inf,
						"setValue_Fan",
						&bus_error,
						&response,
						"i",
						FinalFanSpeed);
			if(rc < 0)
				fprintf(stderr, "Failed to adjust fan speed via dbus: %s\n", bus_error.message);
			sd_bus_error_free(&bus_error);
			response = sd_bus_message_unref(response);
		}

		for(i=0; i<g_FanModuleObjPath.size; i++) {
			if (fan_presence[i] == fan_presence_previous[i])
				continue;

			rc = sd_bus_call_method(bus,
						"org.openbmc.Inventory",
						g_FanModuleObjPath.path[i],
						"org.openbmc.InventoryItem",
						"setPresent",
						&bus_error,
						&response,
						"s",
						(fan_presence[i] == 1 ? "True" : "False"));
			if(rc < 0)
				fprintf(stderr, "Failed to update fan presence via dbus: %s\n", bus_error.message);
			sd_bus_error_free(&bus_error);
			response = sd_bus_message_unref(response);
		}

finish:
		sd_bus_error_free(&bus_error);
		response = sd_bus_message_unref(response);
		sd_bus_flush(bus);
		memcpy(fan_presence_previous, fan_presence, sizeof(fan_presence));
		memset(fan_presence, 0, sizeof(fan_presence));
		sleep(1);
	}
	bus = sd_bus_flush_close_unref(bus);
	freeall_fan_obj(&g_Closeloop_Header);
	freeall_fan_obj(&g_Openloop_Header);
	shmdt(g_shm_addr);
	shmctl(g_shm_id , IPC_RMID , NULL);
	return rc < 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}

static int get_dbus_fan_parameters(sd_bus *bus , char *request_param , int *reponse_len, char reponse_data[50][200])
{
	sd_bus_error bus_error = SD_BUS_ERROR_NULL;
	sd_bus_message *response = NULL;
	int rc = 0;
	const char*  response_param;

	*reponse_len = 0; //clear reponse_len

	rc = sd_bus_call_method(bus,
				"org.openbmc.managers.System",
				"/org/openbmc/managers/System",
				"org.openbmc.managers.System",
				"getFanControlParams",
				&bus_error,
				&response,
				"s", request_param);
	if(rc < 0) {
		printf("%s, %d response message:[%s]\n", __FUNCTION__, __LINE__, strerror(-rc));
	} else {
		rc = sd_bus_message_read(response, "s", &response_param);
		if (rc < 0 ) {
			fprintf(stderr, "Failed to parse response message:[%s]\n", strerror(-rc));
			return rc;
		}

		int stard_idx = 0, end_idx = 0;
		int str_len = 0;
		while (response_param[end_idx]!=0) {
			if (response_param[end_idx] == ';') { // ';' means to indentify every data token
				if (stard_idx < end_idx) {
					str_len = end_idx - stard_idx;
					if (str_len < MAX_PATH_LEN) {
						memcpy(reponse_data[*reponse_len], response_param+stard_idx, str_len);
						reponse_data[*reponse_len][str_len] = '\0';
						*reponse_len=*reponse_len+1;
					} else
						printf("Error:%s[%d], parse string exceds length:%d, str_len:%d\n", __FUNCTION__, __LINE__, MAX_PATH_LEN, str_len);
				}
				stard_idx=end_idx+1;
			}
			end_idx++;
		}
	}
	sd_bus_error_free(&bus_error);
	response = sd_bus_message_unref(response);
	return rc;
}

static int initial_fan_config(sd_bus *bus)
{
	int reponse_len = 0;
	char reponse_data[50][200];
	int i;
	int obj_count = 0;
	char *p;
	int index;

	get_dbus_fan_parameters(bus, "FAN_INPUT_OBJ", &reponse_len, reponse_data);
	g_FanInputObjPath.size = reponse_len;
	for (i = 0; i<reponse_len; i+=2) {
		strcpy(g_FanInputObjPath.path[i], reponse_data[i]);
	}
	get_dbus_fan_parameters(bus, "FAN_DBUS_INTF_LOOKUP#FAN_INPUT_OBJ", &reponse_len, reponse_data);
	if (reponse_len == 2) {
		strcpy(g_FanInputObjPath.service_bus , reponse_data[0]);
		strcpy(g_FanInputObjPath.service_inf , reponse_data[1]);
	}

	get_dbus_fan_parameters(bus, "FAN_OUTPUT_OBJ", &reponse_len, reponse_data);
	g_FanSpeedObjPath.size = reponse_len;
	for (i = 0; i<reponse_len; i++) {
		strcpy(g_FanSpeedObjPath.path[i], reponse_data[i]);
	}
	get_dbus_fan_parameters(bus, "FAN_DBUS_INTF_LOOKUP#FAN_OUTPUT_OBJ", &reponse_len, reponse_data);
	if (reponse_len == 2) {
		strcpy(g_FanSpeedObjPath.service_bus , reponse_data[0]);
		strcpy(g_FanSpeedObjPath.service_inf , reponse_data[1]);
	}

	get_dbus_fan_parameters(bus, "OPEN_LOOP_PARAM", &reponse_len, reponse_data);
	g_ParamA = atof(reponse_data[0]);
	g_ParamB = atof(reponse_data[1]);
	g_ParamC = atof(reponse_data[2]);
	g_LowAmb = atoi(reponse_data[3]);
	g_UpAmb = atoi(reponse_data[4]);
	g_LowSpeed = atoi(reponse_data[5]);
	g_HighSpeed = atoi(reponse_data[6]);

	g_fan_para_shm->g_ParamA= g_ParamA;
	g_fan_para_shm->g_ParamB= g_ParamB;
	g_fan_para_shm->g_ParamC= g_ParamC;
	g_fan_para_shm->g_LowAmb= g_LowAmb;
	g_fan_para_shm->g_UpAmb= g_UpAmb;
	g_fan_para_shm->g_LowSpeed= g_LowSpeed;
	g_fan_para_shm->g_HighSpeed= g_HighSpeed;
	g_fan_para_shm->flag_openloop= 1;


	obj_count = 1;
	struct st_closeloop_obj_data *t_closeloop_data = NULL;
	while (1) {
		char prefix_closeloop[100];
		struct st_fan_obj_path_info *t_fan_obj = NULL;

		prefix_closeloop[0] = 0;
		sprintf(prefix_closeloop, "CLOSE_LOOP_GROUPS_%d", obj_count);
		get_dbus_fan_parameters(bus, prefix_closeloop, &reponse_len, reponse_data);
		if (reponse_len <= 2)
			break;

		t_fan_obj =(struct st_fan_obj_path_info *) malloc(sizeof(struct st_fan_obj_path_info));

		t_fan_obj->size = reponse_len;
		for (i = 0; i<reponse_len ; i++)
			strcpy(t_fan_obj->path[i], reponse_data[i]);

		prefix_closeloop[0] = 0;
		sprintf(prefix_closeloop, "FAN_DBUS_INTF_LOOKUP#CLOSE_LOOP_GROUPS_%d", obj_count);
		get_dbus_fan_parameters(bus, prefix_closeloop, &reponse_len, reponse_data);
		if (reponse_len == 2) {
			strcpy(t_fan_obj->service_bus , reponse_data[0]);
			strcpy(t_fan_obj->service_inf , reponse_data[1]);
		} else {
			free(t_fan_obj);
			break;
		}

		prefix_closeloop[0] = 0;
		sprintf(prefix_closeloop, "CLOSE_LOOP_PARAM_%d", obj_count);
		get_dbus_fan_parameters(bus, prefix_closeloop, &reponse_len, reponse_data);
		if (reponse_len > 0) {
			t_closeloop_data = (struct st_closeloop_obj_data *) malloc(sizeof(struct st_closeloop_obj_data));
			index = obj_count -1;
			t_closeloop_data->index = index;
			t_closeloop_data->Kp = (double)atof(reponse_data[0]);
			t_closeloop_data->Ki = (double)atof(reponse_data[1]);
			t_closeloop_data->Kd = (double)atof(reponse_data[2]);
			t_closeloop_data->sensor_tracking = atoi(reponse_data[3]);
			t_closeloop_data->warning_temp = atoi(reponse_data[4]);

			g_fan_para_shm->closeloop_param[index].Kp = t_closeloop_data->Kp;
			g_fan_para_shm->closeloop_param[index].Ki = t_closeloop_data->Ki;
			g_fan_para_shm->closeloop_param[index].Kd = t_closeloop_data->Kd;
			g_fan_para_shm->closeloop_param[index].sensor_tracking = t_closeloop_data->sensor_tracking;
			g_fan_para_shm->closeloop_param[index].warning_temp = t_closeloop_data->warning_temp;
			g_fan_para_shm->flag_closeloop = 1;

			for (i = 0 ; i<100; i++)
				t_closeloop_data->interal_Err[i] = 0;
			t_closeloop_data->last_error = 0;
			t_closeloop_data->intergral_i = 0;
		}
		t_fan_obj->obj_data = (void*)t_closeloop_data;
		

		push_fan_obj(&g_Closeloop_Header, t_fan_obj);
		obj_count++;
	}
	g_fan_para_shm->closeloop_count =  obj_count-1;

	obj_count = 1;
	while (1) {
		char prefix_openloop[100];
		struct st_fan_obj_path_info *t_fan_obj = NULL;

		prefix_openloop[0] = 0;
		sprintf(prefix_openloop, "OPEN_LOOP_GROUPS_%d", obj_count);
		get_dbus_fan_parameters(bus, prefix_openloop, &reponse_len, reponse_data);
		if (reponse_len == 0)
			break;

		t_fan_obj =(struct st_fan_obj_path_info *) malloc(sizeof(struct st_fan_obj_path_info));

		t_fan_obj->size = reponse_len;
		for (i = 0; i<reponse_len ; i++)
			strcpy(t_fan_obj->path[i], reponse_data[i]);

		prefix_openloop[0] = 0;
		sprintf(prefix_openloop, "FAN_DBUS_INTF_LOOKUP#OPEN_LOOP_GROUPS_%d", obj_count);
		get_dbus_fan_parameters(bus, prefix_openloop, &reponse_len, reponse_data);
		if (reponse_len == 2) {
			strcpy(t_fan_obj->service_bus , reponse_data[0]);
			strcpy(t_fan_obj->service_inf , reponse_data[1]);
		} else {
			free(t_fan_obj);
			break;
		}

		push_fan_obj(&g_Openloop_Header, t_fan_obj);

		obj_count++;
	}

	get_dbus_fan_parameters(bus, "FAN_LED_OFF", &reponse_len, reponse_data);
	FAN_LED_OFF = reponse_len > 0? strtoul(reponse_data[0], &p, 16): FAN_LED_OFF;

	get_dbus_fan_parameters(bus, "FAN_LED_PORT0_ALL_BLUE", &reponse_len, reponse_data);
	FAN_LED_PORT0_ALL_BLUE = reponse_len > 0? strtoul(reponse_data[0], &p, 16): FAN_LED_PORT0_ALL_BLUE;

	get_dbus_fan_parameters(bus, "FAN_LED_PORT1_ALL_BLUE", &reponse_len, reponse_data);
	FAN_LED_PORT1_ALL_BLUE = reponse_len > 0? strtoul(reponse_data[0], &p, 16): FAN_LED_PORT1_ALL_BLUE;

	get_dbus_fan_parameters(bus, "FAN_LED_PORT0_ALL_RED", &reponse_len, reponse_data);
	FAN_LED_PORT0_ALL_RED = reponse_len > 0? strtoul(reponse_data[0], &p, 16): FAN_LED_PORT0_ALL_RED;

	get_dbus_fan_parameters(bus, "FAN_LED_PORT1_ALL_RED", &reponse_len, reponse_data);
	FAN_LED_PORT1_ALL_RED = reponse_len > 0? strtoul(reponse_data[0], &p, 16): FAN_LED_PORT1_ALL_RED;

	get_dbus_fan_parameters(bus, "PORT0_FAN_LED_RED_MASK", &reponse_len, reponse_data);
	PORT0_FAN_LED_RED_MASK = reponse_len > 0? strtoul(reponse_data[0], &p, 16): PORT0_FAN_LED_RED_MASK;

	get_dbus_fan_parameters(bus, "PORT0_FAN_LED_BLUE_MASK", &reponse_len, reponse_data);
	PORT0_FAN_LED_BLUE_MASK = reponse_len > 0? strtoul(reponse_data[0], &p, 16): PORT0_FAN_LED_BLUE_MASK;

	get_dbus_fan_parameters(bus, "PORT1_FAN_LED_RED_MASK", &reponse_len, reponse_data);
	PORT1_FAN_LED_RED_MASK = reponse_len > 0? strtoul(reponse_data[0], &p, 16): PORT1_FAN_LED_RED_MASK;

	get_dbus_fan_parameters(bus, "PORT1_FAN_LED_BLUE_MASK", &reponse_len, reponse_data);
	PORT1_FAN_LED_BLUE_MASK = reponse_len > 0? strtoul(reponse_data[0], &p, 16): PORT1_FAN_LED_BLUE_MASK;

	get_dbus_fan_parameters(bus, "FAN_LED_SPEED_LIMIT", &reponse_len, reponse_data);
	g_fanled_speed_limit = reponse_len > 0? atoi(reponse_data[0]): g_fanled_speed_limit;

	get_dbus_fan_parameters(bus, "FAN_LED_I2C_BUS", &reponse_len, reponse_data);
	if (reponse_len > 0)
		strcpy(g_FanLed_I2CBus, reponse_data[0]);

	get_dbus_fan_parameters(bus, "FAN_LED_I2C_SLAVE_ADDRESS", &reponse_len, reponse_data);
	g_FanLed_SlaveAddr = reponse_len > 0? strtoul(reponse_data[0], &p, 16): g_FanLed_SlaveAddr;

	//Refere to FRU_INSTANCES in config/.py file to search inventory item object path with keywords: 'fan'
	get_dbus_fan_parameters(bus, "INVENTORY_FAN", &reponse_len, reponse_data);
	g_FanModuleObjPath.size = reponse_len;
	for (i = 0; i<reponse_len; i++) {
		strcpy(g_FanModuleObjPath.path[i], reponse_data[i]);
	}

	get_dbus_fan_parameters(bus, "CHASSIS_POWER_STATE", &reponse_len, reponse_data);
	if (reponse_len > 0) {
		strcpy(g_PowerObjPath.path[0], reponse_data[0]);
		g_PowerObjPath.size = 1;
	}
	get_dbus_fan_parameters(bus, "FAN_DBUS_INTF_LOOKUP#CHASSIS_POWER_STATE", &reponse_len, reponse_data);
	if (reponse_len == 2) {
		strcpy(g_PowerObjPath.service_bus , reponse_data[0]);
		strcpy(g_PowerObjPath.service_inf , reponse_data[1]);
	}
}

static void inital_fan_pid_shm()
{
	key_t key = ftok(FAN_SHM_PATH, FAN_SHM_KEY);
	int i;

	g_shm_id = shmget(key, sizeof(struct st_fan_parameter), (IPC_CREAT | 0666));
	if (g_shm_id < 0) {
		printf("Error: shmid \n");
		return ;
	}
	g_shm_addr =  shmat(g_shm_id, NULL, 0);
	if (g_shm_addr == (char *) -1) {
		printf("Error: shmat \n");
		return ;
	}

	g_fan_para_shm = (struct st_fan_parameter *) g_shm_addr;
	if (g_fan_para_shm != NULL) {
		g_fan_para_shm->flag_closeloop = 0;
		g_fan_para_shm->flag_openloop = 0;
		g_fan_para_shm->max_fanspeed = 255;
		g_fan_para_shm->min_fanspeed = 0;
		for (i = 0 ; i<5; i++) {
			g_fan_para_shm->closeloop_param[i].closeloop_sensor_reading = 0;
			g_fan_para_shm->closeloop_param[i].sample_n = SAMPLING_N;
		}
		g_fan_para_shm->closeloop_count = 0;
		g_fan_para_shm->openloop_sensor_offset = -7;
	}
}

int main(int argc, char *argv[])
{
	inital_fan_pid_shm();
	return fan_control_algorithm_monitor();
}


