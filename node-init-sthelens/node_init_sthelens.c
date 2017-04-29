#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>

/*----------------------------------------------------------------*/
/* Main Event Loop                                                */
#define PHYSICAL_I2C 7
#define PSU_NUM 6
#define LM25066_I2C 0
#define LM25066_NUM_1 2
#define LM25066_NUM_2 8

int
main(int argc, char *argv[])
{
    char buff_path[256] = "";
    int i = 0;

    /* Init pmbus node */
    for(i=1; i<=PSU_NUM; i++)
    {
        sprintf(buff_path, "echo pmbus 0x58 > /sys/bus/i2c/devices/i2c-%d/new_device", PHYSICAL_I2C+i);
        printf("%s\n", buff_path);
        system(buff_path);
    }

    /* Init lm25066 node */
    for(i=0; i<LM25066_NUM_1; i++)
    {
        sprintf(buff_path, "echo lm25066 0x%x > /sys/bus/i2c/devices/i2c-%d/new_device",0x10+i, LM25066_I2C);
        printf("%s\n", buff_path);
        system(buff_path);
    }

    for(i=0; i<LM25066_NUM_2; i++)
    {
        sprintf(buff_path, "echo lm25066 0x%x > /sys/bus/i2c/devices/i2c-%d/new_device",0x40+i, LM25066_I2C);
        printf("%s\n", buff_path);
        system(buff_path);
    }

    /* For firmware update feature: Create /var/home/ folder && link  between /run/initramfs and /var/home/wcs */
    system("mkdir /var/home/");
    system("ln -s /run/initramfs /var/home/wcs");

    return 0;
}
