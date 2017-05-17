#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=missing-docstring

from __future__ import print_function
import argparse
import logging
import sys
from obmc.events import Event
from obmc.events import EventManager

logging.basicConfig(format='%(levelname)-8s| %(message)s')
LOGGER = logging.getLogger('pyeventctl')
LOGGER.setLevel(logging.DEBUG)

SEVERITY_INFO = 'INFO'
SEVERITY_WARN = 'WARNING'
SEVERITY_CRIT = 'CRITICAL'

def severity_uint8_to_string(uint8):
    if uint8 == Event.SEVERITY_INFO:
        return SEVERITY_INFO
    elif uint8 == Event.SEVERITY_WARN:
        return SEVERITY_WARN
    elif uint8 == Event.SEVERITY_CRIT:
        return SEVERITY_CRIT
    else:
        raise ValueError('invalid severity level %d' % uint8)

def severity_string_to_uint8(string):
    if string == SEVERITY_INFO:
        return Event.SEVERITY_INFO
    elif string == SEVERITY_WARN:
        return Event.SEVERITY_WARN
    elif string == SEVERITY_CRIT:
        return Event.SEVERITY_CRIT
    else:
        raise ValueError('invalid severity level %s' % string)

def add_log(args):
    event = Event(
        severity_string_to_uint8(args.severity),
        int(args.sensor_type, 16),
        int(args.sensor_number, 16),
        int(args.event_dir_type, 16),
        int(args.event_data_1, 16),
        int(args.event_data_2, 16),
        int(args.event_data_3, 16),
        )
    logid = EventManager().add_log(event)
    print('created log %04X' % logid)

def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser_add = subparsers.add_parser('add')
    parser_add.set_defaults(func=add_log)
    parser_add.add_argument(
        '--severity', type=str, default=SEVERITY_INFO,
        choices=[SEVERITY_INFO, SEVERITY_WARN, SEVERITY_CRIT])
    parser_add.add_argument(
        '--event_dir_type', type=str, default='0x00',
        help='event_dir_type in hexadecimal')
    parser_add.add_argument(
        '--event_data_1', type=str, default='0x00',
        help='event data 1 in hexadecimal')
    parser_add.add_argument(
        '--event_data_2', type=str, default='0x00',
        help='event data 2 in hexadecimal')
    parser_add.add_argument(
        '--event_data_3', type=str, default='0x00',
        help='event data 3 in hexadecimal')
    parser_add.add_argument(
        'sensor_type', type=str, help='sensor type in hexadecimal')
    parser_add.add_argument(
        'sensor_number', type=str, help='sensor number in hexadecimal')
    parser_clear = subparsers.add_parser('clear')
    parser_clear.set_defaults(func=clear_logs)
    parser_list = subparsers.add_parser('list')
    parser_list.set_defaults(func=list_logs)
    return parser

def clear_logs(_):
    event_manager = EventManager()
    event_manager.remove_all_logs(0x80) # FIXME hard-coded
    print('removed all event logs')

def list_logs(_):
    event_manager = EventManager()
    print('%04s | %19s | %8s | %s' % ('ID', 'TIME', 'SEVERITY', 'MESSAGE'))
    for logid in event_manager.get_log_ids():
        event = event_manager.get_log(logid)
        print('%04X | %19s | %8s | %s' % (
            event.logid, event.time, severity_uint8_to_string(event.severity),
            event.assemble_message()))

def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    args.func(args)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except StandardError as exce:
        LOGGER.exception(exce)
