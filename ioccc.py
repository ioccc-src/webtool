#!/usr/bin/env python3
# pylint: disable=import-error
# pylint: disable=wildcard-import
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=unused-wildcard-import
# pylint: disable=unused-import
"""
The IOCCC submit server
"""

# system imports
#
import hashlib
import uuid
import inspect


# 3rd party imports
#
from flask import Flask, Response, url_for, render_template, flash, redirect, request
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
from ioccc_common import *


# Submit tool server version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "0.5.3 2024-10-25"


# Configure the app
#
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_TARBALL_LEN
app.config['FLASH_AKK'] = "ioccc-submit-tool"
app.config['FLASK_DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['BASIC_AUTH_FORCE'] = True
#
# We will read the 1st line of the SECRET_FILE, ignoring the newline
#
# IMPORTANT: You MUST generate the secret key once and then
#            copy/paste the value into your app or store it as an
#            environment variable. Do NOT regenerate the secret key within
#            the app, or you will get a new value for each instance
#            of the app, which can cause issues when you deploy to
#            production since each instance of the app has a
#            different SECRET_KEY value.
#
try:
    with open(SECRET_FILE, 'r', encoding="utf-8") as secret:
        app.secret_key = secret.read().rstrip()
        secret.close()
except OSError:
    # FALLBACK: generate on the fly for testing
    #
    # IMPORTANT: This will not work for production as different
    #            instances of this app will have different secrets.
    #
    app.secret_key = str(uuid.uuid4())


# start HTTP Basic authorization
#
auth = HTTPBasicAuth()


# set app file paths
#
with app.test_request_context('/'):
    url_for('static', filename='style.css')
    url_for('static', filename='script.js')
    url_for('static', filename='ioccc.png')


@auth.verify_password
def verify_password(username, password):
    """
    Standard Password Validation.
    """

    # Return False if:
    #
    # if the username is not valid, or
    # if the username is not in the password file, or
    # if the username is not allowed to login, or
    # if the password is not the correct password for the username
    #
    # Otherwise return True:
    #
    # if the username is valid, and
    # if the username is in the password file, and
    # if the username is allowed to login, and
    # if the password is the correct password for the username
    #
    return verify_user_password(username, password)


@app.route('/', methods=["GET"])
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
    slots = initialize_user_tree(username)

    # verify we have slots
    #
    if not slots:
        return Response(response="Configuration error #0.1", status=400)

    # return main user interface
    #
    return render_template("index.html", user=username, etable=slots, date=str(cldate).replace('+00:00', ''))


@app.route('/update', methods=["POST"])
@auth.login_required
def upload():
    """
    Upload slot file
    """

    # verify that the contest is still open
    #
    opdate, cldate, now = check_state()
    if now < opdate or now > cldate:
        flash("The IOCCC is closed.")
        return redirect(IOCCC_ROOT)

    # get usernmame
    #
    username = auth.current_user()

    # setup for user
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        flash("ERROR: " + return_last_errmsg())
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
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        flash("ERROR: " + return_last_errmsg())
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
        flash("ERROR: " + return_last_errmsg())
        return redirect(IOCCC_ROOT)

    # save the file in the slot
    #
    upload_file = user_dir + "/" + slot_num_str  + "/" + file.filename
    file.save(upload_file)
    if not update_slot(username, slot_num, upload_file):
        flash("ERROR: " + return_last_errmsg())
        # fallthru to unlock_slot()

    # unlock the slot
    #
    if not unlock_slot():
        flash("ERROR: " + return_last_errmsg())
        # fallthru to redirect(IOCCC_ROOT)

    # report on the successful upload
    #
    flash("Uploaded file: " + file.filename)

    # return to the main user page
    #
    return redirect(IOCCC_ROOT)


@app.route('/logout')
@auth.login_required
def logout():
    """
    Gross hack to invalidate the BasicAuth session

    See https://stackoverflow.com/questions/233507/how-to-log-out-user-from-web-site-using-basic-authentication
    """

    # hack !!! :-)
    #
    print("http://log:out@" + HOST_NAME + ":" + TCP_PORT + "/" + " with code=401")
    return redirect("http://log:out@" + HOST_NAME + ":" + TCP_PORT + "/", code=401)


# case: debugging via direct execution
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=TCP_PORT)
