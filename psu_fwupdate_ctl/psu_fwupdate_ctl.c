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

enum {
	EM_PSU_DEVICE_1 = 0,
	EM_PSU_DEVICE_2,
	EM_PSU_DEVICE_3,
	EM_PSU_DEVICE_4,
	EM_PSU_DEVICE_5,
	EM_PSU_DEVICE_6,
	EM_PSU_DEVICE_MAX,
};

enum {
	EM_PSU_CMD_CHECK_VER_CTL = 0,
	EM_PSU_CMD_UNLOCK_PSU_CTL,
	EM_PSU_CMD_WR_ISP_KEY_CTL,
	EM_PSU_CMD_BOOT_PSU_OS_CTL,
	EM_PSU_CMD_RESTART_CTL,
	EM_PSU_CMD_WR_DATA_CTL,
	EM_PSU_CMD_CHECK_DATA_CTL,
	EM_PSU_CMD_REBOOT_PSU_CTL,
	EM_PSU_CMD_MAX
};

typedef struct {
	__u8 bus_no;

	__u8 slave;

	__u8 device_index;
} psu_device_mapping;

psu_device_mapping psu_device_bus[EM_PSU_DEVICE_MAX] = {
	{8, 0x58, EM_PSU_DEVICE_1},
	{9, 0x58, EM_PSU_DEVICE_2},
	{10, 0x58, EM_PSU_DEVICE_3},
	{11, 0x58, EM_PSU_DEVICE_4},
	{12, 0x58, EM_PSU_DEVICE_5},
	{13, 0x58, EM_PSU_DEVICE_6},
};

typedef struct {
	int len;
	__u8 data[256];
} i2c_cmd_data;

typedef struct {
	int cmd;
	i2c_cmd_data write_cmd;
	i2c_cmd_data read_cmd;
	int delay;
} psu_device_i2c_cmd;

static char g_psu_fw_data_path[100];

psu_device_i2c_cmd psu_device_cmd_tab[EM_PSU_CMD_MAX] = {
	{
		EM_PSU_CMD_CHECK_VER_CTL,
		{2, {0x08, 0xD5}},
		{-1,{0x0}},
		0
	},
	{
		EM_PSU_CMD_UNLOCK_PSU_CTL,
		{2, {0x10, 0x00}},
		{-1,{0x0}},
		0
	},
	{
		EM_PSU_CMD_WR_ISP_KEY_CTL,
		{5, {0xD1, 0x49, 0x6E, 0x56, 0x65}},
		{-1,{0x0}},
		0
	},
	{
		EM_PSU_CMD_BOOT_PSU_OS_CTL,
		{2, {0xD2, 0x02}},
		{-1,{0x0}},
		0
	},
	{
		EM_PSU_CMD_RESTART_CTL,
		{2, {0xD2, 0x01}},
		{-1,{0x0}},
		0
	},
	{
		EM_PSU_CMD_WR_DATA_CTL,
		{17, {0xD4}},
		{-1,{0x0}},
		20*1000

	},
	{
		EM_PSU_CMD_CHECK_DATA_CTL,
		{2, {0x01, 0xD2}},
		{4,{0x0}},
		0
	},
	{
		EM_PSU_CMD_REBOOT_PSU_CTL,
		{3, {0x00, 0xD2, 0x03}},
		{-1,{0x0}},
		0
	},

};

#define I2C_CLIENT_PEC          0x04    /* Use Packet Error Checking */
#define I2C_M_RECV_LEN          0x0400  /* length will be first received byte */

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

static int smbus_commmand_write(int i2c_bus, int i2c_addr, __u8 *write_data, int write_count, int i2c_command)
{
	int fd;
	char filename[MAX_I2C_DEV_LEN] = {0};
	int rc=-1;
	int retry_gpu = 5;
	int count = 0;
	int w_count = 0;
	int i;

	sprintf(filename,"/dev/i2c-%d",i2c_bus);
	fd = open(filename,O_RDWR);

	if (fd == -1) {
		fprintf(stderr, "Failed to open i2c device %s", filename);
		return rc;
	}

	if(i2c_smbus_write_block_data(fd, i2c_command, write_count, write_data) < 0) {
		close(fd);
		return -1;
	}
	close(fd);
	return 0;
}

static int psu_i2c_raw_access(int i2c_bus, int i2c_addr, int cmd)
{
	psu_device_i2c_cmd *i2c_cmd;
	int ret = 0;
	int i;
	i2c_cmd = &psu_device_cmd_tab[cmd];
	ret = i2c_raw_access(i2c_bus, i2c_addr, i2c_cmd->write_cmd.len,
			     i2c_cmd->write_cmd.data, i2c_cmd->read_cmd.len, i2c_cmd->read_cmd.data);
	if (ret < 0) {
		fprintf(stderr, "Failed to do iotcl cmd:%d, ret:%d\n", i2c_cmd->cmd, ret);
		return ret;
	}

	printf("[%s]cmd:%d :\n", __FUNCTION__, cmd);
	for (i = 0; i<i2c_cmd->write_cmd.len; i++)
		printf("0x%0x ", i2c_cmd->write_cmd.data[i]);
	printf("\n---------------\n");
	for (i = 0; i<i2c_cmd->read_cmd.len; i++)
		printf("0x%0x ", i2c_cmd->read_cmd.data[i]);
	if (i2c_cmd->read_cmd.len > 0)
		printf("\n=========================\n");

	return ret;
}

static void disable_psu_bus_unbind(int i2c_bus, int i2c_addr)
{
	char cmd[200] = {0};
	sprintf(cmd, "echo %d-00%x > /sys/bus/i2c/devices/%d-00%x/driver/unbind",
		i2c_bus, i2c_addr, i2c_bus, i2c_addr);
	system(cmd);
}

static void enable_psu_bus_bind(int i2c_bus, int i2c_addr)
{

	char file_path[100];
	char buffer[100];
	FILE *pFile;

	sprintf(file_path, "/sys/bus/i2c/devices/i2c-%d/delete_device",i2c_bus);
	pFile = fopen(file_path,"w" );
	if( pFile != NULL ) {
		buffer[0] = 0;
		sprintf(buffer, "0x%x",i2c_addr);
		fwrite(buffer,1,strlen(buffer),pFile);
	}
	fclose(pFile);

	file_path[0] = 0;
	sprintf(file_path, "//sys/bus/i2c/devices/i2c-%d/new_device",i2c_bus);
	pFile = fopen(file_path,"w" );
	if( pFile != NULL ) {
		buffer[0] = 0;
		sprintf(buffer, "pmbus 0x%x",i2c_addr);
		fwrite(buffer,1,strlen(buffer),pFile);
	}
	fclose(pFile);
}

static int write_psu_fwdata(int i2c_bus, int i2c_addr)
{
	FILE *fPtr;
	char data[49];
	int ret, ret_data;
	int i;

	fPtr = fopen(g_psu_fw_data_path, "r");
	if (!fPtr) {
		fprintf(stderr, "write_psu_fwdata: open file fail: %s\n", g_psu_fw_data_path);
		return -1;
	}

	psu_device_i2c_cmd *i2c_cmd;
	i2c_cmd = &psu_device_cmd_tab[EM_PSU_CMD_WR_DATA_CTL];
	while (!feof(fPtr)) {
		memset(data, 0, sizeof(data));
		ret = fread(data, sizeof(data) -1 , 1, fPtr);

		char *ptr_data = data;
		i2c_cmd_data *prt_i2c_write= &(i2c_cmd->write_cmd);
		prt_i2c_write->len = 1;

		while(*ptr_data != '\0') {
			int t_data;
			ret_data = sscanf(ptr_data,"%0X",  &t_data);
			if (ret_data <= 0)
				break;

			prt_i2c_write->data[prt_i2c_write->len]=t_data;
			prt_i2c_write->len++;
			ptr_data+=3;
		}

		if (prt_i2c_write->len > 1) {
			if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_WR_DATA_CTL) < 0) {
				fprintf(stderr, "write_psu_fwdata: EM_PSU_CMD_WR_DATA_CTL Error!! \n");
				for (i = 0; i<prt_i2c_write->len; i++)
					printf("0x%0X ", prt_i2c_write->data[i]);
				printf("\n----------------\n");

				fclose(fPtr);
				return -1;
			}
			usleep(20*1000);
		}
	}
	fclose(fPtr);
	return 1;
}

static int start_psu_fwupdate(int psu_number)
{
	int i2c_bus;
	int i2c_addr;
	int ret = -1;

	i2c_bus = psu_device_bus[psu_number].bus_no;
	i2c_addr = psu_device_bus[psu_number].slave;

	disable_psu_bus_unbind(i2c_bus, i2c_addr);

	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_CHECK_VER_CTL) < 0)
		goto error_psu_fwupdate;
	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_UNLOCK_PSU_CTL) < 0)
		goto error_psu_fwupdate;
	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_WR_ISP_KEY_CTL) < 0)
		goto error_psu_fwupdate;
	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_BOOT_PSU_OS_CTL) < 0)
		goto error_psu_fwupdate;
	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_RESTART_CTL) < 0)
		goto error_psu_fwupdate;
	if (write_psu_fwdata(i2c_bus, i2c_addr) < 0)
		goto error_psu_fwupdate;
	if (psu_i2c_raw_access(i2c_bus, i2c_addr, EM_PSU_CMD_REBOOT_PSU_CTL) < 0)
		goto error_psu_fwupdate;

	ret = 0;

error_psu_fwupdate:
	enable_psu_bus_bind(i2c_bus, i2c_addr);
	return ret;
}

int
main(int argc, char **argv)
{
	if (argc != 3) {
		fprintf(stderr, "Error option settings !!!\n");
		return -1;
	}

	int psu_number = atoi(argv[1]) - 1;
	strcpy(g_psu_fw_data_path, argv[2]);

	return 	start_psu_fwupdate(psu_number);
}

