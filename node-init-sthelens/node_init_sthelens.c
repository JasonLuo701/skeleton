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

void init_pcie_slot_gpio()
{
    int SlotPRSNTGPIO[] = {220, 221, 222, 223};
    int i = 0;
    char buff_path[256] = "";

    for(i=0; i<(sizeof(SlotPRSNTGPIO)/sizeof(SlotPRSNTGPIO[0])); i++) {
        sprintf(buff_path, "echo %d > /sys/class/gpio/export", SlotPRSNTGPIO[i]);
        system(buff_path);

        sprintf(buff_path, "echo in > /sys/class/gpio/gpio%d/direction", SlotPRSNTGPIO[i]);
        system(buff_path);
    }
}

int
main(int argc, char *argv[])
{
    char buff_path[256] = "";
    int i = 0;

    sprintf(buff_path, "ln -s /usr/lib/python2.7/site-packages/subprocess32.py /usr/lib/python2.7/site-packages/subprocess.py");
    system(buff_path);

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
    system("mkdir /var/wcs/");
    system("ln -s /run/initramfs /var/wcs/home");

    /* Check the ntp server address in EEPROM */
    system("python /usr/sbin/ntp_eeprom.py --check-ntp");

    /* Init PCIE slot present GPIO*/
    init_pcie_slot_gpio();

    return 0;
}
