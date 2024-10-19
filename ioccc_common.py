#!/usr/bin/env python3
# pylint: disable=too-many-lines
# pylint: disable=import-error
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=undefined-variable
# pylint: disable=unused-import
"""
Common support / utility functions needed by the IOCCC Submit Server
and related tools.

IMPORTANT NOTE: This code must NOT assume the use of Flask, nor call
                functions such as flash().  This code may be imported
                into utility functions that are command line and not
                web app related.

IMPORTANT NOTE: To return an error message to a caller, set: global_errmsg
"""

# import modules
#
import re
import json
import os


# import from modules
#
from string import Template
from os import makedirs, umask
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path


# For user slot locking
#
# See:
#
#   https://snyk.io/advisor/python/filelock/example for filelock examples
#   https://py-filelock.readthedocs.io/en/latest/index.html
#
from filelock import Timeout, FileLock


##################
# Global constants
##################

# IOCCC common version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION_IOCCC_COMMON = "1.0.1 2024-10-18"

# default content open and close date if there is no STATE_FILE
#
DEF_OPDATE = datetime(2024, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
DEF_CLDATE = datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))

# force password change grace time
#
# Time in seconds from when force_pw_change is set to true that the
# user must login and change their password.  If "pw_change_by" >= 0, and
# if "force_pw_change" is "true", then login is denied if now > "pw_change_by".
#
FORCE_PW_GRACE_SECS = 72*3600

# default IP and port
#
HOST_NAME = "127.0.0.1"
TCP_PORT = "8191"

# important directories and files
#
IOCCC_ROOT = "/"
IOCCC_DIR = IOCCC_ROOT + "app"
# if we are testing in ., assume ./app is a symlink to app
if not Path(IOCCC_DIR).is_dir():
    IOCCC_ROOT = "./"
    IOCCC_DIR = IOCCC_ROOT + "app"
PW_FILE = IOCCC_DIR + "/etc/iocccpasswd.json"
PW_LOCK = IOCCC_DIR + "/etc/lock.iocccpasswd.json"
STATE_FILE = IOCCC_DIR + "/etc/state.json"
ADM_FILE = IOCCC_DIR + "/etc/admins.json"
SECRET_FILE = IOCCC_DIR + "/etc/.secret"

# POSIX safe filename regular expression
#
POSIX_SAFE_RE = "^[0-9A-Za-z][0-9A-Za-z._+-]*$"

# JSON related values
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
PASSWORD_VERSION_VALUE = "1.1 2024-10-18"

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

# global slot lock - lock file descriptor or none
#
# When lock_file is not none, flock has been applied to some lock file.
# When lock_file is none, no flock has been applied to a slot lock file.
#
# When starting to operate on a slot, and before we lock the slot, we
# check if lock_file is not none.  If lock_file is not none, we force
# the previous slot lock to be unlocked.
#
# The slot lock file only needs to be locked during a brief slot operation,
# which are brief in duration.  Moreover this server is NOT multi-threaded.
# We NEVER want to lock more than one slot at a time.
#
# Nevertheless if, before we start a slot operation AND before we attempt
# to lock the slot, we discover that some other slot is still locked
# (due to unexpected asynchronous event or exception, or code bug), we
# will force that previous lock to be unlocked.
#
# pylint: disable-next=global-statement,invalid-name
global_slot_lock = None         # lock file descriptor or None
# pylint: disable-next=global-statement,invalid-name
global_lock_user = None         # username whose slot is locked or None
# pylint: disable-next=global-statement,invalid-name
global_lock_slot_num = None     # slot number that is locked or None
# pylint: disable-next=global-statement,invalid-name
global_errmsg = ""            # recent error message or None


def return_user_dir_path(username):
    """
    Return the user directory path

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> username is not POSIX safe
        != None ==> directory (may not exist) of for the user (not exist)

    A useful side effect of this call is to verify that the username
    string is sane.  However, the username may not be a valid user
    nor may the user directory exist.  It is up to caller to check that.

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not isinstance(username, str):
        global_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username not POSIX safe: <<" + username + ">>"
        return None

    # return user directory path
    #
    user_dir = IOCCC_DIR + "/users/" + username
    return user_dir


def return_slot_dir_path(username, slot_num):
    """
    Return the slot directory path under a given user directory

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        None ==> invalid slot number or Null user_dir
        != None ==> slot directory (may not exist))

    It is up the caller to create, if needed, the slot directory.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - must make a user_dir value
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # paranoia - must be a valid slot number
    #
    if (slot_num < 0 or slot_num > MAX_SUBMIT_SLOT):
        global_errmsg = "ERROR: in " + me + ": invalid slot number: " + str(slot_num) + \
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
        None ==> invalid slot number or Null user_dir
        != None ==> path of the JSON filename for this user's slot

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


def load_pwfile():
    """
    Return the JSON contents of the password file

    Obtain a lock for password file before opening and reading the password file.
    We release the lock for the password file afterwards.

    Returns:
        None ==> unable to read the JSON in the password file
        != None ==> JSON from the password file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # Lock the password file
    #
    pw_lock_fd = FileLock(PW_LOCK, timeout=LOCK_TIMEOUT, is_singleton=True)
    if not pw_lock_fd:
        global_errmsg = "ERROR: in " + me + ": unable to lock password file"
        return None

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close and unlock the password file
            #
            j_pw.close()
            pw_lock_fd.release(force=True)
    except OSError as exception:
        global_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " exception: " + str(exception)

        # unlock the password file
        #
        pw_lock_fd.release(force=True)
        return None

    # return the password JSON data
    #
    return pw_file_json


def replace_pwfile(pw_file_json):
    """
    Replace the contents of the password file

    Obtain a lock for password file before opening and writing JSON to the password file.
    We release the lock for the password file afterwards.

    Given:
        pw_file_json    JSON to write into the password file

    Returns:
        False ==> unable to write JSON into the password file
        True ==> password file updated with JSON
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # Lock the password file
    #
    pw_lock_fd = FileLock(PW_LOCK, timeout=LOCK_TIMEOUT, is_singleton=True)
    if not pw_lock_fd:
        global_errmsg = "ERROR: in " + me + ": unable to lock password file"
        return False

    # rewrite the password file with the pw_file_json and unlock
    #
    try:
        with open(PW_FILE, mode="w", encoding="utf-8") as j_pw:
            j_pw.write(json.dumps(pw_file_json, ensure_ascii=True, indent=4))
            j_pw.write('\n')

            # close and unlock the password file
            #
            j_pw.close()
            pw_lock_fd.release(force=True)
    except OSError:

        # unlock the password file
        #
        global_errmsg = "ERROR: in " + me + ": unable to write password file"
        pw_lock_fd.release(force=True)
        return False

    # password file updated
    #
    return True


def lookup_username(username):
    """
    Return JSON information for username from password file

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> no such username, or username does not match POSIX_SAFE_RE, or bad password file
        != None ==> JSON information about username

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        global_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return None

    # load JSON from the password file
    #
    pw_file_json = load_pwfile()
    if not pw_file_json:
        return None

    # search the password file for the user
    #
    user_json = None
    for i in pw_file_json:
        if i['username'] == username:
            user_json = i
            break
    if not user_json:
        global_errmsg = "ERROR: in " + me + ": unknown username: <<" + username + ">>"
        return None

    # sanity check the JSON information for user
    #
    if not isinstance(user_json['username'], str):
        global_errmsg = "ERROR: in " + me + ": username is not a string: <<" + str(user_json['username']) + ">>"
        return None
    if user_json["no_comment"] != NO_COMMENT_VALUE:
        global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment username : <<" + username + ">>"
        return None
    if user_json["iocccpasswd_format_version"] != PASSWORD_VERSION_VALUE:
        global_errmsg = "ERROR: in " + me + ": invalid iocccpasswd_format_version for username : <<" + username + ">>"
        return None
    if not user_json['pwhash']:
        global_errmsg = "ERROR: in " + me + ": no pwhash for username : <<" + username + ">>"
        return None
    if not isinstance(user_json['pwhash'], str):
        global_errmsg = "ERROR: in " + me + ": pwhash is not a string for username : <<" + username + ">>"
        return None
    if not is_boolean(user_json['force_pw_change']):
        global_errmsg = "ERROR: in " + me + ": force_pw_change is not a boolean for username : <<" + username + ">>"
        return None
    if not user_json['pw_change_by']:
        global_errmsg = "ERROR: in " + me + ": no pw_change_by for username : <<" + username + ">>"
        return None
    if not is_numeric(user_json['pw_change_by']):
        global_errmsg = "ERROR: in " + me + ": pw_change_by is not a number for username : <<" + username + ">>"
        return None
    if not is_boolean(user_json['disable_login']):
        global_errmsg = "ERROR: in " + me + ": disable_login is not a boolean for username : <<" + username + ">>"
        return None

    # return JSON information for user
    #
    return user_json


def update_username(username, pwhash, force_pw_change, pw_change_by, disable_login):
    """
    Update a username entry in the password file, or add the entry
    if the username is not already in the password file.

    Given:
        username            IOCCC submit server username
        pwhash              SHA256 hash of the password (i.e., a string of the form: pbkdf2:sha256:...)
        force_pw_change     boolean indicating if the user will be forced to change their password on next login
        pw_change_by        pw_change_by >= 0 and force_pw_change and now > pw_change_by ==> deny login
                            pw_change_by < 0 ==> no deadline for changing password
        disable_login       boolean indicating if the user is banned from login

    Returns:
        False ==> unable to update user in the password file
        True ==> user updated or added to the password file

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        global_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return False

    # paranoia - pwhash must be a string
    #
    if not isinstance(pwhash, str):
        global_errmsg = "ERROR: in " + me + ": pwhash is not a string for username : <<" + username + ">>"
        return None

    # paranoia - force_pw_change must be a boolean
    #
    if not is_boolean(force_pw_change):
        global_errmsg = "ERROR: in " + me + ": force_pw_change is not a boolean for username : <<" + username + ">>"
        return None

    # paranoia - pw_change_by must be a number
    if not is_numeric(pw_change_by):
        global_errmsg = "ERROR: in " + me + ": pw_change_by is not a number for username : <<" + username + ">>"
        return None

    # paranoia - disable_login must be a boolean
    #
    if not is_boolean(disable_login):
        global_errmsg = "ERROR: in " + me + ": disable_login is not a boolean for username : <<" + username + ">>"
        return None

    # Lock the password file
    #
    pw_lock_fd = FileLock(PW_LOCK, timeout=LOCK_TIMEOUT, is_singleton=True)
    if not pw_lock_fd:
        global_errmsg = "ERROR: in " + me + ": unable to lock password file"
        return None

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close the password file
            #
            j_pw.close()
    except OSError as exception:

        # unlock the password file
        #
        global_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " exception: " + str(exception)
        pw_lock_fd.release(force=True)
        return None

    # scan through the password file, looking for the user
    #
    found_username = False
    for i in pw_file_json:
        if i['username'] == username:

            # user found, update user info
            #
            i['pwhash'] = pwhash
            i['force_pw_change'] = force_pw_change
            i['pw_change_by'] = pw_change_by
            i['disable_login'] = disable_login
            found_username = True
            break

    # the user is new, add the user to the JSON from the password file
    #
    if not found_username:
        pw_file_json.append({ "no_comment" : NO_COMMENT_VALUE, \
                              "iocccpasswd_format_version" : PASSWORD_VERSION_VALUE, \
                              "username" : username, \
                              "pwhash" : pwhash, \
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
            j_pw.close()
            pw_lock_fd.release(force=True)
    except OSError as exception:
        global_errmsg = "ERROR: in " + me + ": unable to write password file" + \
                        " exception: " + str(exception)

        # unlock the password file
        #
        pw_lock_fd.release(force=True)
        return None

    # password updated with new username information
    #
    return True


def delete_username(username):
    """
    Remove a username from the password file

    Given:
        username    IOCCC submit server username to remove

    Returns:
        None ==> no such username, or username does not match POSIX_SAFE_RE, or bad password file
        != None ==> JSON information about username that was removed

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        global_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return None

    # Lock the password file
    #
    pw_lock_fd = FileLock(PW_LOCK, timeout=LOCK_TIMEOUT, is_singleton=True)
    if not pw_lock_fd:
        global_errmsg = "ERROR: in " + me + ": unable to lock password file"
        return None

    # load the password file and unlock
    #
    try:
        with open(PW_FILE, 'r', encoding="utf-8") as j_pw:
            pw_file_json = json.load(j_pw)

            # close the password file
            #
            j_pw.close()
    except OSError as exception:

        # unlock the password file
        #
        global_errmsg = "ERROR: in " + me + ": cannot read password file" + \
                        " exception: " + str(exception)
        pw_lock_fd.release(force=True)
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
            j_pw.write(json.dumps(pw_file_json, ensure_ascii=True, indent=4))
            j_pw.write('\n')

            # close and unlock the password file
            #
            j_pw.close()
            pw_lock_fd.release(force=True)
    except OSError as exception:

        # unlock the password file
        #
        global_errmsg = "ERROR: in " + me + ": unable to write password file" + \
                        " exception: " + str(exception)
        pw_lock_fd.release(force=True)
        return None

    # return the user that was deleted, if they were found
    #
    return deleted_user


def is_user_login_disabled(username):
    """
    Determine if the user has been disabled.

    NOTE: If the user is not in the password file, we cannot state that the
          user has been disabled.   So in that case we return False.

    Given:
        username    IOCCC submit server username

    Returns:
        True        username has been disabled in the password file, or username is invalid
        False       username login attempt is allowed

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename string
    #
    if not isinstance(username, str):
        global_errmsg = "ERROR: in " + me + ": username arg is not a string: <<" + str(username) + ">>"
        return None
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username is not POSIX safe: <<" + username + ">>"
        return True

    # fail if user login is disabled or missing from the password file
    #
    user_json = lookup_username(username)
    if not user_json:

        # user is not in the password file, so we cannot state they have been disabled
        #
        return True

    # deny login if disable_login is true
    #
    if user_json['disable_login']:

        # login disabled
        #
        return True

    # deny login is the force_pw_change and we are beyond the window to change
    #
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user_json['force_pw_change'] and user_json['pw_change_by'] >= 0 and now > user_json['pw_change_by']:

        # failed to change the password in time
        #
        return True

    # user login attempt is allowed
    #
    return False


def lock_slot(username, slot_num):
    """
    lock a slot for a user

    A side effect of locking the slot is that the user directory will be created.
    If it does not exist, and the slot directory for the user will be created.
    If it does not exist, and the lock file will be created .. unless we return None.

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

        Force a previously locked slot to be unlocked,
        Lock the new slot.
        Register the locked slot.

    Returns:
        lock file descriptor    lock successful
        None                    lock not successful, invalid username, invalid slot_num

    NOTE: We use the python filelock module.  See:

          https://pypi.org/project/filelock/
          https://py-filelock.readthedocs.io/en/latest/api.html
          https://snyk.io/advisor/python/filelock/example

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_slot_lock
    # pylint: disable-next=global-statement
    global global_lock_user
    # pylint: disable-next=global-statement
    global global_lock_slot_num
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name
    umask(0o022)

    # validate username and slot
    #
    if is_user_login_disabled(username):
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
        global_errmsg = "ERROR: in " + me + ": failed to create for username: <<" + username + ">>"
        return None

    # be sure the slot directory exits
    #
    try:
        makedirs(slot_dir, mode=0o2770, exist_ok=True)
    except OSError:
        global_errmsg = "ERROR: in " + me + ": failed to create slot: " + slot_num_str + \
                        "for username: <<" + username + ">>"
        return None

    # be sure the lock file exists for this slot
    #
    lock_file = slot_dir + "/lock"
    Path(lock_file).touch()

    # Force any stale slot lock to become unlocked
    #
    if global_slot_lock:
        # Carp
        #
        if not global_lock_user:
            global_lock_user = "((no-username))"
        if not global_lock_slot_num:
            global_lock_slot_num = "((no-slot))"
        global_errmsg = "Warning: forcing stale slot unlock for username: <<" + global_lock_user + ">> slot: " + \
               str(global_lock_slot_num)

        # Force previous stale slot lock to become unlocked
        #
        try:
            global_slot_lock.release(force=True)
        except OSError:
            # We give up as we cannot force the unlock
            #
            global_errmsg = "ERROR: failed to force stale slot unlock for username: <<" + global_lock_user + \
                            ">> slot: " + str(global_lock_slot_num)
            global_slot_lock = None
            global_lock_user = None
            global_lock_slot_num = None
            return None

        # clear the global lock information
        #
        global_slot_lock = None
        global_lock_user = None
        global_lock_slot_num = None

    # Lock the slot
    #
    slot_lock_fd = FileLock(lock_file, timeout=LOCK_TIMEOUT, is_singleton=True)
    try:
        with slot_lock_fd:
            # note our new lock
            #
            global_slot_lock = slot_lock_fd
            global_lock_user = username
            global_lock_slot_num = slot_num
    except Timeout:

        # too too long to get the lock
        #
        global_errmsg = "Warning: timeout on slot lock for username: <<" + username + ">> slot: " + slot_num_str
        return None

    # return the slot lock success
    #
    return slot_lock_fd


def unlock_slot():
    """
    unlock a previously locked slot

    A slot locked via lock_slot(username, slot_num) is unlocked
    using the global_slot_lock that noted the slot lock descriptor.

    Returns:
        True    slot unlock successful
        None    failed to unlock slot
    """

    # declare global use
    #
    # pylint: disable-next=global-statement
    global global_slot_lock
    # pylint: disable-next=global-statement
    global global_lock_user
    # pylint: disable-next=global-statement
    global global_lock_slot_num
    # pylint: disable-next=global-statement
    global global_errmsg

    # unlock the global slot lock
    #
    if global_slot_lock:
        try:
            global_slot_lock.release(force=True)
        except OSError as exception:
            # We give up as we cannot unlock the slot
            #
            if not global_lock_user:
                global_lock_user = "((None))"
            if not global_lock_slot_num:
                global_lock_slot_num = "((no-slot))"
            global_errmsg = "Warning: failed to unlock for username: <<" + cglobal_lock_user + \
                            ">> slot: " + global_lock_slot_num + " exception: " + str(exception)

    # clear lock, lock user and lock slot
    #
    global_slot_lock = None
    global_lock_user = None
    global_lock_slot_num = None


def write_slot_json(slots_json_file, slot_json):
    """
    Write out an index of slots for the user.

    Given:
        slots_json_file     JSON filename for a given slot
        slot_json           JSON content for a given slot
    """
    # declare global use
    #
    # pylint: disable-next=global-statement
    global global_errmsg

    # write JSON file for slot
    #
    try:
        with open(slots_json_file, mode="w", encoding="utf-8") as slot_file_fp:
            slot_file_fp.write(json.dumps(slot_json, ensure_ascii=True, indent=4))
            slot_file_fp.write('\n')
            slot_file_fp.close()
    except OSError:
        global_errmsg = "ERROR: failed to write out slot file: " + slots_json_file
        return False
    return True


def initialize_user_tree(username):
    """
    Initialize the directory tree for a given user

    We create the directory for the username if the directory does not exist.
    We create the slot for the username if the slot directory does not exist.
    We create the lock file for the slot it the lock file does not exist.
    We initialize the slot JSON file it the slot JSON file does not exist.

    NOTE: Because this may be called early, we cannot use HTML or other
          error carping delivery.  We only set global_excpt are return None.

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> invalid slot number or Null user_dir
        != None ==> array of slot JSON data

    NOTE: We use the python filelock module.  See:

          https://pypi.org/project/filelock/
          https://py-filelock.readthedocs.io/en/latest/api.html
          https://snyk.io/advisor/python/filelock/example
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # setup
    #
    if is_user_login_disabled(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return False
    umask(0o022)

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError as exception:
        global_errmsg = "ERROR: in " + me + ": cannot form user directory for user: <<" + \
                        username + ">> exception: " + str(exception)
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
        except OSError as exception:
            global_errmsg = "ERROR: in " + me + ": cannot form slot directory: " + \
                            slot_dir + " exception: " + str(exception)
            return None

        # Force any stale slot lock to become unlocked
        #
        unlock_slot()

        # be sure the lock file exists for this slot
        #
        lock_file = slot_dir + "/lock"
        try:
            Path(lock_file).touch()
        except OSError as exception:
            global_errmsg = "ERROR: in " + me + ": cannot form slot directory: " + \
                            slot_dir + " exception: " + str(exception)
            return None

        # Lock the slot
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
                slot_file_fp.close()
                if slots[slot_num]["no_comment"] != NO_COMMENT_VALUE:
                    global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #0 username : <<" + \
                                    username + ">> for slot: " + slot_num_str
                    unlock_slot()
                    return None
                if slots[slot_num]["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                    global_errmsg = "ERROR: in " + me + ": invalid JSON slot_JSON_format_version #0"
                    unlock_slot()
                    return None
        except OSError:
            t = Template(EMPTY_JSON_SLOT_TEMPLATE)
            slots[slot_num] = json.loads(t.substitute( { 'NO_COMMENT_VALUE': NO_COMMENT_VALUE, \
                                                         'SLOT_VERSION_VALUE': SLOT_VERSION_VALUE, \
                                                         'slot_num': slot_num_str } ))
            if slots[slot_num]["no_comment"] != NO_COMMENT_VALUE:
                global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #1 username : <<" + \
                                username + ">> for slot: " + slot_num_str
                unlock_slot()
                return None
            if slots[slot_num]["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                global_errmsg = "ERROR: in " + me + ": invalid JSON slot_JSON_format_version #1"
                unlock_slot()
                return None
            try:
                with open(slot_json_file, mode="w", encoding="utf-8") as slot_file_fp:
                    slot_file_fp.write(json.dumps(slots[slot_num], ensure_ascii=True, indent=4))
                    slot_file_fp.write('\n')
                    slot_file_fp.close()
            except OSError as exception:
                global_errmsg = "ERROR: in " + me + ": unable to write JSON slot file: " + \
                                slot_json_file + " exception: " + str(exception)
                unlock_slot()
                return None

        # Unlock the slot
        #
        unlock_slot()

    # Return success
    #
    return slots


def get_json_slot(username, slot_num):
    """
    read JSON data for a given slot

    Given:
        username    IOCCC submit server username
        slot_num    slot number for a given username

    Returns:
        None ==> invalid slot number or Null user_dir
        != None ==> slot directory (may not exist))
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name
    umask(0o022)

    # validate username
    #
    if is_user_login_disabled(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # process this slot for this user
    #
    slot = None

    # setup for the user's slot
    #
    slot_num_str = str(slot_num)
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        return None
    slot_json_file = return_slot_json_filename(username, slot_num)
    if not slot_json_file:
        return None

    # first and foremost, lock the user slot
    #
    # NOTE: If needed the user directory and the slot directory will be created.
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        return None

    # read the JSON file for the user's slot
    #
    # NOTE: We initialize the slot JSON file if the JSON file does not exist.
    #
    try:
        with open(slot_json_file, "r", encoding="utf-8") as slot_file_fp:
            slot = json.load(slot_file_fp)
            slot_file_fp.close()
            if slot["no_comment"] != NO_COMMENT_VALUE:
                global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #2 username : <<" + \
                                username + ">> for slot: " + slot_num_str
                unlock_slot()
                return None
            if slot.slot["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                global_errmsg = "ERROR: in " + me + ": SON slot[" + slot_num_str + "] version: " + \
                                slot[slot_num].slot["slot_JSON_format_version"] + " != " + SLOT_VERSION_VALUE
                unlock_slot()
                return None
    except OSError:
        # initialize slot JSON file
        #
        t = Template(EMPTY_JSON_SLOT_TEMPLATE)
        slot = json.loads(t.substitute( { 'NO_COMMENT_VALUE': NO_COMMENT_VALUE, \
                                          'SLOT_VERSION_VALUE': SLOT_VERSION_VALUE, \
                                          'slot_num': slot_num_str } ))
        if slot["no_comment"] != NO_COMMENT_VALUE:
            global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #3 username : <<" + \
                            username + ">> for slot: " + slot_num_str
            unlock_slot()
            return None
        if slot["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
            global_errmsg = "ERROR: in " + me + ": JSON slot[" + slot_num_str + "] version: " + \
                            slot[slot_num].slot["slot_JSON_format_version"] + " != " + SLOT_VERSION_VALUE
            unlock_slot()
            return None
        if not write_slot_json(slot_json_file, slot):
            unlock_slot()
            return None

    # unlock the user slot
    #
    unlock_slot()

    # return slot information
    #
    return slot


def get_all_json_slots(username):
    """
    read the JSON data for all slots for a given user.

    Given:
        username    IOCCC submit server username

    Returns:
        None ==> invalid slot number or Null user_dir
        != None ==> array of slot JSON data
    """

    # setup
    #
    umask(0o022)

    # validate usewrname
    #
    if is_user_login_disabled(username):
        return None
    user_dir = return_user_dir_path(username)
    if not user_dir:
        return None

    # process each slot for this user
    #
    slots = []
    for slot_num in range(0, MAX_SUBMIT_SLOT+1):

        # get the JSON slot
        #
        json_slot_data = get_json_slot(username, slot_num)
        if not json_slot_data:
            return None
        slots[slot_num] = json_slot_data

    return slots


def update_slot(username, slot_num, slot_file):
    """
    Update a given slot for a given user.

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
    global global_errmsg
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
            file_fp.close()
    except OSError:
        global_errmsg = "ERROR: in " + me + ": failed to open for username: <<" + username + ">> slot: " + \
                        slot_num_str + " file: " + slot_file
        return False

    # If the slot previously saved file that has a different name than the new file, then remove the old file
    #
    if slots[slot_num]['filename']:

        # determine the slot directory
        #
        slot_dir = return_slot_dir_path(username, slot_num)
        if not slot_dir:
            return False

        # remove previously saved fike
        #
        old_file = slot_dir + "/" + slots[slot_num]['filename']
        if slot_file != old_file and os.path.isfile(old_file):
            os.remove(old_file)
            global_errmsg = "ERROR: in " + me + ": removed from slot: " + slot_num_str + \
                            " file: " + slots[slot_num]['filename']

    # record and report SHA256 hash of file
    #
    slots[slot_num]['status'] = "Uploaded file into slot"
    slots[slot_num]['filename'] = os.path.basename(slot_file)
    slots[slot_num]['length'] = os.path.getsize(slot_file)
    dt = datetime.now(timezone.utc).replace(tzinfo=None)
    slots[slot_num]['date'] = re.sub(r'\.[0-9]{6}$', '', str(dt)) + " UTC"
    slots[slot_num]['sha256'] = result.hexdigest()

    # save JSON data for the slot
    #
    slots_json_file = return_slot_json_filename(username, slot_num)
    if not slots_json_file:
        return False
    if not write_slot_json(slots_json_file, slots[slot_num]):
        return False
    return True


def readjfile(jfile):
    """
    Return the contents of a JSON file.

    Given:
        jfile   JSON file to read

    Returns:
        != None     JSON file contents
        None        unable to read JSON file
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # try to read JSON contents
    #
    try:
        with open(jfile, 'r', encoding="utf-8") as j_fp:
            return json.load(j_fp)
    except OSError as exception:
        global_errmsg = "ERROR: in " + me + ": cannot open JSON in: " + \
                        jfile + " exception: " + str(exception)
        return []


def set_state(opdate, cldate):
    """
    Set contest dates.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # set the state file with open and close date/time
    #
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as sf_fp:
            sf_fp.write(json.dumps(f'{{ "opendate" : "{opdate}", "closedate" : "{cldate}" }}', \
                                   ensure_ascii=True, indent=4))
            sf_fp.write('\n')
            sf_fp.close()
    except OSError:
        global_errmsg = "ERROR: in " + me + ": cannot write state file: " + STATE_FILE


def check_state():
    """
    See if the contest is opened.
    """

    # setup
    #
    now = datetime.now(timezone.utc)

    # read state file if exists and is not emopty
    #
    if os.path.isfile(STATE_FILE) and os.stat(STATE_FILE).st_size > 0:
        st_info = readjfile(STATE_FILE)
    else:
        st_info = []

    # obtain content open and close date/time from state file
    #
    if st_info:
        the_time = datetime.fromisoformat(st_info['opendate'])
        opdate = datetime(the_time.year, the_time.month, the_time.day, \
                          the_time.hour, the_time.minute, the_time.second, tzinfo=ZoneInfo("UTC"))
        the_time = datetime.fromisoformat(st_info['closedate'])
        cldate = datetime(the_time.year, the_time.month, the_time.day, \
                          the_time.hour, the_time.minute, the_time.second, tzinfo=ZoneInfo("UTC"))

    # in case we filed to read the state file
    #
    else:
        # set default open and close date/time
        #
        opdate = DEF_OPDATE
        cldate = DEF_CLDATE

    return opdate, cldate, now
