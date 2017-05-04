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

def add_log(args):
    event = Event(
        args.severity,
        args.message,
        args.sensor_type,
        args.sensor_number)
    logid = EventManager().add_log(event)
    print('created log %04X' % logid)

def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser_add = subparsers.add_parser('add')
    parser_add.set_defaults(func=add_log)
    parser_add.add_argument(
        '--severity', type=str, default=Event.SEVERITY_INFO,
        choices=[Event.SEVERITY_DEBUG, Event.SEVERITY_INFO, Event.SEVERITY_ERR])
    parser_add.add_argument(
        'sensor_type', type=str, help='sensor type in hexadecimal')
    parser_add.add_argument(
        'sensor_number', type=str, help='sensor number in hexadecimal')
    parser_add.add_argument('message', type=str)
    parser_clear = subparsers.add_parser('clear')
    parser_clear.set_defaults(func=clear_logs)
    parser_list = subparsers.add_parser('list')
    parser_list.set_defaults(func=list_logs)
    return parser

def clear_logs(_):
    event_manager = EventManager()
    event_manager.remove_all_logs()
    print('removed all event logs')

def list_logs(_):
    event_manager = EventManager()
    print('%04s | %19s | %8s | %s' % ('ID', 'TIME', 'SEVERITY', 'MESSAGE'))
    for logid in event_manager.get_log_ids():
        event = event_manager.get_log(logid)
        print('%04X | %19s | %8s | %s' % (
            event.logid, event.time, event.severity, event.message))

def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    args.func(args)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except StandardError as exce:
        LOGGER.exception(exce)
