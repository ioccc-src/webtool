#!/usr/bin/env python3
# pylint: disable=import-error,too-many-return-statements,too-many-branches,too-many-lines,too-many-statements
"""
Routines to implement IOCCC registration functions.
"""

# import modules
#
import re
import json
import hashlib
import uuid
import inspect
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


# 3rd party imports
#
from flask import Flask, Response, url_for, render_template, flash, redirect, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from iocccpasswd import adduser, deluser


# Global constants
#
# default content open and close date if there is no STATE_FILE
#
DEF_OPDATE = datetime(2024, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
DEF_CLDATE = datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
#
# default IP and port
#
HOST_NAME = "127.0.0.1"
TCP_PORT = "8191"
#
# important directories and files
#
IOCCC_ROOT = "/"
IOCCC_DIR = IOCCC_ROOT + "app"
# if we are testing in ., assume ./app is a symlink to app
if not Path(IOCCC_DIR).is_dir():
    IOCCC_ROOT = "./"
    IOCCC_DIR = IOCCC_ROOT + "app"
PW_FILE = IOCCC_DIR + "/etc/iocccpasswd.json"
STATE_FILE = IOCCC_DIR + "/etc/state.json"
ADM_FILE = IOCCC_DIR + "/etc/admins.json"
SECRET_FILE = IOCCC_DIR + "/etc/.secret"
#
# POSIX safe filename regular expression
#
POSIX_SAFE_RE = "^[0-9A-Za-z][0-9A-Za-z._+-]*$"
#
# other important values
#
NO_COMMENT_VALUE = "mandatory comment: because comments were removed from the original JSON spec"
SLOT_VERSION_VALUE = "1.0 2024-10-02"
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
#
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
#
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
#
# Lock timeout in seconds
#
LOCK_TIMEOUT = 13
#
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
# will force that previous lock to be unlocked (and report via flash).
#
# pylint: disable-next=global-statement,invalid-name
global_slot_lock = None         # lock file descriptor or None
# pylint: disable-next=global-statement,invalid-name
global_lock_user = None         # username whose slot is locked or None
# pylint: disable-next=global-statement,invalid-name
global_lock_slot_num = None     # slot number that is locked or None
# pylint: disable-next=global-statement,invalid-name
global_errmsg = None            # recent error message or None


# Configure the application
#
application = Flask(__name__)
application.config['MAX_CONTENT_LENGTH'] = MAX_TARBALL_LEN
application.config['BASIC_AUTH_FORCE'] = True
#
# We will read the 1st line of the SECRET_FILE, ignoring the newline
#
# IMPORTANT: You MUST generate the secret key once and then
#            copy/paste the value into your application or store it as an
#            environment variable. Do NOT regenerate the secret key within
#            the application, or you will get a new value for each instance
#            of the application, which can cause issues when you deploy to
#            production since each instance of the application has a
#            different SECRET_KEY value.
#
try:
    with open(SECRET_FILE, 'r', encoding="utf-8") as secret:
        application.secret_key = secret.read().rstrip()
except OSError:
    # FALLBACK: generate on the fly for testing
    #
    # IMPORTANT: This will not work for production as different
    #            instances of this application will have different secrets.
    #
    application.secret_key = str(uuid.uuid4())


# start HTTP Basic authorization
#
auth = HTTPBasicAuth()


# set application file paths
#
with application.test_request_context('/'):
    url_for('static', filename='style.css')
    url_for('static', filename='script.js')
    url_for('static', filename='ioccc.png')


def get_user_dir(username):
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
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # paranoia - username must be a POSIX safe filename
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not re.match(POSIX_SAFE_RE, username):
        global_errmsg = "ERROR: in " + me + ": username not POSIX safe: " + username
        return None

    # return user directory path
    #
    user_dir = IOCCC_DIR + "/users/" + username
    return user_dir


def get_slot_dir(username, slot_num):
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
    user_dir = get_user_dir(username)
    if not user_dir:
        return None

    # paranoia - must be a valid slot number
    #
    if (slot_num < 0 or slot_num > MAX_SUBMIT_SLOT):
        global_errmsg = "ERROR: in " + me + ": invalid slot number: " + str(slot_num)
        return None

    # return slot directory path under a given user directory
    #
    slot_dir = user_dir + "/" + str(slot_num)
    return slot_dir


def get_slot_json_filename(username, slot_num):
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
    user_dir = get_user_dir(username)
    if not user_dir:
        return None
    slot_dir = get_slot_dir(username, slot_num)
    if not slot_dir:
        return None

    # determine the JSON filename for this given slot
    #
    slot_json_file = slot_dir + "/slot.json"
    return slot_json_file


def initialize_user(username):
    """
    Initialize an IOCCC submit server user

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

    NOTE: The username must be a POSIX safe filename.  See POSIX_SAFE_RE.
    """

    # setup
    #
    # pylint: disable-next=global-statement
    global global_errmsg
    me = inspect.currentframe().f_code.co_name

    # setup
    #
    user_dir = get_user_dir(username)
    if not user_dir:
        return False
    umask(0o022)

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError as exception:
        global_errmsg = "ERROR: in " + me + ": cannot form user directory for user: " + \
                        username + " exception: " + str(exception)
        return None

    # process each slot for this user
    #
    slots = [None] * (MAX_SUBMIT_SLOT+1)
    for slot_num in range(0, MAX_SUBMIT_SLOT+1):

        # determine the slot directory
        #
        slot_dir = get_slot_dir(username, slot_num)
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
        slot_json_file = get_slot_json_filename(username, slot_num)
        if not slot_json_file:
            unlock_slot()
            return None
        try:
            with open(slot_json_file, "r", encoding="utf-8") as slot_file_fp:
                slots[slot_num] = json.load(slot_file_fp)
                if slots[slot_num]["no_comment"] != NO_COMMENT_VALUE:
                    global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #0"
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
                global_errmsg = "ERROR: in " + me + ": invalid JSON no_comment #1"
                unlock_slot()
                return None
            if slots[slot_num]["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                global_errmsg = "ERROR: in " + me + ": invalid JSON slot_JSON_format_version #0"
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

    # declare global use
    #
    # pylint: disable-next=global-statement
    global global_slot_lock
    # pylint: disable-next=global-statement
    global global_lock_user
    # pylint: disable-next=global-statement
    global global_lock_slot_num

    # setup
    #
    user_dir = get_user_dir(username)
    if not user_dir:
        flash("username is not POSIX safe: " + username)
        return None
    slot_num_str = str(slot_num)
    slot_dir = get_slot_dir(username, slot_num)
    if not slot_dir:
        flash("invalid slot number: " + slot_num_str)
        return None
    umask(0o022)

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError as exception:
        print(str(exception))
        flash("ERROR: failed to create for username: " + username)
        return None

    # be sure the slot directory exits
    #
    try:
        makedirs(slot_dir, mode=0o2770, exist_ok=True)
    except OSError as exception:
        print(str(exception))
        flash("ERROR: failed to create for username: " + username + " slot: " + slot_num_str)
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
        flash("Warning: forcing stale slot unlock for username: " + global_lock_user + " slot: " + \
               str(global_lock_slot_num))

        # Force previous stale slot lock to become unlocked
        #
        try:
            global_slot_lock.release(force=True)
        except OSError as exception:
            # We give up as we cannot force the unlock
            #
            print(str(exception))
            flash("ERROR: failed to force stale slot unlock for username: " + global_lock_user + \
                   " slot: " + str(global_lock_slot_num))
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
        # Carp
        #
        flash("ERROR: timeout on slot lock for username: " + username + " slot: " + slot_num_str)
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

    # unlock the global slot lock
    #
    if global_slot_lock:
        try:
            global_slot_lock.release(force=True)
        except OSError as exception:
            # We give up as we cannot unlock the slot
            #
            flash(str(exception))
            if not global_lock_user:
                global_lock_user = "((None))"
            if not global_lock_slot_num:
                global_lock_slot_num = "((no-slot))"
            flash("Warning: failed to unlock slot for username: " + global_lock_user + \
                  " slot: " + global_lock_slot_num)

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
    try:
        with open(slots_json_file, mode="w", encoding="utf-8") as slot_file_fp:
            slot_file_fp.write(json.dumps(slot_json, ensure_ascii=True, indent=4))
            slot_file_fp.write('\n')
            slot_file_fp.close()
    except OSError as exception:
        print(str(exception))
        flash("ERROR: failed to write out slot")
        return False
    return True


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
    user_dir = get_user_dir(username)
    if not user_dir:
        flash("username is not POSIX safe: " + username)
        return None
    umask(0o022)

    # process this slot for this user
    #
    slot = None

    # setup for the user's slot
    #
    slot_num_str = str(slot_num)
    slot_dir = get_slot_dir(username, slot_num)
    if not slot_dir:
        flash("invalid slot number: " + slot_num_str)
        return None
    slot_json_file = get_slot_json_filename(username, slot_num)
    if not slot_json_file:
        return None

    # first and foremost, lock the user slot
    #
    # NOTE: If needed the user directory and the slot directory will be created.
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        flash("ERROR: failed to lock for username: " + username + " slot: " + slot_num_str)
        return None

    # read the JSON file for the user's slot
    #
    # NOTE: We initialize the slot JSON file if the JSON file does not exist.
    #
    try:
        with open(slot_json_file, "r", encoding="utf-8") as slot_file_fp:
            slot = json.load(slot_file_fp)
            if slot["no_comment"] != NO_COMMENT_VALUE:
                flash("ERROR: invalid JSON no_comment")
                unlock_slot()
                return None
            if slot.slot["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
                flash("ERROR: JSON slot[" + slot_num_str + "] version: " + \
                      slot[slot_num].slot["slot_JSON_format_version"] + " != " + SLOT_VERSION_VALUE)
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
            flash("ERROR: invalid JSON no_comment")
            unlock_slot()
            return None
        if slot["slot_JSON_format_version"] != SLOT_VERSION_VALUE:
            flash("ERROR: JSON slot[" + slot_num_str + "] version: " + \
                  slot[slot_num].slot["slot_JSON_format_version"] + " != " + SLOT_VERSION_VALUE)
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
    user_dir = get_user_dir(username)
    if not user_dir:
        flash("username is not POSIX safe: " + username)
        return None
    umask(0o022)

    # process each slot for this user
    #
    slots = []
    for slot_num in range(0, MAX_SUBMIT_SLOT+1):

        # get the JSON slot
        #
        slots[slot_num] = get_json_slot(username, slot_num)

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
    slots = initialize_user(username)
    if not slots:
        if not global_errmsg:
            global_errmsg = "((empty))"
        flash("ERROR: cannot initialize user: " + username + \
              " error: " + global_errmsg)
        return False
    slot_num_str = str(slot_num)

    # open the file
    #
    try:
        with open(slot_file, "rb") as file_fp:
            result = hashlib.sha256(file_fp.read())
    except OSError as exception:
        print(str(exception))
        flash("ERROR: failed to open for username: " + username + " slot: " + \
              slot_num_str + " file: " + slot_file)
        return False

    # record and report SHA256 hash of file
    #
    slots[slot_num]['status'] = "Uploaded file into slot"
    slots[slot_num]['filename'] = os.path.basename(slot_file)
    slots[slot_num]['length'] = os.path.getsize(slot_file)
    dt = datetime.now(timezone.utc).replace(tzinfo=None)
    slots[slot_num]['date'] = re.sub(r'\.[0-9]{6}$', '', str(dt)) + " UTC"
    slots[slot_num]['sha256'] = result.hexdigest()
    flash("Uploaded file: " + os.path.basename(slot_file))
    flash("SHA256 hash of upload: " + slots[slot_num]['sha256'])
    user_dir = get_user_dir(username)
    if not user_dir:
        return False
    slots_json_file = get_slot_json_filename(username, slot_num)
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
        global_errmsg = "ERROR: in " + me + ": cannot read JSON in: " + \
                        jfile + " exception: " + str(exception)
        flash("ERROR: cannot open:" + jfile + " reason: " + str(exception))
        return []


def set_state(opdate, cldate):
    """
    Set contest dates.
    """

    # set the state file with open and close date/time
    #
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as sf_fp:
            sf_fp.write(json.dumps(f'{{ "opendate" : "{opdate}", "closedate" : "{cldate}" }}', \
                                   ensure_ascii=True, indent=4))
            sf_fp.write('\n')
            sf_fp.close()
    except OSError as exception:
        print(str(exception))
        print("couldn't write state file: " + STATE_FILE)


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


@auth.verify_password
def verify_password(username, password):
    """
    Standard Password Validation.
    """

    # paranoia - username must be a POSIX safe filename
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not re.match(POSIX_SAFE_RE, username):
        flash("username is not POSIX safe: " + username)
        return False

    # setup
    #
    users = readjfile(PW_FILE)
    if not users:
        flash("unable to read IOCCC password file")
        return False

    # verify password
    #
    if username in users and check_password_hash(users.get(username), password):
        return username
    return False


@application.route('/', methods=["GET"])
@auth.login_required
def index():
    """
    Basic User Interface.
    """

    # verify the contest is ioen
    #
    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        return render_template("closed.html")

    # setup
    #
    username = auth.current_user()

    # paranoia - username must be a POSIX safe filename
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not re.match(POSIX_SAFE_RE, username):
        return Response(response="Configuration error #0.0", status=400)

    # get the JSON slots for the user
    #
    slots = initialize_user(username)

    # verify we have slots
    #
    if not slots:
        return Response(response="Configuration error #0.1", status=400)

    # return main user interface
    #
    return render_template("index.html", user=username, etable=slots, date=str(cldate).replace('+00:00', ''))


@application.route('/admin', methods=["GET"])
@auth.login_required
def admin():
    """
    Present administrative page.
    """

    # setup
    #
    users = readjfile(PW_FILE)
    admins = readjfile(ADM_FILE)
    username = auth.current_user()

    # paranoia - username must be a POSIX safe filename
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not re.match(POSIX_SAFE_RE, username):
        return Response(response="Configuration error #1.0", status=400)

    # firewall
    #
    if not users:
        return Response(response="Configuration error #1.1", status=400)
    if not admins:
        return Response(response="Configuration error #1.2", status=400)

    # verify user is an admin
    #
    if not username in admins:
        return Response(response="Permission denied.", status=404)

    # read state file
    #
    st_info = readjfile(STATE_FILE)
    if st_info:
        opdate = st_info['opendate']
        cldate = st_info['closedate']
    else:
        opdate = DEF_OPDATE
        cldate = DEF_CLDATE

    # return admin interface page
    #
    return render_template("admin.html", contestants=users, user=username,
                           opdate=opdate, cldate=cldate)


@application.route('/update', methods=["POST"])
@auth.login_required
def upload():
    """
    Upload slot file
    """

    # verify that the contest is still open
    #
    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        flash("Contest Closed.")
        return redirect(IOCCC_ROOT)

    # setup
    #
    username = auth.current_user()

    # setup for user
    #
    user_dir = get_user_dir(username)
    if not user_dir:
        flash("username is not POSIX safe: " + username)
        return redirect(IOCCC_ROOT)

    # verify they selected a slot number to upload
    #
    if not 'slot_num' in request.form:
        flash("No slot selected")
        return redirect(IOCCC_ROOT)
    user_input = request.form['slot_num']
    try:
        slot_num = int(user_input)
    except ValueError:
        flash("Slot number is not a number: " + user_input)
        return redirect(IOCCC_ROOT)
    slot_num_str = user_input

    # verify slot number
    #
    slot_dir = get_slot_dir(username, slot_num)
    if not slot_dir:
        flash("invalid slot number: " + slot_num_str)
        return redirect(IOCCC_ROOT)

    # verify they selected a file to upload
    #
    if 'file' not in request.files:
        flash('No file part')
        return redirect(IOCCC_ROOT)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(IOCCC_ROOT)

    # verify that the filename is in a submit file form
    #
    re_match_str = "^submit\\." + username + "-" + slot_num_str + "\\.[1-9][0-9]{9,}\\.txz$"
    if not re.match(re_match_str, file.filename):
        flash("Filename for slot " + slot_num_str + " must match this regular expression: " + re_match_str)
        return redirect(IOCCC_ROOT)

    # lock the slot
    #
    slot_lock_fd = lock_slot(username, slot_num)
    if not slot_lock_fd:
        flash("for username: " + username + " cannot lock slot: " + slot_num_str)
        return redirect(IOCCC_ROOT)

    # save the file in the slot
    #
    upload_file = user_dir + "/" + slot_num_str  + "/" + file.filename
    file.save(upload_file)
    if not update_slot(username, slot_num, upload_file):
        flash('Failure updating slot file')
        # fallthru to unlock_slot

    # unlock the slot
    #
    unlock_slot()

    # return to the main user page
    #
    return redirect(IOCCC_ROOT)


@application.route('/admin-update', methods=["POST"])
@auth.login_required
def admin_update():
    """
    Backend admin update process.
    """

    # get users
    #
    users = readjfile(PW_FILE)
    if not users:
        return Response(response="Configuration error #2.0", status=400)

    # get username
    #
    username = auth.current_user()
    if not username:
        return Response(response="Configuration error #2.1", status=400)

    # paranoia - username must be a POSIX safe filename
    #
    # This also prevents username with /, and prevents it from being empty string,
    # thus one cannot create a username with system cracking "funny business".
    #
    if not re.match(POSIX_SAFE_RE, username):
        return Response(response="Configuration error #2.2", status=400)

    # get admins
    #
    admins = readjfile(ADM_FILE)
    if not admins:
        return Response(response="Configuration error #2.3", status=400)

    # firewall
    #
    if not username in admins:
        return Response(response="Permission denied!", status=404)

    # setup
    #
    user_dir = get_user_dir(username)
    if not user_dir:
        flash("username is not POSIX safe: " + username)
        return redirect(IOCCC_ROOT)
    umask(0o022)

    # read the state file
    #
    st_info = readjfile(STATE_FILE)
    if st_info:
        opdate = st_info['opendate']
        cldate = st_info['closedate']
    else:
        # No state file, so use default open and close dates
        opdate = DEF_OPDATE
        cldate = DEF_CLDATE

    # obtain open and close date/time from form if available
    #
    if "opendate" in request.form and not request.form['opendate'] == '':
        opdate = request.form['opendate']
    if "closedate" in request.form and not request.form['closedate'] == '':
        cldate = request.form['closedate']

    # store the open and close date/time in the state file
    #
    set_state(opdate, cldate)

    # obtain the new username from form if available
    #
    if "newuser" in request.form:
        newuser = request.form['newuser']
        if not newuser == "":
            if not re.match("[a-zA-Z0-9][a-zA-Z0-9.@_+-]+", newuser):
                flash('bad username for new user.')
                return redirect("/admin")
            if newuser in users:
                flash('username already in use.')
                return redirect('/admin')
            ret = adduser(newuser, PW_FILE)
            if ret:
                (user, password) = ret
                flash(f"user: {user} password: {password}")

    # case: attempting to delete a user
    #
    for key in request.form:
        if request.form[key] in admins:
            flash(request.form[key] + ' is an admin and cannot be deleted.')
            return redirect('/admin')
        if re.match('^contest.*', key):
            deluser(request.form[key], IOCCC_DIR, PW_FILE)

    # return to admin user page
    #
    return redirect("/admin")


@application.route('/logout')
@auth.login_required
def logout():
    """
    Gross hack to invalidate the BasicAuth session

    See https://stackoverflow.com/questions/233507/how-to-log-out-user-from-web-site-using-basic-authentication
    """

    # hack !!! :-)
    #
    return redirect("http://logout:@" + HOST_NAME + ":" + TCP_PORT + "/")


#skip# @application.route('/register', methods=["GET"])
#skip# def register():
#skip#     opdate, cldate, now = check_state()
#skip#     return render_template("register.html", date=cldate)
#skip#
#skip#
#skip# @application.route('/reg', methods=["POST"])
#skip# def reg():
#skip#     if not ("firstname" in request.form and "lastname" in request.form
#skip#             and "email" in request.form and "rules" in request.form ):
#skip#         flash("Form not complete")
#skip#         return(redirect(ioccc_root + "/register"))
#skip#     email = request.form['email']
#skip#     if (len(request.form['firstname']) < 1 or len(request.form['lastname']) < 1
#skip#         or not re.match("[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}$", email)):
#skip#         flash("Form not properly complete.")
#skip#         return(redirect(ioccc_root + "/register"))
#skip#     if (not request.form['rules']):
#skip#         flash("Rules not agreed.")
#skip#         return(redirect(ioccc_root + "/register"))
#skip#     return render_template("re-confirm.html")


# case: debugging via direct execution
#
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=TCP_PORT)
