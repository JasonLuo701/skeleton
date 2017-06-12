#include <stdio.h>
#include <openbmc_intf.h>
#include <gpio.h>
#include <openbmc.h>
#include <pthread.h>
#include <fcntl.h>

/* ------------------------------------------------------------------------- */
static const gchar* dbus_object_path = "/org/openbmc/buttons";
static const gchar* instance_name = "power0";
static const gchar* dbus_name = "org.openbmc.buttons.Power";
static const gchar* dbus_control_power_name = "org.openbmc.control.Power";
static const gchar* dbus_control_power_objpath = "/org/openbmc/control/power0";
static const int LONG_PRESS_SECONDS = 3;
static GDBusObjectManagerServer *manager = NULL;
static ControlPower *control_power = NULL;

//This object will use these GPIOs
GPIO gpio_button = (GPIO){ "PWR_BTN_N" };

static gboolean
on_is_on(Button *btn,
		GDBusMethodInvocation *invocation,
		gpointer user_data)
{
	gboolean btn_state=button_get_state(btn);
	button_complete_is_on(btn,invocation,btn_state);
	return TRUE;
}

static gboolean
on_button_press(Button *btn,
		GDBusMethodInvocation *invocation,
		gpointer user_data)
{
	button_emit_pressed(btn);
	button_complete_sim_press(btn,invocation);
	return TRUE;
}

static gboolean
set_dc_on_off_state(gboolean in_progress)
{
	int result, count=-1;
	FILE *fp;
	int rc;

	fp = fopen("/run/initramfs/dc_on_off.LOCK", "a+");
	if (fp == NULL)
		return FALSE;
	result = flock(fileno(fp), LOCK_EX);
	if (result < 0)
		return FALSE;
	fscanf(fp, "%d", &count);
	if (count == -1)
		count = 0;
	if (ftruncate(fileno(fp), 0) != 0)
		return FALSE;
	if (in_progress)
	{
		count++;
		rc = control_power_get_dc_on_off (control_power);
		control_power_set_dc_on_off(control_power, 1);
		rc = control_power_get_dc_on_off (control_power);
	} else {
		count--;
		if (count < 0)
			count = 0;
		if (count == 0) {
			rc = control_power_get_dc_on_off (control_power);
			control_power_set_dc_on_off(control_power, 0);
			rc = control_power_get_dc_on_off (control_power);
		}
	}
	fflush(fp);
	fclose(fp);

	return TRUE;
}

static void
*post_reset_flag()
{
	sleep(10);
	set_dc_on_off_state(FALSE);
}

static gboolean
reset_dc_on_off_flag()
{
	pid_t pid;
	pthread_t tid;
	pthread_create(&tid, NULL, post_reset_flag, NULL);
	pthread_detach(tid);
	return TRUE;
}

static gboolean
on_button_interrupt( GIOChannel *channel,
		GIOCondition condition,
		gpointer user_data )
{
	GError *error = 0;
	gsize bytes_read = 0;
	gchar buf[2];
	buf[1] = '\0';
	g_io_channel_seek_position( channel, 0, G_SEEK_SET, 0 );
	g_io_channel_read_chars(channel,
			buf, 1,
			&bytes_read,
			&error );
	printf("%s\n",buf);

	time_t current_time = time(NULL);
	if(gpio_button.irq_inited)
	{
		Button* button = object_get_button((Object*)user_data);
		if(buf[0] == '0')
		{
			printf("Power Button pressed\n");
			set_dc_on_off_state(TRUE);
			button_emit_pressed(button);
			reset_dc_on_off_flag();
			button_set_timer(button,(long)current_time);
		}
		else
		{
			long press_time = current_time-button_get_timer(button);
			printf("Power Button released, held for %ld seconds\n",press_time);
			if(press_time > LONG_PRESS_SECONDS)
			{
				set_dc_on_off_state(TRUE);
				button_emit_pressed_long(button);
				reset_dc_on_off_flag();
			} else {
				button_emit_released(button);
			}
		}
	}
	else { gpio_button.irq_inited = true; }

	return TRUE;
}

static void
on_bus_acquired(GDBusConnection *connection,
		const gchar *name,
		gpointer user_data)
{
	ObjectSkeleton *object;
	//g_print ("Acquired a message bus connection: %s\n",name);
	manager = g_dbus_object_manager_server_new(dbus_object_path);
	gchar *s;
	s = g_strdup_printf("%s/%s",dbus_object_path,instance_name);
	object = object_skeleton_new(s);
	g_free(s);

	Button* button = button_skeleton_new();
	object_skeleton_set_button(object, button);
	g_object_unref(button);

	//define method callbacks
	g_signal_connect(button,
			"handle-is-on",
			G_CALLBACK(on_is_on),
			NULL); /* user_data */
	g_signal_connect(button,
			"handle-sim-press",
			G_CALLBACK(on_button_press),
			NULL); /* user_data */


	/* Export the object (@manager takes its own reference to @object) */
	g_dbus_object_manager_server_set_connection(manager, connection);
	g_dbus_object_manager_server_export(manager, G_DBUS_OBJECT_SKELETON(object));
	g_object_unref(object);

	// get gpio device paths
	int rc = GPIO_OK;
	do {
		rc = gpio_init(connection,&gpio_button);
		if(rc != GPIO_OK) { break; }
		rc = gpio_open_interrupt(&gpio_button,on_button_interrupt,object);
		if(rc != GPIO_OK) { break; }
	} while(0);
	if(rc != GPIO_OK)
	{
		printf("ERROR PowerButton: GPIO setup (rc=%d)\n",rc);
	}

	control_power = control_power_proxy_new_sync (connection,
					G_DBUS_PROXY_FLAGS_NONE,
					dbus_control_power_name,
					dbus_control_power_objpath,
					NULL,
					NULL);
}


static void
on_name_acquired(GDBusConnection *connection,
		const gchar *name,
		gpointer user_data)
{
}

static void
on_name_lost(GDBusConnection *connection,
		const gchar *name,
		gpointer user_data)
{
}

gint
main(gint argc, gchar *argv[])
{
	GMainLoop *loop;

	cmdline cmd;
	cmd.argc = argc;
	cmd.argv = argv;

	guint id;
	loop = g_main_loop_new(NULL, FALSE);

	id = g_bus_own_name(DBUS_TYPE,
			dbus_name,
			G_BUS_NAME_OWNER_FLAGS_ALLOW_REPLACEMENT |
			G_BUS_NAME_OWNER_FLAGS_REPLACE,
			on_bus_acquired,
			on_name_acquired,
			on_name_lost,
			&cmd,
			NULL);

	g_main_loop_run(loop);

	g_bus_unown_name(id);
	g_main_loop_unref(loop);
	return 0;
}
