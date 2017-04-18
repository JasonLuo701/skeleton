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

#define MAX_MDOT2_NUM 4
#define MDOT2_WRITE_CMD 0x0
typedef struct
{
    uint8_t bus;
    uint8_t slave_addr;
} pcie_dev_mapping;

pcie_dev_mapping Mdot2[MAX_MDOT2_NUM] = {
    {27, 0x6a},
    {28, 0x6a},
    {29, 0x6a},
    {30, 0x6a},
};

int get_Mdot2_data(int index)
{
    int fd, rc=0;
    int retry = 5;
    int readbuf[4];
    sprintf(filename,"/dev/i2c-%d", Mdot2[index].bus);

    fd = open(filename,O_RDWR);
    if (fd == -1) 
    {
        fprintf(stderr, "Failed to open i2c device %s", filename);
        return rc;
    }

    rc = ioctl(fd,I2C_SLAVE,slave);
    if(rc < 0)
    {
        fprintf(stderr, "Failed to do iotcl I2C_SLAVE\n");
        close(fd);
        return -1;
    }

   // if(i2c_smbus_write_byte(fd, MDOT2_WRITE_CMD) < 0)
   // {
   //     close(fd);
   //     return -1;
   // }

    while (retry)
    {
        if (i2c_smbus_read_block_data(fd, MDOT2_WRITE_CMD, readbuf) == 4)
        {
            printf("M.2 reading : 0x%x, 0x%x, 0x%x, 0x%x\n", readbuf[0], 
                                     readbuf[1], readbuf[2], readbuf[3]);
            close(fd);
            return 0;
        }
        retry--;
    }

    close(fd);
    return 0;
}

void pcie_data_scan()
{
    int i;

    while(1)
    {
        for(i=0; i<MAX_MDOT2_NUM; i++)
        {
            get_Mdot2_data(i);
        }
    }
}

int main(void)
{
    pcie_data_scan();
    return 0;
}
