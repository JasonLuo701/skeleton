#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

#include <fcntl.h>
#include <dirent.h>
#include <systemd/sd-bus.h>
#include <linux/i2c-dev-user.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sdbus_property.h>

int
fscanf(FILE *__restrict __stream,
                __const char *__restrict __format, ...)
{
    printf ("SHOUL NOT BE CALLED !!!!!!!!!!!!!!!\n");
    return 0;
}



#define DEFAULT_BUS     ( 0 )
#define DEFAULT_SLAVE   ( 0x4c )



#define READ_MODE       ( 0 )
#define WRITE_MODE      ( 1 )
#define MAX_CMDSTR_SIZE 25

static int bus = DEFAULT_BUS;
static __u8 slave_addr = DEFAULT_SLAVE;
static size_t write_count = -1;
static __u8 write_buffer[ 1024 ];
static __u8 read_buffer[ 1024 ];

static int operation_mode = -1;
char CmdString [MAX_CMDSTR_SIZE];

static char *arglist[] =
{
    "-b",
    "-s",
    "-d",
    "-w",
    "-r",
    "-c",
    NULL
};

static int busArgHandler( int argc, char **argv, int index );
static int slaveArgHandler( int argc, char **argv, int index );
static int dataArgHandler( int argc, char **argv, int index );
static int writeArgHandler( int argc, char **argv, int index );
static int readArgHandler( int argc, char **argv, int index );
static int CmdArgHandler( int argc, char **argv, int index );

static int ( *handlerList[] )( int, char **, int ) =
{
    busArgHandler,
    slaveArgHandler,
    dataArgHandler,
    writeArgHandler,
    readArgHandler,
    CmdArgHandler,
    NULL
};

typedef int (*fn_ptr)(char *);
typedef struct
{
    char  CmdStr [MAX_CMDSTR_SIZE];
    fn_ptr  PmbCmd;

} PmbMenu_T;

static void display_usage( void )
{
    printf("pmbus-test\n");
    printf( "Usage: pmbus-test <arguments>\n" );
    printf( "Arguments:\n" );

    printf( "\n*** PMBus Functions ***\n" );
    printf( "\t-b <bus number>: Set the bus number for this transaction.  Defaults to 0\n" );
    printf( "\t-s slave:\tCommunicate with the specified slave address in 7-bit format (in\n" );
    printf( "\t\t\thexadecimal)\n" );
    printf( "\t\t\tDefaults to 0x5a\n" );
    printf( "\t-d <bytes>:\tSend any number of data bytes to the specified slave.\n" );
    printf( "\t\t\tSeparate hexadecimal data bytes with spaces.  If this\n" );
    printf( "\t\t\tflag is used, it must be the last one on the\n" );
    printf( "\t\t\tcommand line.\n" );
    printf( "\t-r:\t\tJust read from the specified address, don't do a write.\n" );
    printf( "\t-w:\t\tJust write to the specified address, don't do a read.\n" );
    printf( "\t-c:\t\tCommand String\n" );
    printf( "\t-l:\t\tList of Supported Command Strings \n" );
    return;
}
static void display_Cmdstring( void )
{
    printf( "\nList of Supported Command Strings\n" );
    printf("\n[OPERATION, CLEAR_FALUTS, CAPABILITY, STATUS_WORD, ");
    printf("\nREAD_VIN, READ_IIN, READ_VOUT, READ_IOUT, READ_POUT, READ_PIN, ");
    printf("\nREAD_TEMPERATURE_1, READ_TEMPERATURE_2, READ_TEMPERATURE_3, READ_FAN_SPEED_1]\n");

}
static void parse_arguments( int argc, char **argv )
{
    int i, j,cnt=0;

    if( argc <= 1 )
    {
        display_usage();
        exit( EXIT_FAILURE );
    }
    if( strcmp( argv[ 1 ],"-l" ) == 0 )
    {
        display_Cmdstring();
        exit( EXIT_FAILURE );
    }
    for( i = 1; i < argc; i++ )
    {
        j = 0;
        while( arglist[ j ] != NULL )
        {
            if( strcmp( argv[ i ], arglist[ j ] ) == 0 )
            {
                int retval;
                /* Match!  Handle this argument (and skip the specified
                   number of arguments that were just handled) */
                retval = handlerList[ j ]( argc, argv, i );
                if( retval >= 0 )
                    i += retval;
                else
                {
                    fprintf( stderr, "Cannot handle argument: %s\n", arglist[ j ] );
                    exit( EXIT_FAILURE );
                }
                cnt++;
            }
            j++;
        }
    }
  if(cnt < 4)
      {
        display_usage();
        exit( EXIT_FAILURE );
    }
}


static int busArgHandler( int argc, char **argv, int index )
{
    if( index + 1 <= argc )
        bus = (__u8)strtol( argv[ index + 1 ], NULL, 10 );
    else
    {
        fprintf( stderr, "Missing argument to -b\n" );
        exit( EXIT_FAILURE );
    }

    return( 1 );
}

static int slaveArgHandler( int argc, char **argv, int index )
{
    long raw_slave_addr = 0;
    if( index + 1 <= argc )
    {
        raw_slave_addr = strtol( argv[ index + 1 ], NULL, 16 );
        if (raw_slave_addr > 255) {
            fprintf( stderr, "Slave address exceed 0xFF.\n" );
            exit( EXIT_FAILURE );
        }
        slave_addr = (__u8)raw_slave_addr;
        if( slave_addr == (__u8)0 )
        {
            fprintf( stderr, "Slave address 0x00 is not valid.\n" );
            exit( EXIT_FAILURE );
        }
    }
    else
    {
        fprintf( stderr, "Missing argument to -s\n" );
        exit( EXIT_FAILURE );
    }

    return( 1 );
}


static int dataArgHandler( int argc, char **argv, int index )
{
    int i;

    if( index + 1 > argc )
    {
        fprintf( stderr, "Missing argument(s) to -d\n" );
    }

    for( i = index + 1, write_count = 0; i < argc; i++, write_count++ )
        write_buffer[ write_count ] = (__u8)strtol( argv[ i ], NULL, 16 );

    return( write_count );
}


static int writeArgHandler( int argc, char **argv, int index )
{
    if( operation_mode != -1 )
    {
        fprintf( stderr, "Multiple operation types specified!\n" );
        exit( EXIT_FAILURE );
    }

    operation_mode = WRITE_MODE;

    return( 0 );
}


static int readArgHandler( int argc, char **argv, int index )
{
    if( operation_mode != -1 )
    {
        fprintf( stderr, "Multiple operation types specified!\n" );
        exit( EXIT_FAILURE );
    }

    operation_mode = READ_MODE;

    return( 0 );
}


static int CmdArgHandler( int argc, char **argv, int index )
{
    if( index + 1 <= argc )
    {
        strcpy (CmdString, argv[ index + 1 ]);
    }
    else
    {
        fprintf( stderr, "Missing argument to -c\n" );
        exit( EXIT_FAILURE );
    }

    return( 1 );
}

void print_result(char *result) {
	printf("%s: %s\n", CmdString, result);
	return;
}

int read_dev_node_string(char *path) {
	FILE *fp;
	char buf[100] = {0};
	float result;

	printf("dev_node %s\n", path);
	fp = fopen(path, "r");
	if(fp == NULL) {
		return -1;
	}
	fread(buf, sizeof(char), 100, fp);
	fclose(fp);
	print_result(buf);

	return 0;
}

int read_dev_node_decimal(char *path, int scale) {
	FILE *fp;
	char buf[100] = {0};
	float result;

	printf("dev_node %s\n", path);
	fp = fopen(path, "r");
	if(fp == NULL) {
		return -1;
	}
	fread(buf, sizeof(char), 100, fp);
	fclose(fp);
	sscanf(buf, "%f", &result);
	result = result / scale;

	if(snprintf( buf, sizeof(buf),"%f", result) >= sizeof(buf))
	{
		printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
		return -1;
	}
	print_result(buf);

	return 0;
}

int write_dev_node(char *path, char *buf) {
	int rc;
	FILE *fp = fopen(path,"w");
	if(fp == NULL) {
		return -1;
	}

	rc = fwrite(buf, strlen(buf), 1, fp);

	fclose(fp);

	return (rc == 1) ? 0 : -1;
}

int ReadVIN(char *hwmon_path) {
	int scale = 1000;

	strcat(hwmon_path, "in1_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}

int ReadIIN(char *hwmon_path) {
	int scale = 1000;

	strcat(hwmon_path, "curr1_input");
	read_dev_node_decimal(hwmon_path, scale);
    return 0;
}

int ReadPIN(char *hwmon_path) {
	int scale = 1000000;

	strcat(hwmon_path, "power1_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}

int ReadStatusWord(char *hwmon_path) {

	strcat(hwmon_path, "pmbus_status_word");
	read_dev_node_string(hwmon_path);

    return 0;
}

int ReadVOUT(char *hwmon_path) {
	int scale = 1000;

	strcat(hwmon_path, "in2_input");
	read_dev_node_decimal(hwmon_path, scale);
    return 0;
}

int ReadIOUT(char *hwmon_path) {
	int scale = 1000;

	strcat(hwmon_path, "curr2_input");
	read_dev_node_decimal(hwmon_path, scale);
    return 0;
}

int ReadPOUT(char *hwmon_path) {
	int scale = 1000000;

	strcat(hwmon_path, "power2_input");
	read_dev_node_decimal(hwmon_path, scale);
    return 0;
}

int ReadCapability(char *hwmon_path) {
	strcat(hwmon_path, "pmbus_capability");
	read_dev_node_string(hwmon_path);
    return 0;
}

int RWOperation(char *hwmon_path) {
	char buf[100];
	strcat(hwmon_path, "pmbus_operation");
    if(operation_mode==0) {
		read_dev_node_string(hwmon_path);
		return 0;
    } else {
		if (write_buffer[0]) {
			if(snprintf( buf, sizeof(buf),"%x", write_buffer[0]) >= sizeof(buf))
			{
				printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
				return -1;
			}
			write_dev_node(hwmon_path, buf);
			return 0;
		}
	}

}

int SendClearFaults(char *hwmon_path) {
	char buf[100];
	strcat(hwmon_path, "pmbus_clear_fault");
	if (write_buffer[0]) {
		if(snprintf( buf, sizeof(buf),"%x", write_buffer[0]) >= sizeof(buf))
		{
			printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
			return -1;
		}
		write_dev_node(hwmon_path, buf);
		return 0;
	}
    return 0;
}
int ReadTemp1(char *hwmon_path)
{
	int scale = 1000;

	strcat(hwmon_path, "temp1_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}

int ReadTemp2(char *hwmon_path)
{
	int scale = 1000;

	strcat(hwmon_path, "temp2_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}

int ReadTemp3(char *hwmon_path)
{
	int scale = 1000;

	strcat(hwmon_path, "temp3_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}

int ReadFan1Speed(char *hwmon_path)
{
	int scale = 1;

	strcat(hwmon_path, "fan1_input");
	read_dev_node_decimal(hwmon_path, scale);

    return 0;
}


PmbMenu_T PmMenu [] =
{
    {"OPERATION", RWOperation},
    {"CLEAR_FALUTS", SendClearFaults},
    {"CAPABILITY", ReadCapability},
    {"STATUS_WORD", ReadStatusWord},
    {"READ_VIN", ReadVIN},
    {"READ_IIN", ReadIIN},
    {"READ_VOUT", ReadVOUT},
    {"READ_IOUT", ReadIOUT},
    {"READ_TEMPERATURE_1", ReadTemp1},
    {"READ_TEMPERATURE_2",ReadTemp2},
    {"READ_TEMPERATURE_3",ReadTemp3},
    {"READ_FAN_SPEED_1", ReadFan1Speed},
    {"READ_POUT", ReadPOUT},
    {"READ_PIN", ReadPIN}
};

int main( int argc, char **argv )
{
    char hwmon_path[256];
    char hwmon_path_device[256];
	char actual_path[256]={0};
	char *hwmon_dir = "/sys/class/hwmon/";
    int bytes_read,i, Index =0;
    int CmdFnd = 0;
	struct stat st;
    struct dirent entry;
    struct dirent *endp;
    DIR *dirp;
	char *delim = "/";
    char *pch;
	char *bus_info;
	char bus_slave_addr[32];

    /* Read and interpret the arguments */
    parse_arguments( argc, argv );

	if(snprintf( bus_slave_addr, sizeof(bus_slave_addr),"%d-%.4x", bus, slave_addr) >= sizeof(bus_slave_addr))
	{
		printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
		return -1;
	}
	if (stat(hwmon_dir, &st) == -1)
        return -1;

    if ((dirp = opendir(hwmon_dir)) == NULL)
        return 0;
    for (;;) {
        endp = NULL;
        if (readdir_r(dirp, &entry, &endp) == -1) {
            closedir(dirp);
            return -1;
        }
        if (endp == NULL)
            break;
        if (strcmp(entry.d_name, ".") ==0 ||
            strcmp(entry.d_name, "..") ==0)
            continue;
		if(snprintf( hwmon_path_device, sizeof(hwmon_path_device),"%s%s/device", hwmon_dir, entry.d_name) >= sizeof(hwmon_path_device))
		{
			printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
			return -1;
		}
		if(snprintf( hwmon_path, sizeof(hwmon_path),"%s%s/", hwmon_dir, entry.d_name) >= sizeof(hwmon_path))
		{
			printf("Buffer Overflow in File :%s Line : %d  Function : %s\n",__func__, __LINE__, __func__);
			return -1;
		}
		realpath(hwmon_path_device, actual_path);
		pch = strtok(actual_path,delim);
		while(pch!=NULL) {
			bus_info = pch;
			pch = strtok(NULL,delim);
		}
		if (!strncmp(bus_info, bus_slave_addr, sizeof(bus_slave_addr))) {
			break;
		}
	}

    for (Index = 0; Index < (sizeof(PmMenu ) /sizeof (PmbMenu_T)); Index++)
    {
        if (strcasecmp (CmdString, PmMenu[Index].CmdStr) == 0)
        {
            CmdFnd =1;
            break;
        }
    }

    if (0 == CmdFnd)
    {
        printf ("Command Not Found ");
        return -1;
    }
    bytes_read = PmMenu [Index].PmbCmd (hwmon_path);

    return 0;
}
