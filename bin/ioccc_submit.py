#!/usr/bin/env python3
#
# ioccc_submit.py - IOCCC submit tool simulator

"""
ioccc_submit.py - IOCCC submit tool command line interface

This tool simulates the IOCCC submit tool web application
from the command line.
"""


# system imports
#
import os
import sys
import argparse


# import the ioccc python utility code
#
# Sort the import list with: sort -d -u
#
# pylint: disable-next=unused-import

from iocccsubmit.ioccc import application

from iocccsubmit.ioccc_common import \
    IP_ADDRESS, \
    TCP_PORT, \
    change_startup_appdir, \
    error, \
    return_last_errmsg, \
    setup_logger


# ioccc_submit.py version
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
    # pylint: disable-next=invalid-name

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="IOCCC submit server tool",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-i', '--ip',
                        help=f'IP address to connect (def: {IP_ADDRESS})',
                        default=IP_ADDRESS,
                        action="store",
                        metavar='ip',
                        type=str)
    parser.add_argument('-l', '--log',
                        help="log via: stdout stderr syslog none (def: stderr)",
                        default="stderr",
                        action="store",
                        metavar='logtype',
                        type=str)
    parser.add_argument('-L', '--level',
                        help="set log level: dbg debug info warn warning error crit critical (def: info)",
                        default="info",
                        action="store",
                        metavar='dbglvl',
                        type=str)
    parser.add_argument('-p', '--port',
                        help=f'open port (def: {TCP_PORT})',
                        default=TCP_PORT,
                        action="store",
                        metavar='port',
                        type=int)
    parser.add_argument('-t', '--topdir',
                        help="path of a correctly application tree",
                        metavar='appdir',
                        type=str)
    args = parser.parse_args()

    # setup logging according to -l logtype -L dbglvl
    #
    setup_logger(args.log, args.level)

    # -t topdir - set the path to the top level application direcory
    #
    if args.topdir:
        if not change_startup_appdir(args.topdir):
            error(f'{program}: change_startup_appdir failed: <<{return_last_errmsg()}>>')
            print("ERROR via print: change_startup_appdir failed: <<" + return_last_errmsg() + ">>")
            sys.exit(3)

    # launch the application if run from the command line
    #
    application.run(host=args.ip, port=args.port, debug=True)


# case: run from the command line
#
if __name__ == '__main__':
    main()
