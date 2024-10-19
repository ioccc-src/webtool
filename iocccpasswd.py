#!/usr/bin/env python3
# pylint: disable=import-error
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
# pylint: disable=too-many-branches
# pylint: disable=unused-import
# pylint: disable=too-many-statements
"""
Functions to implement adding and deleting of IOCCC contestants.
"""

# system imports
#
import json
import argparse
from os import listdir, remove, rmdir
import sys


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
from ioccc_common import *


# iocccpassword version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.1 2024-10-19"


def main():
    """
    Main routine when run as a program.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    global_errmsg = ""
    force_pw_change = False
    password = None
    disable_login = False
    pw_change_by = -1
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    program = os.path.basename(__file__)

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="Manage IOCCC submit server password file",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-a', '--add',
                        help="add a new user",
                        metavar='USER',
                        nargs=1)
    parser.add_argument('-u', '--update',
                        help="update a user or add if not a user",
                        metavar='USER',
                        nargs=1)
    parser.add_argument('-d', '--delete',
                        help="delete an exist user",
                        metavar='USER',
                        nargs=1)
    parser.add_argument('-p', '--password',
                        help="specify the password (def: generate random password)",
                        metavar='PW',
                        nargs=1)
    parser.add_argument('-c', '--change',
                        help='force a password change at next login',
                        metavar='')
    parser.add_argument('-g', '--grace',
                        help='grace time in seconds from to change the password',
                        metavar='SECS',
                        type=int,
                        nargs=1)
    parser.add_argument('-n', '--nologin',
                        help='disable login',
                        metavar='')
    args = parser.parse_args()

    # -c - force user to change their password at the next login
    #
    if args.change:
        force_pw_change = True

    # -g secs - set the grace time to change in seconds from now
    #
    if args.grace:
        pw_change_by = args.grace + now

    # -p password - use password supplied in the command line
    #
    if args.password:
        password = args.password

    # -n - disable login of user
    #
    if args.nologin:
        disable_login = True

    # -a user - add user if they do not already exist
    #
    if args.add:

        # add with random password unless we used -p password
        #
        if not password:
            password = generate_password()

        # we store the hash of the password only
        #
        pwhash = hash_password(password)

        # determine the username to add
        #
        username = args.add

        # the user must not already exist
        #
        if lookup_username(username):
            print(f"ERROR: username already exists: {username}")
            sys.exit(7)

        # add the user
        #
        if update_username(username, pwhash, force_pw_change, pw_change_by, disable_login):
            print(f"added username: {username} password: {password}")
        else:
            print(f"ERROR: cannot add added username: {username} password: {password}")
            print(global_errmsg)
            sys.exit(8)

    # -u user - update if they exit, or add user if they do not already exist
    #
    if args.update:

        # add with random password unless we used -p password
        #
        if not password:
            password = generate_password()

        # we store the hash of the password only
        #
        pwhash = hash_password(password)

        # determine the username to update
        #
        username = args.update

        # update the user
        #
        if update_username(username, pwhash, force_pw_change, pw_change_by, disable_login):
            print(f"Updated username: {username} password: {password}")
            sys.exit(0)
        else:
            print(f"ERROR: cannot add added username: {username} password: {password}")
            print(global_errmsg)
            sys.exit(9)

    # -d user - delete user
    #
    if args.delete:

        # determine the username to delete
        #
        username = args.update

        # the user must already exist
        #
        if not lookup_username(username):
            print(f"ERROR: username does not exist: {username}")
            sys.exit(10)

        # remove the user
        #
        if delete_username(username):
            print(f"username: {username} deleted")
            sys.exit(0)
        else:
            print(f"unable to delete username: {username}")
            print(global_errmsg)
            sys.exit(10)

if __name__ == '__main__':
    main()
