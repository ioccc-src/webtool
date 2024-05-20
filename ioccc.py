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

# entry numbers from 0 to MAX_SUBMIT_SLOT
#
# IMPORTANT: MAX_SUBMIT_SLOT must match MAX_SUBMIT_SLOT in soup/limit_ioccc.h
# in the mkiocccentry repo:
#
#   https://github.com/ioccc-src/mkiocccentry
#
# XXX - TODO - put a note in soup/limit_ioccc.h referring back to MAX_SUBMIT_SLOT as well - XXX
#
MAX_SUBMIT_SLOT = 9

def write_entries(entry_file, entries):
    """
    Write out an index of entries for the user.
    """
    try:
        with open(entry_file, mode="w", encoding="utf-8") as entries_fp:
            entries_fp.write(json.dumps(entries, ensure_ascii=True, sort_keys=True, indent=4))
            entries_fp.write('\n')
            entries_fp.close()
    except IOError as excpt:
        print(str(excpt))
        return None
    return True

def get_entries(user):
    """
    read in the entry list for a given user.
    """

    # setup
    #
    user_dir = IOCCC_DIR + "/users/" + user
    entries_file = user_dir + "/entries.json"
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
    for i in range(0, MAX_SUBMIT_SLOT+1):
        submit_dir = user_dir + "/" + str(i)
        try:
            makedirs(submit_dir, exist_ok=True)
        except OSError as excpt:
            print(str(excpt))
            return None

    # form the entries JSON files
    #
    try:
        with open(entries_file, "r", encoding="utf-8") as entries_fp:
            entries = json.load(entries_fp)
    except IOError:
        entries = {
            0: "No entry",
            1: "No entry",
            2: "No entry",
            3: "No entry",
            4: "No entry",
            5: "No entry",
            6: "No entry",
            7: "No entry",
            8: "No entry",
            9: "No entry",
        }
        if not write_entries(entries_file, entries):
            return None
    return entries

def update_entries(username, entry_no, filename):
    """
    Update a given entry for a given user.
    """
    entries = get_entries(username)
    user_dir = IOCCC_DIR + "/users/" + username
    entries_file = user_dir + "/entries.json"
    if not entries:
        return None
    try:
        with open(filename, "rb") as file_fp:
            result = hashlib.sha256(file_fp.read())
    except IOError as excpt:
        print(str(excpt))
        return None
    entries[entry_no] = result.hexdigest()
    print("entry_no = " + entry_no + " hash = " + entries[entry_no])
    if not write_entries(entries_file, entries):
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
    if username in users and \
            check_password_hash(users.get(username), password):
        return username
    return False

@application.route('/', methods=["GET"])
@auth.login_required
def index():
    """
    Basic User Interface.
    """
    username = auth.current_user()
    entries = get_entries(username)
    if not entries:
        return Response(response="Configuration error", status=400)
    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        return render_template("closed.html")
    return render_template("index.html", user=username, etable=entries, date=str(cldate))

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
    Upload Entries
    """
    username = auth.current_user()
    user_dir = IOCCC_DIR + "/users/" + username

    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        flash("Contest Closed.")
        return redirect(IOCCC_ROOT)
    if not 'entry_no' in request.form:
        flash("No entry selected")
        return redirect(IOCCC_ROOT)
    entry_no = request.form['entry_no']
    if 'file' not in request.files:
        flash('No file part')
        return redirect(IOCCC_ROOT)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(IOCCC_ROOT)
    re_match_str = "^submit\." + username + "-" + entry_no + "\.[1-9][0-9]{9,}\.txz$"
    if (not re.match(re_match_str, file.filename)):
        flash("Filename for slot " + entry_no + " must match this regular expression: " + re_match_str)
        return redirect(IOCCC_ROOT)
    entryfile = user_dir + "/" + entry_no  + "/" + file.filename
    file.save(entryfile)
    if not update_entries(username, entry_no, entryfile):
        flash('Failure updating entries')
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

