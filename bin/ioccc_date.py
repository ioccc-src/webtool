#!/usr/bin/env python3
#
# ioccc_date.py - Manage the IOCCC start and/or end dates

"""
ioccc_date.py - Manage the IOCCC start and/or end dates
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
        change_startup_appdir, \
        error, \
        read_state, \
        return_last_errmsg, \
        setup_logger, \
        update_state


# ioccc_date.py version
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
    start_given = False
    stop_given = False

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="Manage IOCCC submit server password file and state file",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-t', '--topdir',
                        help="app directory path",
                        metavar='appdir',
                        nargs=1)
    parser.add_argument('-s', '--start',
                        help="set IOCCC start date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
                        nargs=1)
    parser.add_argument('-S', '--stop',
                        help="set IOCCC stop date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
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

    # determine the IOCCC start and IOCCC end dates
    #
    start_datetime, stop_datetime = read_state()
    if not start_datetime:
        error(f'{program}: read_state for start_datetime failed: <<{return_last_errmsg()}>>')
        print("ERROR via print: unable to fetch of start date: <<" + return_last_errmsg() + ">>")
        sys.exit(4)
    if not stop_datetime:
        error(f'{program}: read_state for stop_datetime failed: <<{return_last_errmsg()}>>')
        print("ERROR via print: unable to fetch of stop date: <<" + return_last_errmsg() + ">>")
        sys.exit(5)

    # -s - set IOCCC start date
    #
    if args.start:
        start_given = True
        start_datetime = args.start[0]

    # -S - set IOCCC stop date
    #
    if args.stop:
        stop_given = True
        stop_datetime = args.stop[0]

    # if either -s DateTime or -S DateTime was given:
    #
    if start_given or stop_given:

        # update the start and/or stop dates
        #
        if not update_state(str(start_datetime), str(stop_datetime)):
            error(f'{program}: update_state failed: <<{return_last_errmsg()}>>')
            print("ERROR via print: failed to update start and/or stop date(s): <<" + return_last_errmsg() + ">>")
            sys.exit(6)
        else:
            print("Notice via print: set IOCCC start: " + str(start_datetime) + " IOCCC stop: " + str(stop_datetime))
            sys.exit(0)

    # no option selected
    #
    print("Notice via print: IOCCC start: " + str(start_datetime) + " IOCCC stop: " + str(stop_datetime))
    sys.exit(0)


# case: run from the command line
#
if __name__ == '__main__':
    main()
