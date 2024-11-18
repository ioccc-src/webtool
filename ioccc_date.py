#!/usr/bin/env python3
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
"""
Functions to set the open and close data of the IOCCC.
"""

# system imports
#
import argparse
import sys


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
# TO DO: Change wild card import into specific import set
#
from ioccc_common import *


# ioccc_date.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.0 2024-11-15"


def main():
    """
    Main routine when run as a program.
    """

    # setup
    #
    program = os.path.basename(__file__)
    start_given = False
    stop_given = False
    start_datetime, stop_datetime = read_state()
    if not start_datetime:
        print("ERROR: unable to fetch of start date: <<" + return_last_errmsg() + ">>")
        sys.exit(3)
    if not stop_datetime:
        print("ERROR: unable to fetch of stop date: <<" + return_last_errmsg() + ">>")
        sys.exit(4)

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="Manage IOCCC submit server password file and state file",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-s', '--start',
                        help="set IOCCC start date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
                        nargs=1)
    parser.add_argument('-S', '--stop',
                        help="set IOCCC stop date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
                        nargs=1)
    args = parser.parse_args()

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
            print("ERROR: failed to update start and/or stop  date(s): <<" + return_last_errmsg() + ">>")
            sys.exit(5)
        else:
            print("Notice: set IOCCC start: " + str(start_datetime) + " IOCCC stop: " + str(stop_datetime))
            sys.exit(0)


    # no option selected
    #
    print("Notice: IOCCC start: " + str(start_datetime) + " IOCCC stop: " + str(stop_datetime))
    sys.exit(0)

if __name__ == '__main__':
    main()
