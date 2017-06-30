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
    int SlotPRSNTGPIO[] = {252, 253, 254, 255};
    int i = 0;
    char buff_path[256] = "";

    for(i=0; i<(sizeof(SlotPRSNTGPIO)/sizeof(SlotPRSNTGPIO[0])); i++) {
        sprintf(buff_path, "echo %d > /sys/class/gpio/export", SlotPRSNTGPIO[i]);
        system(buff_path);

        sprintf(buff_path, "echo in > /sys/class/gpio/gpio%d/direction", SlotPRSNTGPIO[i]);
        system(buff_path);
    }
}

void init_therm_overt_gpio()
{
    int SlotPRSNTGPIO[] = {244, 245, 246, 247, 248, 249, 250, 251};
    int i = 0;
    char buff_path[256] = "";

    for(i=0; i<(sizeof(SlotPRSNTGPIO)/sizeof(SlotPRSNTGPIO[0])); i++) {
        sprintf(buff_path, "echo %d > /sys/class/gpio/export", SlotPRSNTGPIO[i]);
        system(buff_path);

        sprintf(buff_path, "echo in > /sys/class/gpio/gpio%d/direction", SlotPRSNTGPIO[i]);
        system(buff_path);
    }
}

void init_power_good_gpio()
{
    int SlotPRSNTGPIO[] = {228, 229, 230, 231, 232, 233, 234, 235};
    int i = 0;
    char buff_path[256] = "";

    for(i=0; i<(sizeof(SlotPRSNTGPIO)/sizeof(SlotPRSNTGPIO[0])); i++) {
        sprintf(buff_path, "echo %d > /sys/class/gpio/export", SlotPRSNTGPIO[i]);
        system(buff_path);

        sprintf(buff_path, "echo in > /sys/class/gpio/gpio%d/direction", SlotPRSNTGPIO[i]);
        system(buff_path);
    }
}

void init_gpu_power_en()
{
    int SlotPRSNTGPIO[] = {220, 221, 222, 223, 224, 225, 226, 227};
    int i = 0;
    char buff_path[256] = "";

    for(i=0; i<(sizeof(SlotPRSNTGPIO)/sizeof(SlotPRSNTGPIO[0])); i++) {
        sprintf(buff_path, "echo %d > /sys/class/gpio/export", SlotPRSNTGPIO[i]);
        system(buff_path);

        sprintf(buff_path, "echo out > /sys/class/gpio/gpio%d/direction", SlotPRSNTGPIO[i]);
        system(buff_path);
    }
}

void init_gpu_gpio()
{
    int SlotPRSNTGPIO[] = {236, 237, 238, 239, 240, 241, 242, 243};
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

    /* Check the ntp server address in EEPROM */
    system("python /usr/sbin/ntp_eeprom.py --check-ntp");

    /* Init PCIE slot present GPIO*/
    init_pcie_slot_gpio();

    /* Init GPU present & PWR GOOD & thermal GPIO*/
    init_gpu_gpio();
    init_power_good_gpio();
    init_therm_overt_gpio();
    init_gpu_power_en();

    return 0;
}
