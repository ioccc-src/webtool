#!/usr/bin/env python3
#
# set_slot_status.py - modify the status of a IOCCC submit server user's slot

"""
set_slot_status.py - modify the status of a IOCCC submit server user's slot
"""

# system imports
#
import sys
import argparse
import os


# import the ioccc python utility code
#
# Sort the import list with: sort -d -u
#
from iocccsubmit import \
        MAX_SUBMIT_SLOT, \
        change_startup_appdir, \
        error, \
        info, \
        lookup_username, \
        return_last_errmsg, \
        return_slot_json_filename, \
        setup_logger, \
        update_slot_status


# set_slot_status.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "2.2.0 2024-12-22"


def main():
    """
    Main routine when run as a program.
    """

    # setup
    #
    program = os.path.basename(__file__)

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="Manage IOCCC submit server password file and state file",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-t', '--topdir',
                        help="app directory path",
                        metavar='appdir',
                        nargs=1)
    parser.add_argument('-l', '--log',
                        help="log via: stdout stderr syslog none (def: syslog)",
                        default="syslog",
                        action="store",
                        metavar='logtype',
                        type=str)
    parser.add_argument('-L', '--level',
                        help="set log level: dbg debug info warn warning error crit critical (def: info)",
                        default="info",
                        action="store",
                        metavar='dbglvl',
                        type=str)
    parser.add_argument('username', help='IOCCC submit server username')
    parser.add_argument('slot_num', help=f'slot number from 0 to {MAX_SUBMIT_SLOT}')
    parser.add_argument('status', help='slot status string')
    args = parser.parse_args()

    # setup logging according to -l logtype -L dbglvl
    #
    setup_logger(args.log, args.level)

    # -t topdir - set the path to the top level app direcory
    #
    if args.topdir:
        if not change_startup_appdir(args.topdir[0]):
            error(f'{program}: change_startup_appdir failed: <<{return_last_errmsg()}>>')
            print("ERROR via print: change_startup_appdir error: <<" + return_last_errmsg() + ">>")
            sys.exit(3)

    # verify arguments
    #
    username = args.username
    if not lookup_username(username):
        print(f'ERROR via print: lookup_username for  username: {username} '
              f'failed: <<{return_last_errmsg()}>>')
        sys.exit(4)
    slot_num = int(args.slot_num)
    slot_json_file = return_slot_json_filename(username, slot_num)
    if not slot_json_file:
        print(f'ERROR via print: invalid slot number: {slot_num} for username: {username}')
        print(f'Notice: slot numbers must be between 0 and {MAX_SUBMIT_SLOT}')
        sys.exit(5)
    status = args.status

    # update slot JSON file
    #
    if not update_slot_status(username, slot_num, status):
        print(f'ERROR via print: update_slot_status for username: {username} slot_num: {slot_num} '
              f'failed: <<{return_last_errmsg()}>>')
        sys.exit(6)

    # no option selected
    #
    info(f'{program}: username: {username} slot_num: {slot_num} status: <<{status}>>')
    print(f'Notice via print: username: {username} slot_num: {slot_num} status: <<{status}>>')
    sys.exit(0)


# case: run from the command line
#
if __name__ == '__main__':
    main()
