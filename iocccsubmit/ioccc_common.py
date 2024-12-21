#!/usr/bin/env python3
#
# pylint: disable=too-many-lines
#
"""
Common support / utility functions needed by the IOCCC Submit Server
and related tools.

IMPORTANT NOTE: This code must NOT assume the use of Flask, nor call
                functions such as flash().  This code may be imported
                into utility functions that are command line and not
                web app related.

IMPORTANT NOTE: To return an error message to a caller, set: ioccc_last_errmsg
"""

# import modules
#
import sys
import re
import json
import os
import inspect
import string
import secrets
import random
import shutil
import hashlib
import uuid
import logging


# import from modules
#
from string import Template
from os import makedirs, umask
from datetime import datetime, timezone
from pathlib import Path
from random import randrange
from logging.handlers import SysLogHandler


# For user locking
#
# We use the python filelock module.  See:
#
#    https://pypi.org/project/filelock/
#    https://py-filelock.readthedocs.io/en/latest/api.html
#    https://snyk.io/advisor/python/filelock/example
#
from filelock import Timeout, FileLock


# 3rd party imports
#
from werkzeug.security import check_password_hash, generate_password_hash


##################
# Global constants
##################

# ioccc_common.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION_IOCCC_COMMON = "2.1.1 2024-12-20"

# force password change grace time
#
# Time in seconds from when force_pw_change is set to true that the
# user must login and change their password.
#
# If "force_pw_change" is "true", then login is denied if now > pw_change_by.
#
DEFAULT_GRACE_PERIOD = 72*3600

# standard date string in strptime format
#
# The string produced by:
#
#   datetime.now(timezone.utc)
#
# my be converted back into a datetime object by this strptime format string.
#
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"

# IP and port when running this code from the command line.
#
# When this code be being run under Apache, the wsgi module takes
# care of the hostname and port and this these two settings do not apply.
#
HOST_NAME = "127.0.0.1"
TCP_PORT = "8191"

# determine the default APPDIR
#
# case: We have template sub-directory, assume our APPDIR is .
#       (likely testing from the command line)
#
if Path("./templates").is_dir():
    APPDIR = "."

# case: assume are are running under the Apache server, and
#       APPDIR is /var/ioccc
#
# Tests suggest that Apache seems to run applications from the / directory.
#
else:
    APPDIR = "/var/ioccc"

# important directories and files that are relative to APPDIR
#
# We set FOO_RELATIVE_PATH, the value relative to APPDIR, and
# then set FOO to be APPDIR + "/" + FOO_RELATIVE_PATH.
#
# IMPORTANT NOTE: Calling change_startup_appdir(topdir) can
#                 change APPDIR and all of the values below
#                 that depend on APPDIR.
#
PW_FILE_RELATIVE_PATH = "etc/iocccpasswd.json"
PW_FILE = APPDIR + "/" + PW_FILE_RELATIVE_PATH
#
INIT_PW_FILE_RELATIVE_PATH = "etc/init.iocccpasswd.json"
INIT_PW_FILE = APPDIR + "/" + INIT_PW_FILE_RELATIVE_PATH
#
PW_LOCK_RELATIVE_PATH = "etc/iocccpasswd.lock"
PW_LOCK = APPDIR + "/" + PW_LOCK_RELATIVE_PATH
#
ADM_FILE_RELATIVE_PATH = "etc/admins.json"
ADM_FILE = APPDIR + "/" + ADM_FILE_RELATIVE_PATH
#
SECRET_FILE_RELATIVE_PATH = "etc/.secret"
SECRET_FILE = APPDIR + "/" + SECRET_FILE_RELATIVE_PATH
#
USERS_DIR_RELATIVE_PATH = "users"
USERS_DIR = APPDIR + "/" + USERS_DIR_RELATIVE_PATH
#
STATE_FILE_RELATIVE_PATH = "etc/state.json"
STATE_FILE = APPDIR + "/" + STATE_FILE_RELATIVE_PATH
#
INIT_STATE_FILE_RELATIVE_PATH = "etc/init.state.json"
INIT_STATE_FILE = APPDIR + "/" + INIT_STATE_FILE_RELATIVE_PATH
#
STATE_FILE_LOCK_RELATIVE_PATH = "etc/state.lock"
STATE_FILE_LOCK = APPDIR + "/" + STATE_FILE_LOCK_RELATIVE_PATH
#
PW_WORDS_RELATIVE_PATH = "etc/pw.words"
PW_WORDS = APPDIR + "/" + PW_WORDS_RELATIVE_PATH

# POSIX safe filename regular expression
#
POSIX_SAFE_RE = "^[0-9A-Za-z][0-9A-Za-z._+-]*$"

# slot related JSON values
#
NO_COMMENT_VALUE = "mandatory comment: because comments were removed from the original JSON spec"
SLOT_VERSION_VALUE = "1.1 2024-10-13"
EMPTY_JSON_SLOT_TEMPLATE = '''{
    "no_comment": "$NO_COMMENT_VALUE",
    "slot_JSON_format_version":  "$SLOT_VERSION_VALUE",
    "slot": $slot_num,
    "filename": null,
    "length": null,
    "date": null,
    "sha256": null,
    "status": "slot is empty"
}'''

# password related JSON values
#
PASSWORD_VERSION_VALUE = "1.1 2024-10-18"

# state (open and close) related JSON values
#
STATE_VERSION_VALUE = "1.1 2024-10-27"
DEFAULT_JSON_STATE_TEMPLATE = '''{
    "no_comment": "$NO_COMMENT_VALUE",
    "state_JSON_format_version": "$STATE_VERSION_VALUE",
    "open_date": "$OPEN_DATE",
    "close_date": "$CLOSE_DATE"
}'''

# password rules
#
# For password rule guidance, see:
#
#    https://pages.nist.gov/800-63-4/sp800-63b.html
#    https://cybersecuritynews.com/nist-rules-password-security/
#
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 64

# Full path of the startup current working directory
#
STARTUP_CWD = os.getcwd()

# determine the default Pwned password tree
#
# If we have a pwned.pw.tree directory (or symlink to a directory) under the current
# working directory (i.e., "." but using the full path).
#
if Path(f"{STARTUP_CWD}/pwned.pw.tree").is_dir():
    PWNED_PW_TREE = f"{STARTUP_CWD}/pwned.pw.tree"

# Otherwise if we have a pwned.pw.tree directory (or symlink to a directory) under APPDIR,
# then use that as Pwned password tree.
#
elif Path(f"{APPDIR}/pwned.pw.tree").is_dir():
    PWNED_PW_TREE = f"{APPDIR}/pwned.pw.tree"

# Assume the system default Pwned password
#
# This tree was downloaded by:
#
#   /usr/local/bin/pwned-pw-download /usr/local/share/pwned.pw.tree
#
# where /usr/local/bin/pwned-pw-download was installed from:
#
#   https://github.com/lcn2/pwned-pw-download
#
else:
    PWNED_PW_TREE = "/usr/local/share/pwned.pw.tree"

# length of a SHA1 hash in ASCII hex characters
#
SHA1_HEXLEN = 40

# slot numbers from 0 to MAX_SUBMIT_SLOT
#
# IMPORTANT:
#
# The MAX_SUBMIT_SLOT must match MAX_SUBMIT_SLOT define found in this file
#
#   soup/limit_ioccc.h
#
# from the mkiocccentry GitHub repo.  See:
#
#   https://github.com/ioccc-src/mkiocccentry/blob/master/soup/limit_ioccc.h
#
MAX_SUBMIT_SLOT = 9

# compressed tarball size limit in bytes
#
# IMPORTANT:
#
# The MAX_TARBALL_LEN must match MAX_TARBALL_LEN define found in this file
#
#   soup/limit_ioccc.h
#
# from the mkiocccentry GitHub repo.  See:
#
#   https://github.com/ioccc-src/mkiocccentry/blob/master/soup/limit_ioccc.h
#
MAX_TARBALL_LEN = 3999971

# Lock timeout in seconds
#
LOCK_TIMEOUT = 13


# lock state - lock file descriptor or none
#
# When ioccc_last_lock_fd is not none, flock is holding a lock on the file ioccc_last_lock_path.
# When ioccc_last_lock_fd is none, no flock is currently being held.
#
# When we try lock a file via ioccc_file_lock() and we are holding a lock on another file,
# we will force the flock to be released.
#
# The lock file only needs to be locked during a brief operation,
# which are brief in duration.  Moreover this server is NOT multi-threaded.
# We NEVER want to lock more than one file at a time.
#
# Nevertheless if, before we start, say. a slot operation AND before we attempt
# to lock the slot lock file, we discover that some other file is still locked
# (due to unexpected asynchronous event or exception, or code bug), we
# will force that previous lock to be unlocked.
#
# pylint: disable-next=global-statement,invalid-name
ioccc_last_lock_fd = None         # lock file descriptor, or None
# pylint: disable-next=global-statement,invalid-name
ioccc_last_lock_path = None       # path of the file that is locked, or None
# pylint: disable-next=global-statement,invalid-name
ioccc_last_errmsg = ""            # recent error message or empty string
# pylint: disable-next=global-statement,invalid-name
ioccc_pw_words = []


# IOCCC logger - how we log events
#
# When IOCCC_LOGGER is None, no logging is performed,
# otherwise IOCCC_LOGGER is a logging facility setup via setup_logger(string).
#
# NOTE: Until setup_logger(Bool) is called, IOCCC_LOGGER is None,
#       and no logging will occur.
#
IOCCC_LOGGER = None


def return_last_errmsg():
    """
    Return the recent error message or empty string

    Returns:
        ioccc_last_errmsg as a string
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg

    # paranoia - if ioccc_last_errmsg is not a string, return as string version
    #
    if not isinstance(ioccc_last_errmsg, str):
        ioccc_last_errmsg = str(ioccc_last_errmsg)

    # return string
    #
    return ioccc_last_errmsg


def change_startup_appdir(topdir):
    """
    Change the path to the app directory from the APPDIR default.
    Modify paths to all other files and directories used in this file.

    NOTE: It is important that this function be called early AND
          before other functions in this file that use directories
          and files, are called.  Calling this function after other functions
          are called could lead to unpredictable and undesirable results!

    Given:
        topdir  path to the app directory

    Returns:
        True ==> paths successfully changed
        False ==> app directory not found, or
                  topdir is not a string argument
    """

    # setup
    #
    # pylint: disable=global-statement
    global ioccc_last_errmsg
    global APPDIR
    global PW_FILE
    global INIT_PW_FILE
    global PW_LOCK
    global ADM_FILE
    global SECRET_FILE
    global USERS_DIR
    global STATE_FILE
    global INIT_STATE_FILE
    global STATE_FILE_LOCK
    global PW_WORDS
    # pylint: enable=global-statement
    me = inspect.currentframe().f_code.co_name

    # paranoia - if ioccc_last_errmsg is not a string, return as string version
    #
    if not isinstance(topdir, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": topdir arg is not a string"
        return False

    # topdir must be a directory
    #
    if not Path(topdir).is_dir():
        ioccc_last_errmsg = "ERROR: in " + me + ": topdir is not a directory: " + topdir
        return False

    # now modify paths to all other files and directories used in this file
    #
    # pylint: disable=redefined-outer-name
    #
    APPDIR = topdir
    #
    PW_FILE = topdir + "/" + PW_FILE_RELATIVE_PATH
    INIT_PW_FILE = topdir + "/" + INIT_PW_FILE_RELATIVE_PATH
    PW_LOCK = topdir + "/" + PW_LOCK_RELATIVE_PATH
    ADM_FILE = topdir + "/" + ADM_FILE_RELATIVE_PATH
    SECRET_FILE = topdir + "/" + SECRET_FILE_RELATIVE_PATH
    USERS_DIR = topdir + "/" + USERS_DIR_RELATIVE_PATH
    STATE_FILE = topdir + "/" + STATE_FILE_RELATIVE_PATH
    INIT_STATE_FILE = topdir + "/" + INIT_STATE_FILE_RELATIVE_PATH
    STATE_FILE_LOCK = topdir + "/" + STATE_FILE_LOCK_RELATIVE_PATH
    PW_WORDS = topdir + "/" + PW_WORDS_RELATIVE_PATH
    #
    # pylint: enable=redefined-outer-name

    # assume all is well
    #
    return True


def return_user_dir_path(username):
    """
    Return the user directory path

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> username is not POSIX safe
        != None ==> user directory path (which may not yet exist) for a user (which not yet exist)

    A useful side effect of this call is to verify that the username
    string is sane.  However, the username may not be a valid user
    nor may the user directory exist.  It is up to caller to check that.

    It is up the caller to create, if needed, the user directory.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        ioccc_last_errmsg = "ERROR: in " + me + ": username not POSIX safe: <<" + username + ">>"
        return None

    # return user directory path
    #
    user_dir = USERS_DIR + "/" + username
    return user_dir


def return_slot_dir_path(username, slot_num):
    """
    Return the slot directory path under a given user directory

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        None ==> invalid slot number or invalid user directory
        != None ==> slot directory path (may not yet exist)

    It is up the caller to create, if needed, the slot directory.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - must make a user_dir value
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # paranoia - must be a valid slot number
    #
    if (slot_num < 0 or slot_num > MAX_SUBMIT_SLOT):
        ioccc_last_errmsg = "ERROR: in " + me + ": invalid slot number: " + str(slot_num) + \
                        " for username: <<" + username + ">>"
        return None

    # return slot directory path under a given user directory
    #
    slot_dir = user_dir + "/" + str(slot_num)
    return slot_dir


def return_slot_json_filename(username, slot_num):
    """
    Return the JSON filename for given slot directory of a given user directory

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        None ==> invalid slot number or invalid user directory
        != None ==> path of the JSON filename for this user's slot (may not yet exist)

    It is up the caller to create, if needed, the JSON filename.
    """

    # determine slot directory name
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        return None

    # determine the JSON filename for this given slot
    #
    slot_json_file = slot_dir + "/slot.json"
    return slot_json_file


def ioccc_file_lock(file_lock):
    """
    Lock a file

    A side effect of locking a file is that the file will be created with
    more 0664 it it does not exist.

    Given:
        file_lock               the filename to lock

        If the filename does not exist, it will be created.
        If another file is currently unlocked, force the older lock to be unlocked.
        Lock the new file.
        Register the lock.

    Returns:
        lock file descriptor    lock successful
        None                    lock not successful, or
                                unable to create the lock file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_lock_fd
    # pylint: disable-next=global-statement
    global ioccc_last_lock_path
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # be sure the lock file exists
    #
    try:
        Path(file_lock).touch(mode=0o664, exist_ok=True)

    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": failed touch (mode=0o664, exist_ok=True): " + file_lock + \
                      " exception: " + str(errcode)
        return None

    # Force any stale lock to become unlocked
    #
    if ioccc_last_lock_fd:

        # Carp
        #
        if not ioccc_last_lock_path:
            ioccc_last_lock_path = "((no-ioccc_last_lock_path))"
        ioccc_last_errmsg = "Warning: in " + me + ": forcing stale unlock: " + ioccc_last_lock_path

        # Force previous stale lock to become unlocked
        #
        try:
            ioccc_last_lock_fd.release(force=True)

        except OSError as errcode:
            # We give up as we cannot force the unlock
            #
            ioccc_last_errmsg = "Warning: in " + me + ": failed to force stale unlock: " + ioccc_last_lock_path + \
                          " exception: " + str(errcode)

        # clear the past lock
        #
        ioccc_last_lock_fd = None
        ioccc_last_lock_path = None

    # Lock the file
    #
    try:
        with FileLock(file_lock, timeout=LOCK_TIMEOUT, is_singleton=True) as lock_fd:

            # note our new lock
            #
            ioccc_last_lock_fd = lock_fd
            ioccc_last_lock_path = file_lock

    except Timeout:

        # too too long to get the lock
        #
        ioccc_last_errmsg = "Warning: in " + me + ": timeout on lock for: " + ioccc_last_lock_path
        return None

    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + \
                            ": failed to FileLock(file_lock, timeout=LOCK_TIMEOUT, is_singleton=True): " + \
                            file_lock + " exception: " + str(errcode)
        return None

    # return the lock success
    #
    return lock_fd


def ioccc_file_unlock():
    """
    unlock a previously locked file

    A file locked via ioccc_file_lock(file_lock) is unlocked using the last registered lock.

    Returns:
        True     previously locked file has been unlocked
        False    failed to unlock the previously locked file, or
                 no file was previously locked
    """

    # declare global use
    #
    # pylint: disable-next=global-statement
    global ioccc_last_lock_fd
    # pylint: disable-next=global-statement
    global ioccc_last_lock_path
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # case: no file was previously unlocked
    #
    sucess = False
    if not ioccc_last_lock_fd:
        ioccc_last_errmsg = "Warning: in " + me + ": timeout on lock for: " + ioccc_last_lock_path

    # Unlock the file
    #
    else:
        try:
            ioccc_last_lock_fd.release(force=True)
            sucess = True

        except OSError as errcode:
            # We give up as we cannot force the unlock
            #
            ioccc_last_errmsg = "Warning: in " + me + ": failed to unlock: " + ioccc_last_lock_path + \
                          " exception: " + str(errcode)

    # Clear any previous lock
    #
    ioccc_last_lock_fd = None
    ioccc_last_lock_path = None

    # Return the unlock success or failure
    #
    return sucess


def load_pwfile():
    """
    Return the JSON contents of the password file as a python dictionary

    Obtain a lock for password file before opening and reading the password file.
    We release the lock for the password file afterwards.

    Returns:
        None ==> unable to read the JSON in the password file
        != None ==> password file contents as a python dictionary
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # Lock the password file
    #
    pw_lock_fd = ioccc_file_lock(PW_LOCK)
    if not pw_lock_fd:
        return None

    # If there is no password file, or if the password file is empty, copy it from the initial password file
    #
    if not os.path.isfile(PW_FILE) or os.path.getsize(PW_FILE) <= 0:
        try:
            shutil.copy2(INIT_PW_FILE, PW_FILE, follow_symlinks=True)
        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + " #0: cannot cp -p " + INIT_PW_FILE + \
                            " " + PW_FILE + " exception: " + str(errcode)
            ioccc_file_unlock()
            return None

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close and unlock the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
                # fall thru

    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " errcode: " + str(errcode)
        # fall thru

        # we have no JSON to return
        #
        pw_file_json = None

    # return the password JSON data as a python dictionary
    #
    ioccc_file_unlock()
    return pw_file_json


def replace_pwfile(pw_file_json):
    """
    Replace the contents of the password file

    Obtain a lock for password file before opening and writing JSON to the password file.
    We release the lock for the password file afterwards.

    Given:
        pw_file_json    JSON to write into the password file as a python dictionary

    Returns:
        False ==> unable to write JSON into the password file
        True ==> password file was successfully updated
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # Lock the password file
    #
    pw_lock_fd = ioccc_file_lock(PW_LOCK)
    if not pw_lock_fd:
        return False

    # rewrite the password file with the pw_file_json and unlock
    #
    try:
        with open(PW_FILE, mode="w", encoding="utf-8") as j_pw:
            j_pw.write(json.dumps(pw_file_json, ensure_ascii=True, indent=4))
            j_pw.write('\n')

            # close and unlock the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
                return False

    except OSError:

        # unlock the password file
        #
        ioccc_last_errmsg = "ERROR: in " + me + ": unable to write password file"
        ioccc_file_unlock()
        return False

    # password file updated
    #
    ioccc_file_unlock()
    return True


# pylint: disable=too-many-return-statements
#
def validate_user_dict(user_dict):
    """
    Perform sanity checks on user information for username from password file

    Given:
        user_dict    user information as a python dictionary

    Returns:
        True ==> no error found with in user information
        False ==> a problem was found with user JSON information
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # sanity check argument
    #
    if not isinstance(user_dict, dict):
        ioccc_last_errmsg = "ERROR: in " + me + ": user_dict arg is not a python dictionary"
        return False

    # obtain the username
    #
    if not isinstance(user_dict['username'], str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username is not a string: <<" + str(user_dict['username']) + ">>"
        return False
    username = user_dict['username']

    # sanity check the information for user
    #
    if user_dict["no_comment"] != NO_COMMENT_VALUE:
        ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON no_comment username : <<" + \
                            username + ">>"
        return False
    if user_dict["iocccpasswd_format_version"] != PASSWORD_VERSION_VALUE:
        ioccc_last_errmsg = "ERROR: in " + me + ": invalid iocccpasswd_format_version for username : <<" + \
                            username + ">>"
        return False
    if not user_dict['pwhash']:
        ioccc_last_errmsg = "ERROR: in " + me + ": no pwhash for username : <<" + \
                            username + ">>"
        return False
    if not isinstance(user_dict['pwhash'], str):
        ioccc_last_errmsg = "ERROR: in " + me + ": pwhash is not a string for username : <<" + \
                            username + ">>"
        return False
    if not isinstance(user_dict['admin'], bool):
        ioccc_last_errmsg = "ERROR: in " + me + ": admin is not a boolean for username : <<" + \
                            username + ">>"
        return False
    if not isinstance(user_dict['force_pw_change'], bool):
        ioccc_last_errmsg = "ERROR: in " + me + ": force_pw_change is not a boolean for username : <<" + \
                            username + ">>"
        return False
    if user_dict['pw_change_by'] and not isinstance(user_dict['pw_change_by'], str):
        ioccc_last_errmsg = "ERROR: in " + me + ": pw_change_by is not string nor None for username : <<" + \
                            username + ">>"
        return False
    if not isinstance(user_dict['disable_login'], bool):
        ioccc_last_errmsg = "ERROR: in " + me + ": disable_login is not a boolean for username : <<" + \
                            username + ">>"
        return False

    # user information passed the sanity checks
    #
    return True
#
# pylint: enable=too-many-return-statements


def lookup_username(username):
    """
    Return JSON information for username from password file as a python dictionary

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> no such username, or
                 username does not match POSIX_SAFE_RE, or
                 bad password file
        != None ==> user information as a python dictionary
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        ioccc_last_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return None

    # load JSON from the password file as a python dictionary
    #
    pw_file_json = load_pwfile()
    if not pw_file_json:
        return None

    # search the password file for the user
    #
    user_dict = None
    for i in pw_file_json:
        if i['username'] == username:
            user_dict = i
            break
    if not user_dict:
        ioccc_last_errmsg = "ERROR: in " + me + ": unknown username: <<" + username + ">>"
        return None

    # sanity check the user information for user
    #
    if not validate_user_dict(user_dict):
        return None

    # return user information for user in the form of a python dictionary
    #
    return user_dict


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-arguments
#
def update_username(username, pwhash, admin, force_pw_change, pw_change_by, disable_login):
    """
    Update a username entry in the password file, or add the entry
    if the username is not already in the password file.

    Given:
        username            IOCCC submit server username
        pwhash              hashed password as generated by hash_password()
        admin               boolean indicating if the user is an admin
        force_pw_change     boolean indicating if the user will be forced to change their password on next login
        pw_change_by        date and time string in DATETIME_FORMAT by which password must be changed, or
                            None ==> no deadline for changing password
        disable_login       boolean indicating if the user is banned from login

    Returns:
        False ==> unable to update user in the password file
        True ==> user updated, or
                 added to the password file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": username arg is not a string: <<" + str(username) + ">>"
        return False
    if not re.match(POSIX_SAFE_RE, username):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": username is not POSIX safe: <<" + username + ">>"
        return False

    # paranoia - pwhash must be a string
    #
    if not isinstance(pwhash, str):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": pwhash arg is not a string for username : <<" + username + ">>"
        return False

    # paranoia - admin must be a boolean
    #
    if not isinstance(admin, bool):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": admin arg is not a boolean for username : <<" + username + ">>"
        return False

    # paranoia - force_pw_change must be a boolean
    #
    if not isinstance(force_pw_change, bool):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": force_pw_change arg is not a boolean for username : <<" + username + ">>"
        return False

    # paranoia - pw_change_by must None or must be be string
    #
    if not isinstance(pw_change_by, str) and pw_change_by is not None:
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": pw_change_by arg is not a string nor None for username : <<" + username + ">>"
        return False

    # paranoia - disable_login must be a boolean
    #
    if not isinstance(disable_login, bool):
        ioccc_last_errmsg = "ERROR: in " + me + \
                        ": disable_login arg is not a boolean for username : <<" + username + ">>"
        return False

    # Lock the password file
    #
    pw_lock_fd = ioccc_file_lock(PW_LOCK)
    if not pw_lock_fd:
        return False

    # If there is no password file, or if the password file is empty, copy it from the initial password file
    #
    if not os.path.isfile(PW_FILE) or os.path.getsize(PW_FILE) <= 0:
        try:
            shutil.copy2(INIT_PW_FILE, PW_FILE, follow_symlinks=True)
        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + " #1: cannot cp -p " + INIT_PW_FILE + \
                            " " + PW_FILE + " exception: " + str(errcode)
            ioccc_file_unlock()
            return False

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
                return False

    except OSError as errcode:

        # unlock the password file
        #
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " exception: " + str(errcode)
        ioccc_file_unlock()
        return False

    # scan through the password file, looking for the user
    #
    found_username = False
    for i in pw_file_json:
        if i['username'] == username:

            # user found, update user info
            #
            i['pwhash'] = pwhash
            i['admin'] = admin
            i['force_pw_change'] = force_pw_change
            i['pw_change_by'] = pw_change_by
            i['disable_login'] = disable_login
            found_username = True
            break

    # the user is new, add the user to the JSON from the password file
    #
    if not found_username:

        # append the new user to the password file
        #
        pw_file_json.append({ "no_comment" : NO_COMMENT_VALUE, \
                              "iocccpasswd_format_version" : PASSWORD_VERSION_VALUE, \
                              "username" : username, \
                              "pwhash" : pwhash, \
                              "admin" : admin, \
                              "force_pw_change" : force_pw_change, \
                              "pw_change_by" : pw_change_by, \
                              "disable_login" : disable_login })

    # rewrite the password file with the pw_file_json and unlock
    #
    try:
        with open(PW_FILE, mode="w", encoding="utf-8") as j_pw:
            j_pw.write(json.dumps(pw_file_json, ensure_ascii=True, indent=4))
            j_pw.write('\n')

            # close and unlock the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
                return False

    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": unable to write password file" + \
                        " exception: " + str(errcode)

        # unlock the password file
        #
        ioccc_file_unlock()
        return False

    # password updated with new username information
    #
    ioccc_file_unlock()
    return True
#
# pylint: enable=too-many-statements
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements
# pylint: enable=too-many-positional-arguments
# pylint: enable=too-many-arguments


# pylint: disable=too-many-return-statements
#
def delete_username(username):
    """
    Remove a username from the password file

    Given:
        username    IOCCC submit server username to remove

    Returns:
        None ==> no such username, or
                 username does not match POSIX_SAFE_RE, or
                 bad password file
        != None ==> removed user information as a python dictionary
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        ioccc_last_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return None

    # Lock the password file
    #
    pw_lock_fd = ioccc_file_lock(PW_LOCK)
    if not pw_lock_fd:
        return None

    # If there is no password file, or if the password file is empty, copy it from the initial password file
    #
    if not os.path.isfile(PW_FILE) or os.path.getsize(PW_FILE) <= 0:
        try:
            shutil.copy2(INIT_PW_FILE, PW_FILE, follow_symlinks=True)
        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + " #2: cannot cp -p " + INIT_PW_FILE + \
                            " " + PW_FILE + " exception: " + str(errcode)
            ioccc_file_unlock()
            return None

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
            return None

    except OSError as errcode:

        # unlock the password file
        #
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " exception: " + str(errcode)
        ioccc_file_unlock()
        return None

    # scan through the password file, looking for the user
    #
    deleted_user = None
    new_pw_file_json = []
    for i in pw_file_json:

        # set aside the username we are deleting
        #
        if i['username'] == username:
            deleted_user = i

        # otherwise save other users
        #
        else:
            new_pw_file_json.append(i)

    # rewrite the password file with the pw_file_json and unlock
    #
    try:
        with open(PW_FILE, mode="w", encoding="utf-8") as j_pw:
            j_pw.write(json.dumps(new_pw_file_json, ensure_ascii=True, indent=4))
            j_pw.write('\n')

            # close and unlock the password file
            #
            try:
                j_pw.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_FILE + \
                                    " exception: " + str(errcode)
            return None

    except OSError as errcode:

        # unlock the password file
        #
        ioccc_last_errmsg = "ERROR: in " + me + ": unable to write password file" + \
                        " exception: " + str(errcode)
        ioccc_file_unlock()
        return None

    # return the user that was deleted, if they were found
    #
    ioccc_file_unlock()
    return deleted_user
#
# pylint: enable=too-many-return-statements


def generate_password():
    """
    Generate a random password.

    Returns:
        random password as a string
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_pw_words
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name
    blacklist = set('`"\\')
    punct = ''.join( c for c in string.punctuation if c not in blacklist )

    # load the word dictionary if it is empty
    #
    if not ioccc_pw_words:
        with open(PW_WORDS, "r", encoding="utf-8") as f:
            ioccc_pw_words = [word.strip() for word in f]
        try:
            f.close()
        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + PW_WORDS + \
                                " exception: " + str(errcode)
            # fall thru

    # generate a 2-word password with random separators and an f9.4 number
    #
    # Our dictionary has about 104944 (log2 ~ 16.68) words in it.
    # Our selected punctuation list as 30 (log2 ~ 4.91) characters.
    # We append a f9.4 (4 digits + . + 4 digits) number (log2 ~ 19.93).
    #
    # Typical entropy is about 63.10 bits:
    #
    #   log2(104944)*2 + log2(30)*2 + log2(1000) + log2(1000)
    #
    password = secrets.choice(ioccc_pw_words) + random.choice(punct) + secrets.choice(ioccc_pw_words)
    password = password + random.choice(punct) + str(randrange(1000)) + "." + str(randrange(1000))
    return password


def hash_password(password):
    """
    Convert a password into a hashed password.

    Given:
        password    password as a string

    Returns:
        hashed password string
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": password arg is not a string"
        return None

    return generate_password_hash(password)


def verify_hashed_password(password, pwhash):
    """
    Verify that password matches the hashed patches

    Given:
        password    plaintext password
        pwhash      hashed password

    Returns:
        True ==> password matches the hashed password
        False ==> password does NOT match the hashed password, or
                  a non-string args was found
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": password arg is not a string"
        return False

    # firewall - pwhash must be a string
    #
    if not isinstance(pwhash, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": pwhash arg is not a string"
        return False

    # return if the pwhash matches the password
    #
    return check_password_hash(pwhash, password)


def verify_user_password(username, password):
    """
    Verify a password for a given user

    Given:
        username    IOCCC submit server username
        password    plaintext password

    Returns:
        True ==> password matches the hashed password
        False ==> password does NOT match the hashed password, or
                  username is not in the password database, or
                  user is not allowed to login, or
                  a non-string args was found
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string"
        return False

    # firewall - password must be a string
    #
    if not isinstance(password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": password arg is not a string"
        return False

    # fail if user login is disabled or missing from the password file
    #
    user_dict = lookup_username(username)
    if not user_dict:

        # user is not in the password file, so we cannot state they have been disabled
        #
        return False

    # fail if the user is not allowed to login
    #
    if not user_allowed_to_login(user_dict):

        # user is not allowed to login
        #
        return False

    # return the result of the hashed password check for this user
    #
    return verify_hashed_password(password, user_dict['pwhash'])


# pylint: disable=too-many-return-statements
#
def is_pw_pwned(password):
    """
    Determine if a password has bee pwned by doing a lookup
    in the Pwned password tree.

    Given:
        password    plaintext password

    Returns:
        True ==> password found in the Pwned password tree with a pwned count > 0, or
                  failed to SHA-1 hash the password in UPPER CASE hex characters,
                  failed to open or read the required Pwned password tree file,
                  non-string arg was found
        False ==> password not found in the Pwned password tree, or
                  pwned count <= 0

    Regarding the Pwned password tree:

    The pwned password tree has 4 levels.  Files are of the form:

        i/j/k/ikjxy

    where i, j, k, x, y are UPPER CASE hex digits:

        0 1 2 3 4 5 6 7 8 9 A B C D E F

    Each file is of the form:

    35-UPPER-CASE-HEX-digits, followed by a colon (":"), followed by an integer > 0

    For eample, all pwned passwords with a SHA-1 that begin with `12345` will be found in:

        1/2/3/12345

    NOTE: The first 1 SHA-1 HEX characters are duplicated in the 3 directory levels.

    Example: a line from 1/2/3/12345

    The 1/2/3/12345 file contains the following line:

        00772720168B19640759677862AD5350374:4

    The SHA-1 hash of the pwned password is the 1st 5 HEX digits from the file,
    plus the 35 hex digits of the line before the colon (":").  Thus the
    SHA-1 hash of the pwned password is:

        1234500772720168B19640759677862AD5350374

    The "4" after the colon (":") means that the given password has been pwned at
    least 4 times and should NOT be used.

    Consider the password:

        password

    The SHA-1 hash of "password" is:

        5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8

    Using the first 5 hex digits, open the file:

        5/B/A/5BAA6

    Using Unix tools, we can look for the remaining 35 hex digits followed by a ":"

        grep -F 1E4C9B93F3F0682250B6CF8331B7EE68FD8: 5/B/A/5BAA6

    This will produce the line:

        1E4C9B93F3F0682250B6CF8331B7EE68FD8:10437277

    This indicates that the password "`password`", has been pwned at least 10437277 times!
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": password arg is not a string"
        return True

    # compute the SHA-1 of the password in UPPER CASE hex
    #
    m = hashlib.sha1()
    if not m:
        ioccc_last_errmsg = "ERROR: in " + me + ": unable to form a context for SHA-1 hashing"
        return True
    m.update(bytes(password, 'utf-8'))
    sha1_hex = m.hexdigest().upper()
    if not sha1_hex or len(sha1_hex) != SHA1_HEXLEN:
        ioccc_last_errmsg = "ERROR: in " + me + ": SHA-1 hash return was invalid"
        return True

    # determine the Pwned password tree file we need to read
    #
    pwned_file = PWNED_PW_TREE + "/" + sha1_hex[0] + "/" + sha1_hex[1] + "/" + sha1_hex[2] + "/" + sha1_hex[0:5]
    #
    try:
        with open(pwned_file, 'r', encoding="utf8") as input_file:

            # read the lines in the Pwned password tree file
            #
            lines = input_file.readlines()

            # scan the Pwned password tree file for the hash
            #
            scan_for = sha1_hex[5:] + ":"
            for line in lines:
                if line.startswith(scan_for):
                    return True

    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": failed using: " + pwned_file + \
                            " exception: " + str(errcode)
        return True

    # As presume that the password is not Pwned
    #
    return False
#
# pylint: enable=too-many-return-statements


def is_proper_password(password):
    """
    Determine if a password is proper.  That is, if the password
    follows the rules for a good password that as not been pwned.

    For password rule guidance, see:

        https://pages.nist.gov/800-63-4/sp800-63b.html
        https://cybersecuritynews.com/nist-rules-password-security/

    Given:
        password    plaintext password

    Returns:
        True ==> password is allowed under the rules
        False ==> password is is not allowed, or
                  non-string arg was found
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": password arg is not a string"
        return False

    # password must be at at least MIN_PASSWORD_LENGTH long
    #
    if len(password) < MIN_PASSWORD_LENGTH:
        ioccc_last_errmsg = "ERROR: password must be at least " + str(MIN_PASSWORD_LENGTH) + \
                      " characters long"
        return False

    # password must be a sane length
    #
    if len(password) > MAX_PASSWORD_LENGTH:
        ioccc_last_errmsg = "ERROR: password must not be longer than " + str(MAX_PASSWORD_LENGTH) + \
                      " characters"
        return False

    # password must not have been Pwned
    #
    if is_pw_pwned(password):
        ioccc_last_errmsg = "ERROR: new password has been Pwned (compromised), please select a different new password"
        return False

    # until we have password rules, allow any string
    #
    return True


# pylint: disable=too-many-return-statements
#
def update_password(username, old_password, new_password):
    """
    Update the password for a given user.

    NOTE: If the user is allowed to login, and the old_password is the
          current password, and the new_password is an allowed password,
          we update the user's password AND clear any force_pw_change state.

    Given:
        username        IOCCC submit server username
        old_password    current plaintext password
        new_password    new plaintext password

    Returns:
        True ==> password updated
        False ==> old_password does NOT match the hashed password, or
                  non-string args was found, or
                  username is not in the password database, or
                  user is not allowed to login, or
                  new_password is not a valid password
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # firewall - password must be a string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string"
        return False

    # firewall - old_password must be a string
    #
    if not isinstance(old_password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": old_password arg is not a string"
        return False

    # firewall - new_password must be a string
    #
    if not isinstance(new_password, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": new_password arg is not a string"
        return False

    # new_password must be a proper password
    #
    if not is_proper_password(new_password):
        return False

    # fail if user login is disabled or missing from the password file
    #
    user_dict = lookup_username(username)
    if not user_dict:

        # user is not in the password file, so we cannot state they have been disabled
        #
        return False

    # fail if the user is not allowed to login
    #
    if not user_allowed_to_login(user_dict):

        # user is not allowed to login
        #
        return False

    # return the result of the hashed password check for this user
    #
    if not verify_hashed_password(old_password, user_dict['pwhash']):

        # old_password is not correct
        #
        ioccc_last_errmsg = "ERROR: invalid old password"
        return False

    # update user entry in the password database
    #
    # We force the force_pw_change state to be False as this action IS changing the password.
    #
    if not update_username(username,
                           hash_password(new_password),
                           user_dict['admin'],
                           False,
                           None,
                           user_dict['disable_login']):
        return False

    # password successfully updated
    #
    return True
#
# pylint: enable=too-many-return-statements


def user_allowed_to_login(user_dict):
    """
    Determine if the user has been disabled based on the username

    Given:
        user_dict    user information for username as a python dictionary

    Returns:
        True ==> user is allowed to login
        False ==> login is not allowed for the user, or
                  user_dict failed sanity checks, or
                  user is not allowed to login, or
                  user did not change their password in time
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg

    # sanity check the user information
    #
    if not validate_user_dict(user_dict):
        return False

    # deny login if disable_login is true
    #
    if user_dict['disable_login']:

        # login disabled
        #
        ioccc_last_errmsg = "ERROR: user login has been disabled"
        return False

    # deny login is the force_pw_change and we are beyond the pw_change_by time limit
    #
    if user_dict['force_pw_change'] and user_dict['pw_change_by']:

        # Convert pw_change_by into a datetime string
        #
        pw_change_by = datetime.strptime(user_dict['pw_change_by'], DATETIME_FORMAT)

        # determine the datetime of now
        #
        now = datetime.now(timezone.utc)

        # failed to change the password in time
        #
        if now > pw_change_by:
            ioccc_last_errmsg = "ERROR: user failed to change the password in time"
            return False

    # user login attempt is allowed
    #
    return True


def must_change_password(user_dict):
    """
    Determine if the user is required to change their password.

    Given:
        user_dict    user information for username as a python dictionary

    Returns:
        True ==> user must change their password
        False ==> user is not requited to change their password, or
                  invalid user_dict
    """

    # sanity check the user information
    #
    if not validate_user_dict(user_dict):
        return False

    return user_dict['force_pw_change']


def username_login_allowed(username):
    """
    Determine if the user has been disabled based on the username

    Given:
        username    IOCCC submit server username

    Returns:
        True        user is allowed to login
        False       username is not in the password file, or
                    username has been disabled in the password file, or
                    user did not change their password in time, or
                    username does not match POSIX_SAFE_RE
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return False
    if not re.match(POSIX_SAFE_RE, username):
        ioccc_last_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return False

    # fail if user login is disabled or missing from the password file
    #
    user_dict = lookup_username(username)
    if not user_dict:

        # user is not in the password file, so we cannot state they have been disabled
        #
        return False

    # determine, based on the user information, if the user is allowed to login
    #
    return user_allowed_to_login(user_dict)


# pylint: disable=too-many-return-statements
#
def lock_slot(username, slot_num):
    """
    lock a slot for a user

    A side effect of locking the slot is that the user directory will be created.
    A side effect of locking the slot is if another file is locked, that file will be unlocked.
    If it does not exist, and the slot directory for the user will be created.
    If it does not exist, and the lock file will be created .. unless we return None.

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        lock file descriptor    lock successful
        None                    lock not successful, or
                                invalid username, or
                                invalid slot_num
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name
    umask(0o022)

    # validate username and slot
    #
    if not lookup_username(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None
    slot_num_str = str(slot_num)
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        return None

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError:
        ioccc_last_errmsg = "ERROR: in " + me + ": failed to create for username: <<" + username + ">>"
        return None

    # be sure the slot directory exits
    #
    try:
        makedirs(slot_dir, mode=0o2770, exist_ok=True)
    except OSError:
        ioccc_last_errmsg = "ERROR: in " + me + ": failed to create slot: " + slot_num_str + \
                        "for username: <<" + username + ">>"
        return None

    # determine the lock filename
    #
    slot_file_lock = slot_dir + "/lock"

    # lock the slot
    #
    slot_lock_fd = ioccc_file_lock(slot_file_lock)

    # return the slot lock success or None
    #
    return slot_lock_fd
#
# pylint: enable=too-many-return-statements


def unlock_slot():
    """
    unlock a previously locked slot

    A slot locked via lock_slot(username, slot_num) is unlocked
    using the last_slot_lock that noted the slot lock descriptor.

    Returns:
        True    slot unlock successful
        False    failed to unlock slot
    """

    # clear any previous lock
    #
    return ioccc_file_unlock()


def write_slot_json(slots_json_file, slot_json):
    """
    Write out an index of slots for the user.

    Given:
        slots_json_file     JSON filename for a given slot
        slot_json           content for a given slot as a python dictionary

    Returns:
        True    slot JSON file updated
        False   failed to update slot JSON file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # write JSON file for slot
    #
    try:
        with open(slots_json_file, mode="w", encoding="utf-8") as slot_file_fp:
            slot_file_fp.write(json.dumps(slot_json, ensure_ascii=True, indent=4))
            slot_file_fp.write('\n')

            try:
                slot_file_fp.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + slots_json_file + \
                                    " exception: " + str(errcode)
            return False

    except OSError:
        ioccc_last_errmsg = "ERROR: failed to write out slot file: " + slots_json_file
        return False

    return True


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
#
def initialize_user_tree(username):
    """
    Initialize the directory tree for a given user

    We create the directory for the username if the directory does not exist.
    We create the slot for the username if the slot directory does not exist.
    We create the lock file for the slot it the lock file does not exist.
    We initialize the slot JSON file it the slot JSON file does not exist.

    NOTE: Because this may be called early, we cannot use HTML or other
          error carping delivery.  We only set last_excpt are return None.

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> invalid slot number or invalid user directory
        != None ==> array of slot user data as a python dictionary
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # setup
    #
    if not lookup_username(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return False
    umask(0o022)

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot form user directory for user: <<" + \
                        username + ">> exception: " + str(errcode)
        return None

    # process each slot for this user
    #
    slots = [None] * (MAX_SUBMIT_SLOT+1)
    for slot_num in range(0, MAX_SUBMIT_SLOT+1):

        # determine the slot directory
        #
        slot_dir = return_slot_dir_path(username, slot_num)
        if not slot_dir:
            return None
        slot_num_str = str(slot_num)

        # be sure the slot directory exits
        #
        try:
            makedirs(slot_dir, mode=0o2770, exist_ok=True)
        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": cannot form slot directory: " + \
                            slot_dir + " exception: " + str(errcode)
            return None

        # Lock the slot
        #
        # This will create the lock file if needed.
        #
        slot_lock_fd = lock_slot(username, slot_num)
        if not slot_lock_fd:
            return None

        # read the JSON file for the user's slot
        #
        # NOTE: We initialize the slot JSON file if the JSON file does not exist.
        #
        slot_json_file = return_slot_json_filename(username, slot_num)
        if not slot_json_file:
            unlock_slot()
            return None
        try:
            with open(slot_json_file, "r", encoding="utf-8") as slot_file_fp:
                slots[slot_num] = json.load(slot_file_fp)

                try:
                    slot_file_fp.close()
                except OSError as errcode:
                    ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + slot_json_file + \
                                        " exception: " + str(errcode)
                    return None

                if slots[slot_num]["no_comment"] != NO_COMMENT_VALUE:
                    ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #0 username : <<" + \
                                    username + ">> for slot: " + slot_num_str
                    unlock_slot()
                    return None

                if slots[slot_num]["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                    ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON slot_JSON_format_version #0"
                    unlock_slot()
                    return None

        except OSError:
            t = Template(EMPTY_JSON_SLOT_TEMPLATE)
            slots[slot_num] = json.loads(t.substitute( { 'NO_COMMENT_VALUE': NO_COMMENT_VALUE, \
                                                         'SLOT_VERSION_VALUE': SLOT_VERSION_VALUE, \
                                                         'slot_num': slot_num_str } ))
            if slots[slot_num]["no_comment"] != NO_COMMENT_VALUE:
                ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #1 username : <<" + \
                                username + ">> for slot: " + slot_num_str
                unlock_slot()
                return None
            if slots[slot_num]["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON slot_JSON_format_version #1"
                unlock_slot()
                return None
            try:
                with open(slot_json_file, mode="w", encoding="utf-8") as slot_file_fp:
                    slot_file_fp.write(json.dumps(slots[slot_num], ensure_ascii=True, indent=4))
                    slot_file_fp.write('\n')

                    try:
                        slot_file_fp.close()
                    except OSError as errcode:
                        ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + slot_json_file + \
                                            " exception: " + str(errcode)
                        return None

            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": unable to write JSON slot file: " + \
                                slot_json_file + " exception: " + str(errcode)
                unlock_slot()
                return None

        # Unlock the slot
        #
        unlock_slot()

    # Return success
    #
    return slots
#
# pylint: enable=too-many-statements
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements


# pylint: disable=too-many-return-statements
#
def get_json_slot(username, slot_num):
    """
    read JSON data for a given slot

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        None ==> invalid slot number or invalid user directory
        != None ==> slot information as a python dictionary
    """

    # validate username
    #
    if not lookup_username(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # process this slot for this user
    #
    slot = None

    # setup for the user's slot
    #
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        return None
    slot_json_file = return_slot_json_filename(username, slot_num)
    if not slot_json_file:
        return None

    # first and foremost, lock the user slot
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        return None

    # read the JSON file for the user's slot
    #
    slot = read_json_file(slot_json_file)
    if not slot:
        unlock_slot()
        return None

    # unlock the user slot
    #
    unlock_slot()

    # return slot information as a python dictionary
    #
    return slot
#
# pylint: enable=too-many-return-statements


def get_all_json_slots(username):
    """
    read the user data for all slots for a given user.

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> invalid slot number or invalid user directory
        != None ==> array of slot user data as a python dictionary
    """

    # setup
    #
    umask(0o022)

    # validate username
    #
    if not lookup_username(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # initialize the user tree in case this is a new user
    #
    slots = initialize_user_tree(username)
    if not slots:
        return None

    # return slot information as a python dictionary
    #
    return slots


# pylint: disable=too-many-return-statements
# pylint: disable=too-many-locals
#
def update_slot(username, slot_num, slot_file):
    """
    Update a given slot for a given user with a new file

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username
        slot_file   filename stored under a given slot

    Returns:
        True        recorded and reported the SHA256 hash of slot_file
        False       some error was detected
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # initialize user if needed
    #
    slots = initialize_user_tree(username)
    if not slots:
        return False
    slot_num_str = str(slot_num)

    # open the file
    #
    try:
        with open(slot_file, "rb") as file_fp:
            result = hashlib.sha256(file_fp.read())
            try:
                file_fp.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + slot_file + \
                                    " exception: " + str(errcode)
            return False

    except OSError:
        ioccc_last_errmsg = "ERROR: in " + me + ": failed to open for username: <<" + username + ">> slot: " + \
                        slot_num_str + " file: " + slot_file
        return False

    # lock the slot because we are about to change it
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        return False

    # read the JSON file for the user's slot
    #
    slot_json_file = return_slot_json_filename(username, slot_num)
    if not slot_json_file:
        unlock_slot()
        return False
    slot = read_json_file(slot_json_file)
    if not slot:
        unlock_slot()
        return False

    # If the slot previously saved file that has a different name than the new file,
    # then remove the old file
    #
    if slot['filename']:

        # determine the slot directory
        #
        slot_dir = return_slot_dir_path(username, slot_num)
        if not slot_dir:
            unlock_slot()
            return False

        # remove previously saved file
        #
        old_file = slot_dir + "/" + slot['filename']
        if slot_file != old_file and os.path.isfile(old_file):
            os.remove(old_file)
            ioccc_last_errmsg = "ERROR: in " + me + ": removed from slot: " + slot_num_str + \
                            " file: " + slot['filename']

    # record and report SHA256 hash of file
    #
    slot['status'] = "Uploaded file into slot"
    slot['filename'] = os.path.basename(slot_file)
    slot['length'] = os.path.getsize(slot_file)
    dt = datetime.now(timezone.utc).replace(tzinfo=None)
    slot['date'] = re.sub(r'\.[0-9]{6}$', '', str(dt)) + " UTC"
    slot['sha256'] = result.hexdigest()

    # save JSON data for the slot
    #
    slots_json_file = return_slot_json_filename(username, slot_num)
    if not slots_json_file:
        unlock_slot()
        return False
    if not write_slot_json(slots_json_file, slot):
        unlock_slot()
        return False

    # unlock the slot and report success
    #
    unlock_slot()
    return True
#
# pylint: enable=too-many-return-statements
# pylint: enable=too-many-locals


# pylint: disable=too-many-return-statements
#
def update_slot_status(username, slot_num, status):
    """
    Update the status comment for a given user's slot

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username
        status      the new status string for the slot

    Returns:
        True        status updated
        False       some error was detected
    """

    # must be a valid user
    #
    if not lookup_username(username):
        return False
    slot_json_file = return_slot_json_filename(username, slot_num)
    if not slot_json_file:
        return False

    # lock the slot because we are about to change it
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        return None

    # read the JSON file for the user's slot
    #
    slot = read_json_file(slot_json_file)
    if not slot:
        unlock_slot()
        return None

    # update the status
    #
    slot['status'] = status

    # save JSON data for the slot
    #
    slots_json_file = return_slot_json_filename(username, slot_num)
    if not slots_json_file:
        unlock_slot()
        return False
    if not write_slot_json(slots_json_file, slot):
        unlock_slot()
        return False

    # unlock the slot and report success
    #
    unlock_slot()
    return True
#
# pylint: enable=too-many-return-statements


def read_json_file(json_file):
    """
    Return the contents of a JSON file as a python dictionary

    Given:
        json_file   JSON file to read

    Returns:
        != None     JSON file contents as a python dictionary
        None        unable to read JSON file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # try to read JSON contents
    #
    try:
        with open(json_file, 'r', encoding="utf-8") as j_fp:
            # return slot information as a python dictionary
            #
            return json.load(j_fp)
    except OSError as errcode:
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot open JSON in: " + \
                        json_file + " exception: " + str(errcode)
        return []


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
#
def read_state():
    """
    Read the state file for the open and close dates

    Returns:
        == None, None
                Unable to open the state file, or
                Unable to read the state file, or
                Unable to parse the JSON in the state file,
                state file missing the open date, or
                open date string is not in a valid datetime format, or
                state file missing the close date, or
                close date string is not in a valid datetime in DATETIME_FORMAT format
        != None, open_datetime, close_datetime in datetime in DATETIME_FORMAT format
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # Lock the state file
    #
    state_lock_fd = ioccc_file_lock(STATE_FILE_LOCK)
    if not state_lock_fd:
        return None

    # If there is no state file, or if the state file is empty, copy it from the initial state file
    #
    if not os.path.isfile(STATE_FILE) or os.path.getsize(STATE_FILE) <= 0:
        try:
            shutil.copy2(INIT_STATE_FILE, STATE_FILE, follow_symlinks=True)

        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": cannot cp -p " + INIT_STATE_FILE + \
                                " " + STATE_FILE + " exception: " + str(errcode)
            ioccc_file_unlock()
            return None

    # read the state
    #
    state = read_json_file(STATE_FILE)

    # Unlock the state file
    #
    ioccc_file_unlock()

    # detect if we were unable to read the state file
    #
    if not state:
        return None, None

    # state file sanity checks
    #
    if not state["no_comment"]:
        ioccc_last_errmsg = "ERROR: in " + me + ": no JSON no_comment in state file"
    if state["no_comment"] != NO_COMMENT_VALUE:
        ioccc_last_errmsg = "ERROR: in " + me + ": invalid JSON no_comment in state file: <<" + \
                      state["no_comment"] + ">> != <<" + NO_COMMENT_VALUE + ">>"
        return None
    if not state["state_JSON_format_version"]:
        ioccc_last_errmsg = "ERROR: in " + me + ": no JSON state_JSON_format_version in state file"
    if state["state_JSON_format_version"] != STATE_VERSION_VALUE:
        ioccc_last_errmsg = "ERROR: in " + me + ": invalid state_JSON_format_version no_comment in state file: <<" + \
                      state["state_JSON_format_version"] + ">> != <<" + STATE_VERSION_VALUE + ">>"
        return None, None

    # convert open and close date strings into datetime values
    #
    if not state['open_date']:
        ioccc_last_errmsg = "ERROR: in " + me + ": state file missing open_date"
        return None, None
    if not isinstance(state['open_date'], str):
        ioccc_last_errmsg = "ERROR: in " + me + ": state file open_date is not a string"
        return None, None
    try:
        open_datetime = datetime.strptime(state['open_date'], DATETIME_FORMAT)
    except ValueError:
        ioccc_last_errmsg = "ERROR: in " + me + ": state file open_date is not in proper datetime format: <<" + \
                      state['open_date'] + ">>"
        return None, None
    if not state['close_date']:
        ioccc_last_errmsg = "ERROR: in " + me + ": state file missing close_date"
        return None, None
    if not isinstance(state['close_date'], str):
        ioccc_last_errmsg = "ERROR: in " + me + ": state file close_date is not a string"
        return None, None
    try:
        close_datetime = datetime.strptime(state['close_date'], DATETIME_FORMAT)
    except ValueError:
        ioccc_last_errmsg = "ERROR: in " + me + ": state file close_date is not in proper datetime format: <<" + \
                      state['close_date'] + ">>"
        return None, None

    # return open and close dates
    #
    return open_datetime, close_datetime
#
# pylint: enable=too-many-statements
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements


def update_state(open_date, close_date):
    """
    Update contest dates in the JSON state file

    Given:
        open_date   IOCCC open date as a string in DATETIME_FORMAT format
        close_date  IOCCC close date as a string in DATETIME_FORMAT format

    Return:
        True        json state file was successfully written
        False       unable to update json state file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name
    write_sucessful = True

    # firewall - args must be strings in DATETIME_FORMAT format
    #
    if not isinstance(open_date, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": open_date is not a string"
        return False
    try:
        # pylint: disable=unused-variable
        open_datetime = datetime.strptime(open_date, DATETIME_FORMAT)
    except ValueError:
        ioccc_last_errmsg = "ERROR: in " + me + ": open_date is not in proper datetime format: <<" + open_date + ">>"
        return False
    if not isinstance(close_date, str):
        ioccc_last_errmsg = "ERROR: in " + me + ": close_date is not a string"
        return False
    try:
        # pylint: disable=unused-variable
        close_datetime = datetime.strptime(close_date, DATETIME_FORMAT)
    except ValueError:
        ioccc_last_errmsg = "ERROR: in " + me + ": close_date is not in proper datetime format: <<" + close_date + ">>"
        return False

    # Lock the state file
    #
    state_lock_fd = ioccc_file_lock(STATE_FILE_LOCK)
    if not state_lock_fd:
        return False

    # write JSON data into the state file
    #
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as sf_fp:
            t = Template(DEFAULT_JSON_STATE_TEMPLATE)
            state = json.loads(t.substitute( { 'NO_COMMENT_VALUE': NO_COMMENT_VALUE, \
                                               'STATE_VERSION_VALUE': STATE_VERSION_VALUE, \
                                               'OPEN_DATE': open_date, \
                                               'CLOSE_DATE': close_date } ))
            sf_fp.write(json.dumps(state,
                                   ensure_ascii = True,
                                   indent = 4))
            sf_fp.write('\n')

            try:
                sf_fp.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + STATE_FILE + \
                                    " exception: " + str(errcode)
                write_sucessful = False
                # fall thru

    except OSError:
        ioccc_last_errmsg = "ERROR: in " + me + ": cannot write state file: " + STATE_FILE
        write_sucessful = False
        # fall thru

    # Unlock the state file
    #
    ioccc_file_unlock()

    # return success
    #
    return write_sucessful


def contest_is_open():
    """
    Determine if the IOCCC is open.

    Return:
        != None     Contest is open,
                    return close_datetime in datetime in DATETIME_FORMAT format
        None        Contest is closed
    """

    # setup
    #
    now = datetime.now(timezone.utc)

    # obtain open and close dates in datetime format
    #
    open_datetime, close_datetime = read_state()
    if not open_datetime or not close_datetime:
        return None

    # determine if the contest is open now
    #
    if now >= open_datetime:
        if now < close_datetime:
            return close_datetime
    return None


def return_secret():
    """
    Read a application secret key from the SECRET_FILE, or generate it on the fly.

    We try will read the 1st line of the SECRET_FILE, ignoring the newlines.
    If we cannot, we will generate on a secret the fly for testing using a UUID type 4.

    Generating a secret the fly exception case may not work well in production as
    different instances of this app will have different secrets.

    Returns:
        secret randomly generated string or about 64 bytes in length.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    # Try read the 1st line of the SECRET_FILE, ignoring the newline:
    #
    try:
        with open(SECRET_FILE, 'r', encoding="utf-8") as secret:
            secret_key = secret.read().rstrip()
            try:
                secret.close()
            except OSError as errcode:
                ioccc_last_errmsg = "ERROR: in " + me + ": failed to close: " + SECRET_FILE + \
                                    " exception: " + str(errcode)
                # fall thru

    except OSError:
        # FALLBACK: generate on a secret the fly for testing
        #
        # IMPORTANT: This exception case may not work well in production as
        #            different instances of this app will have different secrets.
        #
        secret_key = str(uuid.uuid4())

    # return secret key
    #
    return secret_key


# pylint: disable=too-many-branches
#
def setup_logger(logtype: str | None, dbglvl: str | None) -> None:
    """
    setup_logger - Setup the logging facility.

    Given:

    logtype      "stdout" ==> log to stdout,
                 "stderr" ==> log to stderr,
                 "syslog" ==> log via syslog,
                 "none" ==> do not log,
                 None ==> do not change the log state,
                 all other values ==> do not change the log state

    dbglvl      "dbg" ==> use logging.DEBUG,
                "debug" ==> use logging.DEBUG,
                "info" ==> use logging.INFO,
                "warn" ==> use logging.WARNING,
                "warning" ==> use logging.WARNING,
                "error" ==> use logging.ERROR,
                "crit" ==> use logging.CRITICAL,
                "critical" ==> use logging.CRITICAL,
                 all other values ==> use logging.INFO

    NOTE: Until setup_logger(logtype) is called, IOCCC_LOGGER default None and no logging will occur.

    NOTE: The logtype is case insensitive, so "syslog", "Syslog", "SYSLOG" are treated the same.
    NOTE: The dbglvl is case insensitive, so "info", "Info", "INFO" are treated the same.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global IOCCC_LOGGER
    logging_level = logging.INFO

    # case: logtype is not a string (such as None) or unknown logtype string
    #
    if not logtype or not isinstance(logtype, str) or not logtype.lower() in {'stdout', 'stderr', 'syslog', 'none'}:

        # do not change the log state
        #
        #print("DEBUG: unknown logtype: IOCCC_LOGGER unchanged")
        return

    # case: logtype is "none"
    #
    if logtype.lower() == "none":

        # do not log
        #
        IOCCC_LOGGER = None
        #print(f'DEBUG: none code: logtype: {logtype}: set IOCCC_LOGGER to None')
        return

    # set the debug level based on dbglvl
    #
    # We default to logging.INFO is dbglvl is not a string (such as None) or unknown dbglvl string
    #
    if isinstance(dbglvl, str):
        # pylint: disable-next=consider-using-in
        if dbglvl.lower() == "dbg" or dbglvl.lower() == "debug":
            logging_level = logging.DEBUG
        elif dbglvl.lower() == "info":
            logging_level = logging.INFO
        # pylint: disable-next=consider-using-in
        elif dbglvl.lower() == "warn" or dbglvl.lower() == "warning":
            logging_level = logging.WARNING
        # pylint: disable-next=consider-using-in
        elif dbglvl.lower() == "err" or dbglvl.lower() == "error":
            logging_level = logging.ERROR
        # pylint: disable-next=consider-using-in
        elif dbglvl.lower() == "crit" or dbglvl.lower() == "critical":
            logging_level = logging.CRITICAL
    #print(f'DEBUG: logtype: {logtype} dbglvl: {dbglvl} '
    #      f'logging_level: {logging.getLevelName(logging_level)}')

    # create the logger, which will change the state
    #
    # As this point we know that that logtype of an allowed string.
    #
    IOCCC_LOGGER = logging.getLogger('ioccc')

    # case: logtype is "stdout"
    #
    # log to stdout
    #
    if logtype.lower() == "stdout":

        # set logging file format
        #
        formatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d: %(name)s: %(levelname)s: %(message)s',
              datefmt='%Y-%m-%d %H:%M:%S')

        # setup stdout logging handler
        #
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging_level)
        stdout_handler.setFormatter(formatter)

        # configure the logger
        #
        # There is BUG in logging where logging requires
        # an additional call to the logging.basicConfig function.
        #
        # To avoid duplicate messages, we do not call:
        #
        #   IOCCC_LOGGER.addHandler(stdout_handler)
        #
        logging.basicConfig(level=logging_level, handlers=[stdout_handler])
        #print(f'DEBUG: stdout code: logtype: {logtype} setup: IOCCC_LOGGER for stdout')
        return

    # case: logtype is "stderr"
    #
    # log to stderr
    #
    if logtype.lower() == "stderr":

        # set logging file format
        #
        formatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d: %(name)s: %(levelname)s: %(message)s',
              datefmt='%Y-%m-%d %H:%M:%S')

        # setup stderr logging handler
        #
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging_level)
        stderr_handler.setFormatter(formatter)

        # configure the logger
        #
        # There is BUG in logging where logging requires
        # an additional call to the logging.basicConfig function.
        #
        # To avoid duplicate messages, we do not call:
        #
        #   IOCCC_LOGGER.addHandler(stderr_handler)
        #
        logging.basicConfig(level=logging_level, handlers=[stderr_handler])
        #print(f'DEBUG: stderr code: logtype: {logtype} setup: IOCCC_LOGGER for stderr')
        return

    # fallthru case: logtype is "syslog"
    #
    # log via syslog local5 facility
    #
    formatter = logging.Formatter('%(name)s: %(levelname)s: %(message)s')

    # determine the logging address
    #
    if Path("/var/run/syslog"):
        # macOS - must be first
        log_address = "/var/run/syslog"
    elif Path("/dev/log"):
        # Linux and related friends symlink
        log_address = "/dev/log"
    elif Path("/run/systemd/journal/dev-log"):
        # Linux and related friends
        log_address = "/run/systemd/journal/dev-log"
    else:
        # FreeBSD and NetBSD - must be last
        log_address = "/var/run/log"

    # setup the syslog handler
    #
    syslog_handler = SysLogHandler(address = log_address,
                                   facility = SysLogHandler.LOG_LOCAL5)
    syslog_handler.setLevel(logging_level)
    syslog_handler.setFormatter(formatter)

    # add the file logging handler to the logger
    #
    # To avoid duplicate messages, we do not call:
    #
    #   IOCCC_LOGGER.addHandler(syslog_handler)
    #
    logging.basicConfig(level=logging_level, handlers=[syslog_handler])
    print(f'DEBUG: syslog code: logtype: {logtype} setup: IOCCC_LOGGER for syslog')
#
# pylint: enable=too-many-branches


def debug(msg, *args, **kwargs):
    """
    Write a DEBUG message or not depending on IOCCC_LOGGER

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    if IOCCC_LOGGER:
        try:
            IOCCC_LOGGER.debug(msg, *args, **kwargs)

        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": IOCCC_LOGGER.debug failed, exception: " + str(errcode)


def dbg(msg, *args, **kwargs):
    """
    Write a DEBUG message if we have called setup_logger to setup IOCCC_LOGGER.

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """
    Write a INFO message if we have called setup_logger to setup IOCCC_LOGGER.

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    if IOCCC_LOGGER:
        try:
            IOCCC_LOGGER.info(msg, *args, **kwargs)

        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": IOCCC_LOGGER.info failed, exception: " + str(errcode)


def warning(msg, *args, **kwargs):
    """
    Write a WARNING message if we have called setup_logger to setup IOCCC_LOGGER.

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    if IOCCC_LOGGER:
        try:
            IOCCC_LOGGER.warning(msg, *args, **kwargs)

        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": IOCCC_LOGGER.warning failed, exception: " + str(errcode)


def warn(msg, *args, **kwargs):
    """
    Write a WARNING message if we have called setup_logger to setup IOCCC_LOGGER.

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """
    Write an ERROR message if we have called setup_logger to setup IOCCC_LOGGER.

    If not IOCCC_LOGGER, then
        do not log (do nothing),
    else
        Use IOCCC_LOGGER as a logging facility that was setup  by setup_logger(Bool)
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global ioccc_last_errmsg
    me = inspect.currentframe().f_code.co_name

    if IOCCC_LOGGER:
        try:
            IOCCC_LOGGER.error(msg, *args, **kwargs)

        except OSError as errcode:
            ioccc_last_errmsg = "ERROR: in " + me + ": IOCCC_LOGGER.error failed, exception: " + str(errcode)
