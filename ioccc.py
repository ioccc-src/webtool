#!/usr/bin/env python3
"""
Routines to implement IOCCC registration functions.
"""
import re
import json
import hashlib
from os import makedirs, umask
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from flask import Flask, Response, url_for, render_template, flash, redirect, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from iocccpasswd import adduser, deluser

# For user slot locking
#
# See:
#
#   https://snyk.io/advisor/python/filelock/example for filelock examples
#   https://py-filelock.readthedocs.io/en/latest/index.html
#
from filelock import Timeout, FileLock

application = Flask(__name__)

# compressed tarball size limit in bytes
#
# IMPORTANT: application.config['MAX_CONTENT_LENGTH'] match MAX_TARBALL_LEN in soup/limit_ioccc.h
# in the mkiocccentry repo:
#
#   https://github.com/ioccc-src/mkiocccentry
#
# XXX - TODO - put a note in soup/limit_ioccc.h referring back to MAX_CONTENT_LENGTH as well - XXX
#
# BTW: 3999971 is the largest prime < 4000000
#
application.config['MAX_CONTENT_LENGTH'] = 3999971

# XXX TODO: Use the GitHub method of hiding keys that needs to be deployed
#
# XXX - flask requires application.secret_key to be set, change before deployment
application.secret_key = "CHANGE_ME"

application.config['BASIC_AUTH_FORCE'] = True
auth = HTTPBasicAuth()

with application.test_request_context('/'):
    url_for('static', filename='style.css')
    url_for('static', filename='script.js')
    url_for('static', filename='ioccc.png')

HOST_NAME = "127.0.0.1"
TCP_PORT = "8191"

IOCCC_ROOT = "/"
IOCCC_DIR = "/app"
PW_FILE = IOCCC_DIR + "/etc/iocccpasswd"
STATE_FILE = IOCCC_DIR + "/state"
ADM_FILE = IOCCC_DIR + "/etc/admins"

# slot numbers from 0 to MAX_SUBMIT_SLOT_NUM
#
# IMPORTANT: MAX_SUBMIT_SLOT_NUM must match MAX_SUBMIT_SLOT in soup/limit_ioccc.h
# in the mkiocccentry repo:
#
#   https://github.com/ioccc-src/mkiocccentry
#
# XXX - TODO - put a note in soup/limit_ioccc.h referring back to MAX_SUBMIT_SLOT_NUM as well - XXX
#
MAX_SUBMIT_SLOT_NUM = 9

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
# will force that previous lock to be unlocked (and report via flash).
#
GLOBAL_SLOT_LOCK = None         # lock file descriptor or none
GLOBAL_LOCK_USER = None         # user whose slot is locked or none
GLOBAL_LOCK_SLOT_NUM = None     # slot number that is locked or none


def lock_slot(user, slot_num):
    """
    lock a slot

    Given:
        user        username
        slot_num    slot number

        Force a previously locked slot to be unlocked,
        Lock the new slot.
        Register the locked slot.

    Returns:
        lock file descriptor    lock successful
        None                    lock not successful

    NOTE: We force the use of the Unix flock(2) mechanism as a singleton lock.
          We do NOT wish to support nor use Windows file locking.
          We use the python filelock module.  See:

              https://pypi.org/project/filelock/
              https://py-filelock.readthedocs.io/en/latest/api.html
              https://snyk.io/advisor/python/filelock/example
    """

    # setup
    #
    user_dir = IOCCC_DIR + "/users/" + user
    slot_dir = user_dir + "/" + slot_num
    lock_file = user_dir + "/lock"

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, mode=0o2770, exist_ok=True)
    except OSError as excpt:
        print(str(excpt))
        flash("ERROR: failed to create user dir: " + GLOBAL_LOCK_USER);
        return None

    # be sure the slot directory exits
    #
    try:
        makedirs(slot_dir, mode=0o2770, exist_ok=True)
    except OSError as excpt:
        print(str(excpt))
        return None

    # Force any stale slot lock to become unlocked
    #
    if not GLOBAL_SLOT_LOCK:
        # Carp
        #
        if not GLOBAL_LOCK_USER:
            GLOBAL_LOCK_USER = "((None))"
        if not GLOBAL_LOCK_SLOT_NUM:
            GLOBAL_LOCK_SLOT_NUM = "((no-slot))"
        flash("Warning: unlocking stale slot lock for user: " + GLOBAL_LOCK_USER + " slot: " + GLOBAL_LOCK_SLOT_NUM);

        # Force previous stale slot lock to become unlocked
        #
        try:
            GLOBAL_SLOT_LOCK.release()
        except IOError as excpt:
            # We give up as we cannot force the unlock
            #
            print(str(excpt))
            flash("ERROR: failed to force stale unlock slot lock for user: " + GLOBAL_LOCK_USER + " slot: " + GLOBAL_LOCK_SLOT_NUM);
            GLOBAL_SLOT_LOCK = None
            GLOBAL_LOCK_USER = None
            GLOBAL_LOCK_SLOT_NUM = None
            return None

        # clear the global lock information
        #
        GLOBAL_SLOT_LOCK = None
        GLOBAL_LOCK_USER = None
        GLOBAL_LOCK_SLOT_NUM = None

    # Lock the slot
    #
    slot_lock_fd = FileLock.UnixFileLock(lockfile, timeout=LOCK_TIMEOUT, is_singleton=True)
    try:
        with slot_lock_fd:
            # note our new lock
            #
            GLOBAL_SLOT_LOCK = slot_lock_fd
            GLOBAL_LOCK_USER = user
            GLOBAL_LOCK_SLOT_NUM = slot_num
    except Timeout:
            # Carp
            #
            flash("ERROR: timeout on slot lock for user: " + user + " slot: " + slot_num)
            return None

    # return the slot lock success
    #
    return slot_lock_fd


def unlock_slot():
    """
    unlock a previously locked slot

    A slot locked via lock_slot(user, slot_num) is unlocked
    using the GLOBAL_SLOT_LOCK that noted the slot lock descriptor.

    Returns:
        True    slot unlock successful
        None    failed to unlock slot
    """

    # unlock the global slot lock
    #
    if not GLOBAL_SLOT_LOCK:
        try:
            GLOBAL_SLOT_LOCK.release(force=True)
        except IOError as excpt:
            # We give up as we cannot unlock the slot
            #
            print(str(excpt))
        if not GLOBAL_LOCK_USER:
            GLOBAL_LOCK_USER = "((None))"
        if not GLOBAL_LOCK_SLOT_NUM:
            GLOBAL_LOCK_SLOT_NUM = "((no-slot))"
        flash("Warning: failed to unlock slot for user: " + GLOBAL_LOCK_USER + " slot: " + GLOBAL_LOCK_SLOT_NUM);

    # Carp about lack of slot lock to unlock
    #
    else:
        flash("Warning: no previous slot lock found")

    return None


def write_slots(slots_json_file, slots):
    """
    Write out an index of slots for the user.
    """
    try:
        with open(slots_json_file, mode="w", encoding="utf-8") as slots_file_fp:
            slots_file_fp.write(json.dumps(slots, ensure_ascii=True, sort_keys=True, indent=4))
            slots_file_fp.write('\n')
            slots_file_fp.close()
    except IOError as excpt:
        print(str(excpt))
        return None
    return True


def get_slots(user):
    """
    read in the slot list for a given user.
    """

    # setup
    #
    user_dir = IOCCC_DIR + "/users/" + user
    slots_json_file = user_dir + "/slots.json"
    umask(0o022)

    # be sure the user directory exists
    #
    try:
        makedirs(user_dir, exist_ok=True)
    except OSError as excpt:
        print(str(excpt))
        return None

    # be sure each submission sub-directory under the user directory exists
    #
    for i in range(0, MAX_SUBMIT_SLOT_NUM+1):
        submit_dir = user_dir + "/" + str(i)
        try:
            makedirs(submit_dir, exist_ok=True)
        except OSError as excpt:
            print(str(excpt))
            return None

    # form the slots JSON files
    #
    try:
        with open(slots_json_file, "r", encoding="utf-8") as slots_file_fp:
            slots = json.load(slots_file_fp)
    except IOError:
        slots = {
            0: "No slot file",
            1: "No slot file",
            2: "No slot file",
            3: "No slot file",
            4: "No slot file",
            5: "No slot file",
            6: "No slot file",
            7: "No slot file",
            8: "No slot file",
            9: "No slot file",
        }
        if not write_slots(slots_json_file, slots):
            return None
    return slots


def update_slots(username, slot_num, filename):
    """
    Update a given slot for a given user.
    """
    slots = get_slots(username)
    user_dir = IOCCC_DIR + "/users/" + username
    slots_json_file = user_dir + "/slots.json"
    if not slots:
        return None
    try:
        with open(filename, "rb") as file_fp:
            result = hashlib.sha256(file_fp.read())
    except IOError as excpt:
        print(str(excpt))
        return None
    slots[slot_num] = result.hexdigest()
    print("slot_num = " + slot_num + " hash = " + slots[slot_num])
    if not write_slots(slots_json_file, slots):
        return None
    return True


def readjfile(pwfile):
    """
    read a password (or really any JSON) file.
    """
    try:
        with open(pwfile, 'r', encoding="utf-8") as pw_fp:
            return json.load(pw_fp)
    except FileNotFoundError:
        return []

def set_state(opdate, cldate):
    """
    Set contest dates.
    """
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as sf_fp:
            sf_fp.write(f'{{ "opendate" : "{opdate}", "closedate" : "{cldate}" }}')
            sf_fp.write('\n')
            sf_fp.close()
    except OSError as excpt:
        print("couldn't write STATE_FILE: " + str(excpt))


def check_state():
    """
    See if the contest is opened.
    """
    st_info = readjfile(STATE_FILE)
    if st_info:
        the_time = datetime.fromisoformat(st_info['opendate'])
        opdate = datetime(the_time.year, the_time.month, the_time.day, tzinfo=ZoneInfo("UTC"))
        the_time = datetime.fromisoformat(st_info['closedate'])
        cldate = datetime(the_time.year, the_time.month, the_time.day, tzinfo=ZoneInfo("UTC"))
    else:
        opdate = datetime(2024, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        cldate = datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
    now = datetime.now(timezone.utc)
    return opdate, cldate, now


@auth.verify_password
def verify_password(username, password):
    """
    Standard Password Validation.
    """
    users = readjfile(PW_FILE)
    if username in users and check_password_hash(users.get(username), password):
        return username
    return False


@application.route('/', methods=["GET"])
@auth.login_required
def index():
    """
    Basic User Interface.
    """
    username = auth.current_user()
    slots = get_slots(username)
    if not slots:
        return Response(response="Configuration error", status=400)
    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        return render_template("closed.html")
    return render_template("index.html", user=username, etable=slots, date=str(cldate))


@application.route('/admin', methods=["GET"])
@auth.login_required
def admin():
    """
    Present administrative page.
    """
    users = readjfile(PW_FILE)
    username = auth.current_user()
    admins = readjfile(ADM_FILE)
    if not username in admins:
        return Response(response="Permission denied.", status=404)
    if not users:
        return Response(response="Configuration error", status=400)
    st_info = readjfile(STATE_FILE)
    if st_info:
        opdate = st_info['opendate']
        cldate = st_info['closedate']
    else:
        opdate = str(date.today())
        cldate = opdate
    return render_template("admin.html", contestants=users, user=username,
                           opdate = opdate, cldate=cldate)


@application.route('/update', methods=["POST"])
@auth.login_required
def upload():
    """
    Upload slot file
    """
    username = auth.current_user()
    user_dir = IOCCC_DIR + "/users/" + username

    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        flash("Contest Closed.")
        return redirect(IOCCC_ROOT)
    if not 'slot_num' in request.form:
        flash("No slot selected")
        return redirect(IOCCC_ROOT)
    slot_num = request.form['slot_num']
    if 'file' not in request.files:
        flash('No file part')
        return redirect(IOCCC_ROOT)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(IOCCC_ROOT)
    re_match_str = "^submit\\." + username + "-" + slot_num + "\\.[1-9][0-9]{9,}\\.txz$"
    if (not re.match(re_match_str, file.filename)):
        flash("Filename for slot " + slot_num + " must match this regular expression: " + re_match_str)
        return redirect(IOCCC_ROOT)
    slot_file = user_dir + "/" + slot_num  + "/" + file.filename
    file.save(slot_file)
    if not update_slots(username, slot_num, slot_file):
        flash('Failure updating slot file')
    return redirect(IOCCC_ROOT)


@application.route('/admin-update', methods=["POST"])
@auth.login_required
def admin_update():
    """
    Backend admin update process.
    """
    users = readjfile(PW_FILE)
    username = auth.current_user()
    admins = readjfile(ADM_FILE)
    if not username in admins:
        return Response(response="Permission denied.", status=404)
    st_info = readjfile(STATE_FILE)
    if st_info:
        opdate = st_info['opendate']
        cldate = st_info['closedate']
    else:
        opdate = str(date.today())
        cldate = opdate
    if "opendate" in request.form and not request.form['opendate'] == '':
        opdate = request.form['opendate']
    if "closedate" in request.form and not request.form['closedate'] == '':
        cldate = request.form['closedate']
    set_state(opdate, cldate)
    if "newuser" in request.form:
        newuser = request.form['newuser']
        if not newuser == "":
            if not re.match("[a-zA-Z0-9.@_+-]+", newuser):
                flash('bad username for new user.')
                return redirect("/admin")
            if newuser in users:
                flash('username already in use.')
                return redirect('/admin')
            ret = adduser(newuser, PW_FILE)
            if ret:
                (user, password) = ret
                flash(f"user: {user} password: {password}")
    for key in request.form:
        if request.form[key] in admins:
            flash(request.form[key] + ' is an admin and cannot be deleted.')
            return redirect('/admin')
        if re.match('^contest.*', key):
            deluser(request.form[key], IOCCC_DIR, PW_FILE)
    return redirect("/admin")


@application.route('/logout')
@auth.login_required
def logout():
    """
    Gross hack to invalidate the BasicAuth session

    See https://stackoverflow.com/questions/233507/how-to-log-out-user-from-web-site-using-basic-authentication
    """
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


if __name__ == '__main__':
    application.run(host='0.0.0.0', port=TCP_PORT)

