#!/usr/bin/env python3
# pylint: disable=import-error
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
# pylint: disable=too-many-branches
# pylint: disable=unused-import
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
"""
Functions to implement adding and deleting of IOCCC contestants.
"""

# system imports
#
import json
import argparse
from os import listdir, remove, rmdir
import sys
import uuid


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
from ioccc_common import *


# iocccpassword version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.2 2024-10-28"


def main():
    """
    Main routine when run as a program.
    """

    # setup
    #
    now = datetime.now(timezone.utc)
    force_pw_change = False
    password = None
    disable_login = False
    pw_change_by = None
    program = os.path.basename(__file__)
    admin = False
    start_given = False
    start_datetime = None
    stop_given = False
    stop_datetime = None

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="Manage IOCCC submit server password file and state file",
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
                        action='store_true')
    parser.add_argument('-g', '--grace',
                        help='grace time in seconds from to change the password' + \
                             f'(def: {DEFAULT_GRACE_PERIOD} seconds):',
                        metavar='SECS',
                        type=int,
                        nargs=1)
    parser.add_argument('-n', '--nologin',
                        help='disable login (def: login not explicitly disabled)',
                        action='store_true')
    parser.add_argument('-A', '--admin',
                        help='user is an admin (def: not an admin)',
                        action='store_true')
    parser.add_argument('-U', '--UUID',
                        help='generate a new UUID username and password',
                        action='store_true')
    parser.add_argument('-s', '--start',
                        help="set IOCCC start date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
                        nargs=1)
    parser.add_argument('-S', '--stop',
                        help="set IOCCC stop date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format",
                        metavar='DateTime',
                        nargs=1)
    args = parser.parse_args()

    # -c - force user to change their password at the next login
    #
    if args.change:

        # require the password to change at first login
        #
        force_pw_change = True

        # -g secs - set the grace time to change in seconds from now
        #
        if args.grace:
            pw_change_by = str(now + timedelta(seconds=args.grace[0]))

        # otherwise set the grace time using the default grace period
        #
        else:
            pw_change_by = str(now + timedelta(seconds=DEFAULT_GRACE_PERIOD))

    # -p password - use password supplied in the command line
    #
    if args.password:
        password = args.password[0]

    # -n - disable login of user
    #
    if args.nologin:
        disable_login = True

    # -A - disable login of user
    #
    if args.admin:
        admin = True

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

        # if -s DateTime was not given, obtain the current start date
        #
        if not start_given:
            start_datetime, _ = read_state()
            if not start_datetime:
                print("ERROR: unable to fetch of start date: <<" + return_last_errmsg() + ">>")
                sys.exit(3)

        # if -S DateTime was not given, obtain the current stop date
        #
        if not stop_given:
            _, stop_datetime = read_state()
            if not stop_datetime:
                print("ERROR: unable to fetch of stop date: <<" + return_last_errmsg() + ">>")
                sys.exit(4)

        # update the start and/or stop dates
        #
        if not update_state(str(start_datetime), str(stop_datetime)):
            print("ERROR: failed to update start and/or stop  date(s): <<" + return_last_errmsg() + ">>")
            sys.exit(5)
        else:
            print("Notice: set start: " + str(start_datetime) + " stop: " + str(stop_datetime))
            sys.exit(0)


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
        if not pwhash:
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(6)

        # determine the username to add
        #
        username = args.add[0]

        # the user must not already exist
        #
        if lookup_username(username):
            print("ERROR: username already exists: <<" + username + ">>")
            sys.exit(7)

        # add the user
        #
        if update_username(username, pwhash, admin, force_pw_change, pw_change_by, disable_login):
            print("Notice: added username: " + username + " password: " + password)
            sys.exit(0)
        else:
            print("ERROR: failed to add username: <<" + username + ">> password: <<" + password + ">>")
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
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
        if not pwhash:
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(9)

        # determine the username to update
        #
        username = args.update[0]

        # update the user
        #
        if update_username(username, pwhash, admin, force_pw_change, pw_change_by, disable_login):
            print("Notice: updated username: " + username + " password: " + password)
            sys.exit(0)
        else:
            print("ERROR: failed to update username: <<" + username + ">> password: <<" + password + ">>")
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(10)

    # -d user - delete user
    #
    if args.delete:

        # determine the username to delete
        #
        username = args.delete[0]

        # the user must already exist
        #
        if not lookup_username(username):
            print("ERROR: username does not exist: <<" + username + ">>")
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(11)

        # remove the user
        #
        if delete_username(username):
            print("Notice: deleted username: " + username)
            sys.exit(0)
        else:
            print("ERROR: failed to delete username: <<" + username + ">>")
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(12)

    # -a user - add user if they do not already exist
    #
    if args.UUID:

        # add with random password unless we used -p password
        #
        if not password:
            password = generate_password()

        # we store the hash of the password only
        #
        pwhash = hash_password(password)
        if not pwhash:
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(13)

        # generate an random UUID of type that is not an existing user
        #
        # We try a number of times until we find a new username, or
        # we give up trying.  More likely this loop will run only once
        # because the change of a duplicate UUID being found it nil.
        #
        username = None
        try_limit = 10
        for i in range(0, try_limit, 1):

            # try a new UUID
            #
            username = str(uuid.uuid4())

            # the user must not already exist
            #
            if not lookup_username(username):

                # new user was found
                #
                break

            # super rare case that we found an existing UUID, so try again
            #
            print("Notice: rare: UUID retry " + str(i+1) + " of " + str(try_limit))
            username = None

        # paranoia - no unique username was found
        #
        if not username:
            print("ERROR: SUPER RARE: failed to found a new UUID after " + str(try_limit) + " attempts!!!")
            sys.exit(14)

        # add the user
        #
        if update_username(username, pwhash, admin, force_pw_change, pw_change_by, disable_login):
            print("Notice: UUID username: " + username + " password: " + password)
            sys.exit(0)
        else:
            print("ERROR: failed to add UUID username: <<" + username + ">> password: <<" + password + ">>")
            print("ERROR: last_errmsg: <<" + return_last_errmsg() + ">>")
            sys.exit(15)

    # no option selected
    #
    print("ERROR: must use one of: -a USER or -u USER or -d USER or -U or -s DateTime or -S DateTime")
    sys.exit(16)

if __name__ == '__main__':
    main()
