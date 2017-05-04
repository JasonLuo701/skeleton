#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <dirent.h>
#include <systemd/sd-bus.h>
#include <linux/i2c-dev-user.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sdbus_property.h>


#define MAX_I2C_DEV_LEN 32
#define GPU_ACCESS_SUCCESS_RETURN 0x1f
#define MAX_PXE_NUM (4)

#define PXE_TEMP_PATH "/tmp/pxe"
#define PXE_SERIAL_LEN (8)

enum {
	EM_PXE_DEVICE_1 = 0,
	EM_PXE_DEVICE_2,
	EM_PXE_DEVICE_3,
	EM_PXE_DEVICE_4,
	EM_PXE_DEVICE_5,
	EM_PXE_DEVICE_6,
	EM_PXE_DEVICE_7,
	EM_PXE_DEVICE_8,
};

enum {
	EM_PXE_CMD_TEMP_DISABLE_CTL = 0,
	EM_PXE_CMD_TEMP_ENABLE_CTL,
	EM_PXE_CMD_TEMP_READ,
	EM_PXE_CMD_UPPER_SERIAL_READ,
	EM_PXE_CMD_LOWER_SERIAL_READ,
	EM_PXE_CMD_MAX
};

typedef struct {
	__u32 serial_count;
	__u8 serial_data[PXE_SERIAL_LEN];
} pxe_device_serial;

typedef struct {
	__u8 bus_no;

	__u8 slave;

	__u8 device_index;

	pxe_device_serial serial;

} pxe_device_mapping;

pxe_device_mapping pxe_device_bus[MAX_PXE_NUM] = {
	{16, 0x5d, EM_PXE_DEVICE_1, {0, {0}} },
	{17, 0x5d, EM_PXE_DEVICE_2, {0, {0}} },
	{18, 0x5d, EM_PXE_DEVICE_3, {0, {0}} },
	{19, 0x5d, EM_PXE_DEVICE_4, {0, {0}} },
};

typedef struct {
	int len;
	__u8 data[256];
} i2c_cmd_data;

typedef struct {
	int cmd;
	i2c_cmd_data write_cmd;
	i2c_cmd_data read_cmd;
} pxe_device_i2c_cmd;


pxe_device_i2c_cmd pxe_device_cmd_tab[EM_PXE_CMD_MAX] = {
	{
		EM_PXE_CMD_TEMP_DISABLE_CTL,
		{8, {0x3, 0x0, 0x3e, 0xeb, 0x00, 0x00, 0x00, 0x00}},
		{-1,{0x0}}
	},
	{
		EM_PXE_CMD_TEMP_ENABLE_CTL,
		{8, {0x3, 0x0, 0x3e, 0xeb, 0x00, 0x00, 0x00, 0x80}},
		{-1,{0x0}}
	},
	{
		EM_PXE_CMD_TEMP_ENABLE_CTL,
		{4, {0x4, 0x0, 0x3e, 0xeb}},
		{4, {0x0}}
	},
	{
		EM_PXE_CMD_LOWER_SERIAL_READ,
		{4, {0x4, 0x0, 0x3c, 0x41}},
		{4, {0x0}}
	},
	{
		EM_PXE_CMD_UPPER_SERIAL_READ,
		{4, {0x4, 0x0, 0x3c, 0x42}},
		{4, {0x0}}
	},
};


#define PMBUS_DELAY usleep(400*1000)
#define I2C_CLIENT_PEC          0x04    /* Use Packet Error Checking */
#define I2C_M_RECV_LEN          0x0400  /* length will be first received byte */
#include "i2c-dev.h"


static int g_use_pec = 0;

static int i2c_io(int fd, int slave_addr, int write_len , __u8 *write_data_bytes, int read_len, __u8 *read_data_bytes)
{
	struct i2c_rdwr_ioctl_data data;
	struct i2c_msg msg[2];
	int n_msg = 0;
	int rc;
	int i;

	memset(&msg, 0, sizeof(msg));

	if (write_len > 0) {
		msg[n_msg].addr = slave_addr;
		msg[n_msg].flags = (g_use_pec) ? I2C_CLIENT_PEC : 0;
		msg[n_msg].len = write_len ;
		msg[n_msg].buf = write_data_bytes;
		n_msg++;
	}

	if (read_len>=0) {
		msg[n_msg].addr = slave_addr;
		msg[n_msg].flags = I2C_M_RD
				   | ((g_use_pec) ? I2C_CLIENT_PEC : 0)
				   | ((read_len == 0) ? I2C_M_RECV_LEN : 0);
		/*
		 * In case of g_n_read is 0, block length will be added by
		 * the underlying bus driver.
		 */
		msg[n_msg].len = (read_len) ? read_len : 256;
		msg[n_msg].buf = read_data_bytes ;
		n_msg++;
	}

	data.msgs = msg;
	data.nmsgs = n_msg;

	rc = ioctl(fd, I2C_RDWR, &data);
	if (rc < 0) {
		printf("Failed to do raw io\n");
		return -1;
	}
	return 0;
}

static i2c_raw_access(int i2c_bus, int i2c_addr ,int write_len , __u8 *write_data_bytes, int read_len, __u8 *read_data_bytes)
{
	int fd;
	char filename[MAX_I2C_DEV_LEN] = {0};
	int rc=-1;
	int retry_gpu = 5;
	int count = 0;
	int r_count = 0;
	int i;

	sprintf(filename,"/dev/i2c-%d",i2c_bus);
	fd = open(filename,O_RDWR);

	if (fd == -1) {
		fprintf(stderr, "Failed to open i2c device %s, error:%s", filename, strerror(errno));
		return rc;
	}

	rc = ioctl(fd,I2C_SLAVE,i2c_addr);
	if(rc < 0) {
		fprintf(stderr, "Failed to do iotcl I2C_SLAVE, error:%s\n", strerror(errno));
		close(fd);
		return rc;
	}

	if (read_len>0)
		memset(read_data_bytes, 0x0, read_len);

	rc = i2c_io(fd, i2c_addr, write_len, write_data_bytes, read_len, read_data_bytes);

	close(fd);

	return rc;

}

#define E (10)

double pow(double n, double p)
{
	int i;
	double rc = 1.0;

	if (p >0) {
		for (i = 0; i<p; i++)
			rc=rc*n;
	} else if(p<0) {
		for (i=p; i<0; i++)
			rc = rc / n;
	}

	return rc;
}

double calculate_pxe_temp(unsigned int N)
{
	double result = 0.0;
	result = (-4.5636)*pow(E, -11)*pow(N,4) + (1.4331)*pow(E, -7)*pow(N,3) + (-2.3557)*pow(E, -4)*pow(N,2) + (0.32597*N) + (-53.509);
	return result;

}


#define PXE_TEMP_SENSOR_DATA_MASK (0x3FF)

unsigned int get_temperature_sensor_data(int len, char *data)
{
	unsigned int sd;

	sd = data[0]<<8 | data[1];

	return (sd & PXE_TEMP_SENSOR_DATA_MASK);
}


void write_file_pex(int pxe_idx, double data, char *sub_name)
{
	char f_path[128];
	char sys_cmd[256];

	sprintf(f_path , "%s/pxe%d_%s", PXE_TEMP_PATH, pxe_idx, sub_name);
	sprintf(sys_cmd, "echo %d > %s", (int)data, f_path);
	system(sys_cmd);
}

void function_get_pxe_temp_data(int pxe_idx)
{
	pxe_device_i2c_cmd *i2c_cmd;
	int i2c_bus;
	int i2c_addr;
	int ret;
	int i;
	char *rx_data;
	int rx_len = 0;
	unsigned int temp_sensor_data = 0;
	double real_temp_data = 0.0;

	i2c_bus = pxe_device_bus[pxe_idx].bus_no;
	i2c_addr = pxe_device_bus[pxe_idx].slave;

	i2c_cmd = &pxe_device_cmd_tab[EM_PXE_CMD_TEMP_DISABLE_CTL];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl cmd:%d, ret:%d\n", i2c_cmd->cmd, ret);
		return ;
	}

	i2c_cmd = &pxe_device_cmd_tab[EM_PXE_CMD_TEMP_ENABLE_CTL];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl cmd:%d, ret=%d\n", i2c_cmd->cmd, ret);
		return ;
	}

	i2c_cmd = &pxe_device_cmd_tab[EM_PXE_CMD_TEMP_READ];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl cmd:%d, ret:%d\n", i2c_cmd->cmd, ret);
		return ;
	}

	rx_len = i2c_cmd->read_cmd.len;
	rx_data = i2c_cmd->read_cmd.data;

	if ((rx_data[0] & 0x80) != 0x80) {
		write_file_pex(pxe_idx, -1, "temp");
		return ;
	}

	temp_sensor_data = get_temperature_sensor_data(rx_len, rx_data);
	real_temp_data = calculate_pxe_temp(temp_sensor_data);
	write_file_pex(pxe_idx, real_temp_data, "temp");
}

int pxe_set_dbus_property(int pxe_idx, char *property_name, char *property_value)
{
	char pxe_info_node[256] = {0};
	snprintf(pxe_info_node, sizeof(pxe_info_node), "/org/openbmc/sensors/pxe/pxe%d", pxe_idx);
	return set_dbus_property(pxe_info_node , property_name, "s", (void *) property_value);
}

void function_get_pxe_serial_data(int pxe_idx)
{
	pxe_device_i2c_cmd *i2c_cmd;
	int i2c_bus;
	int i2c_addr;
	int ret;
	int i;
	pxe_device_serial *p_serial;
	char property_value[20];
	char *st = NULL;

	i2c_bus = pxe_device_bus[pxe_idx].bus_no;
	i2c_addr = pxe_device_bus[pxe_idx].slave;
	p_serial = &(pxe_device_bus[pxe_idx].serial);

	if (p_serial->serial_count == PXE_SERIAL_LEN) {
		return ;
	}

	i2c_cmd = &pxe_device_cmd_tab[EM_PXE_CMD_UPPER_SERIAL_READ];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl I2C_SLAVE, cmd:%d, ret:%d\n", i2c_cmd->cmd, ret);
		return ;
	}

	p_serial->serial_count = 0;
	for(i = 0; i<i2c_cmd->read_cmd.len; i++)
		p_serial->serial_data[p_serial->serial_count++] = i2c_cmd->read_cmd.data[i];

	i2c_cmd = &pxe_device_cmd_tab[EM_PXE_CMD_LOWER_SERIAL_READ];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl I2C_SLAVE, cmd:%d, ret:%d\n", i2c_cmd->cmd, ret);
		return ;
	}

	for(i = 0; i<i2c_cmd->read_cmd.len; i++)
		p_serial->serial_data[p_serial->serial_count++] = i2c_cmd->read_cmd.data[i];

	st = property_value;
	for (i = 0; i<p_serial->serial_count; i++, st+=2)
	{
		snprintf(st, 3, "%02x", p_serial->serial_data[i]);
	}

	if (pxe_set_dbus_property(pxe_idx, "Serial Number", property_value) < 0)
		p_serial->serial_count = 0;
}

int  init_data_folder(int index)
{
	char f_path[128];
	FILE *fp;
	sprintf(f_path , "%s/pxe%d_temp", PXE_TEMP_PATH, index);
	if( access( f_path, F_OK ) != -1 )
		return 1;
	else {
		fp = fopen(f_path,"w");
		if(fp == NULL) {
			fprintf(stderr,"Error:[%s] opening:[%s]\n",strerror(errno),f_path);
			return -1;
		}
		fprintf(fp, "%d",-1);
		fclose(fp);
	}
	return 1;

}

void pxe_data_scan()
{
	/* init the global data */
	int i = 0;

	/* create the file patch for dbus usage*/
	/* check if directory is existed */
	if (access(PXE_TEMP_PATH, F_OK) != 0) {
		mkdir(PXE_TEMP_PATH, 0755);
	}

	for(i=0; i<MAX_PXE_NUM; i++) {
		if (init_data_folder(i) != 1)
			return ;
	}

	printf("pxe9797 control starting!!!\n");
	while(1) {
		for(i=0; i<MAX_PXE_NUM; i++) {
			function_get_pxe_temp_data(i);
			function_get_pxe_serial_data(i);
		}
		sleep(1);
	}
}

int
main(void)
{
	pxe_data_scan();
	return 0;
}


