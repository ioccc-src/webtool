#!/usr/bin/env python3
# pylint: disable=import-error
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
# pylint: disable=unused-import
"""
Functions to implement adding, updating and deleting of IOCCC contestants.
"""

# system imports
#
import sys
import json
import argparse
from os import listdir, remove, rmdir
import uuid


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
# TO DO: Change wild card import into specific import set
#
from ioccc_common import *


# ioccc_passwd.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.5 2024-11-22"


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
#
def main():
    """
    Main routine when run as a program.
    """

    # setup
    #
    now = datetime.now(timezone.utc)
    force_pw_change = False
    password = None
    pwhash = None
    disable_login = False
    pw_change_by = None
    program = os.path.basename(__file__)
    admin = False

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
                        help='grace seconds to change the password ' + \
                             f'(def: {DEFAULT_GRACE_PERIOD})',
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
    args = parser.parse_args()

    # -g secs - set the grace time to change in seconds from now
    #
    if args.grace:
        pw_change_by = str(now + timedelta(seconds=args.grace[0]))

    # -c - force user to change their password at the next login
    #
    if args.change:

        # require the password to change at first login
        #
        force_pw_change = True

        # case: -g not give, assume default grace period
        #
        if not args.grace:
            pw_change_by = str(now + timedelta(seconds=DEFAULT_GRACE_PERIOD))

    # -p password - use password supplied in the command line
    #
    if args.password:
        password = args.password[0]
        pwhash = hash_password(password)

    # -n - disable login of user
    #
    if args.nologin:
        disable_login = True

    # -A - make the user an admin
    #
    # NOTE: The admin state is currently unused.  Setting this has no effect
    #       other than to change the state of the user's password entry.
    #
    if args.admin:
        admin = True

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

        # determine the username to update
        #
        username = args.update[0]

        # obtain the user_dict if the user exists
        #
        user_dict = lookup_username(username)

        # if this is an existing user, setup for the update
        #
        if user_dict:

            # case: -p was not given, keep the existing password hash
            #
            if not password:
                pwhash = user_dict['pwhash']

            # case: -A was not given, keep the existing admin
            #
            if not args.admin:
                admin = user_dict['admin']

            # case: -c was not given, keep the existing force_pw_change
            #
            if not args.change:
                force_pw_change = user_dict['force_pw_change']

            # case: -c nor -g was not given, keep the existing pw_change_by
            #
            if not pw_change_by:
                pw_change_by = user_dict['pw_change_by']

            # case: -n was not given, keep the existing disable_login
            #
            if not args.nologin:
                disable_login = user_dict['disable_login']

        # if not yet a user, generate the random password unless we used -p password
        #
        else:

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

        # update the user
        #
        if update_username(username, pwhash, admin, force_pw_change, pw_change_by, disable_login):
            if password:
                print("Notice: updated username: " + username + " password: " + password)
            else:
                print("Notice: updated username: " + username + " password is unchanged")
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
#
# pylint: enable=too-many-locals
# pylint: enable=too-many-branches
# pylint: enable=too-many-statements

if __name__ == '__main__':
    main()
