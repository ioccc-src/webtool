#!/usr/bin/env python3
# pylint: disable=import-error
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
# pylint: disable=unused-import
"""
The IOCCC submit server

NOTE: This code is modeled after:

    https://github.com/costa-rica/webApp01-Flask-Login/tree/github-main
    https://nrodrig1.medium.com/flask-login-no-flask-sqlalchemy-d62310bb43e3
"""

# system imports
#
import uuid
import inspect


# import from modules
#
from typing import Dict, Optional


# 3rd party imports
#
from flask import Flask, render_template, request, redirect, url_for, flash
import flask_login
from flask_login import current_user


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
# TO DO: Change wild card import into specific import set
#
from ioccc_common import *


# ioccc.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.2 2024-11-17"


# Configure the app
#
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_TARBALL_LEN
app.config['FLASH_APP'] = "ioccc-submit-tool"
app.debug = True
app.config['FLASK_ENV'] = "development"
app.config['TEMPLATES_AUTO_RELOAD'] = True
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
    # FALLBACK: generate on a secret the fly for testing
    #
    # IMPORTANT: This exception case may not work well in production as
    #            different instances of this app will have different secrets.
    #
    app.secret_key = str(uuid.uuid4())


# set app file paths
#
with app.test_request_context('/'):
    url_for('static', filename='style.css')
    url_for('static', filename='script.js')
    url_for('static', filename='ioccc.png')


# Setup the login manager
#
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


# Trivial user class
#
class User(flask_login.UserMixin):
    """
    Trivial user class
    """
    user_dict = None
    id = None
    authenticated = False

    def __init__(self,username):
        self.user_dict = lookup_username(username)
        if self.user_dict:
            self.id = username

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the username to satisfy Flask-Login's requirements."""
        return self.id

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False


@login_manager.user_loader
def user_loader(user_id):
    """
    load the user
    """
    user =  User(user_id)
    if user.id:
        return user
    return None


@app.route('/', methods = ['GET', 'POST'])
def login():
    """
    Process login request
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name

    # process POST
    #
    if request.method == 'POST':
        form_dict = request.form.to_dict()
        username = form_dict.get('username')

        # If the user is allowed to login
        #
        user = User(username)
        if user.id and user_allowed_to_login(user.user_dict):

            # validate password
            #
            if verify_hashed_password(form_dict.get('password'),
                                      user.user_dict['pwhash']):
                user.authenticated  = True
                flask_login.login_user(user)

            # get the JSON slots for the user and verify we have slots
            #
            slots = initialize_user_tree(username)
            if not slots:
                flash("ERROR: in: " + me + ": initialize_user_tree() failed: <<" + \
                      return_last_errmsg() + ">>")
                return redirect(url_for('login'))

            # case: user is required to change password
            #
            if must_change_password(user.user_dict):
                flash("user is required to change password - TO DO - add code here")

            # render based on if the contest is open or not
            #
            close_datetime = contest_is_open()
            if close_datetime:

                # case: contest open - both login and user setup are successful
                #
                return render_template('submit.html',
                                       flask_login = flask_login,
                                       username = username,
                                       etable = slots,
                                       date=str(close_datetime).replace('+00:00', ''))

            # case: contest is not open - both login and user setup are successful
            #
            flash("The IOCCC is not open.")
            return render_template('not-open.html',
                                   flask_login = flask_login,
                                   username = username,
                                   etable = slots)

    # case: unable to login
    #
    return render_template('login.html')


# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
#
@app.route('/submit', methods = ['GET', 'POST'])
@flask_login.login_required
def submit():
    """
    Access the IOCCC Submission Page - Upload a file to a user's slot
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name

    # get username
    #
    if not current_user.id:
        flash("Login required.")
        flask_login.logout_user()
        return redirect(url_for('login'))
    username = current_user.id
    # paranoia
    if not username:
        flash("Login required.")
        flask_login.logout_user()
        return redirect(url_for('login'))

    # setup for user
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        flash("ERROR: in: " + me + ": return_user_dir_path() failed: <<" + \
              return_last_errmsg() + ">>")
        flask_login.logout_user()
        return redirect(url_for('login'))

    # get the JSON for all slots for the user
    #
    slots = get_all_json_slots(username)
    if not slots:
        flash("ERROR: in: " + me + ": get_all_json_slots() failed: <<" + \
              return_last_errmsg() + ">>")
        flask_login.logout_user()
        return redirect(url_for('login'))

    # verify that the contest is still open
    #
    close_datetime = contest_is_open()
    if not close_datetime:
        flash("The IOCCC is not open.")
        return render_template('not-open.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots)

    # verify they selected a slot number to upload
    #
    if not 'slot_num' in request.form:
        flash("No slot selected")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    user_input = request.form['slot_num']
    try:
        slot_num = int(user_input)
    except ValueError:
        flash("Slot number is not a number: " + user_input)
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    slot_num_str = user_input

    # verify slot number
    #
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        flash("ERROR: in: " + me + ": return_slot_dir_path() failed: <<" + \
              return_last_errmsg() + ">>")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # verify they selected a file to upload
    #
    if 'file' not in request.files:
        flash('No file part')
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # verify that the filename is in a submit file form
    #
    re_match_str = "^submit\\." + username + "-" + slot_num_str + "\\.[1-9][0-9]{9,}\\.txz$"
    if not re.match(re_match_str, file.filename):
        flash("Filename for slot " + slot_num_str + " must match this regular expression: " + re_match_str)
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # save the file in the slot
    #
    upload_file = user_dir + "/" + slot_num_str  + "/" + file.filename
    file.save(upload_file)
    if not update_slot(username, slot_num, upload_file):
        flash("ERROR: in: " + me + ": update_slot() failed: <<" + \
              return_last_errmsg() + ">>")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # report on the successful upload
    #
    flash("Uploaded file: " + file.filename)
    return render_template('submit.html',
                           flask_login = flask_login,
                           username = username,
                           etable = slots,
                           date=str(close_datetime).replace('+00:00', ''))
#
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements


# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
#
@app.route('/update', methods=["POST"])
@flask_login.login_required
def upload():
    """
    Upload slot file
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name

    # get username
    #
    if not current_user.id:
        flash("Login required.")
        return redirect(url_for('login'))
    username = current_user.id
    # paranoia
    if not username:
        flash("Login required.")
        return redirect(url_for('login'))

    # get the JSON for all slots for the user
    #
    slots = get_all_json_slots(username)
    if not slots:
        flash("ERROR: in: " + me + ": get_all_json_slots() failed: <<" + \
              return_last_errmsg() + ">>")
        return redirect(url_for('login'))

    # setup for user
    #
    user_dir = return_user_dir_path(username)
    if not user_dir:
        flash("ERROR: in: " + me + ": return_user_dir_path() failed: <<" + \
              return_last_errmsg() + ">>")
        return redirect(url_for('login'))

    # verify that the contest is still open
    #
    close_datetime = contest_is_open()
    if not close_datetime:
        flash("The IOCCC is not open.")
        return render_template('not-open.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots)

    # verify they selected a slot number to upload
    #
    if not 'slot_num' in request.form:
        flash("No slot selected")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    user_input = request.form['slot_num']
    try:
        slot_num = int(user_input)
    except ValueError:
        flash("Slot number is not a number: " + user_input)
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    slot_num_str = user_input

    # verify slot number
    #
    slot_dir = return_slot_dir_path(username, slot_num)
    if not slot_dir:
        flash("ERROR: in: " + me + ": return_slot_dir_path() failed: <<" + \
              return_last_errmsg() + ">>")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # verify they selected a file to upload
    #
    if 'file' not in request.files:
        flash('No file part')
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # verify that the filename is in a submit file form
    #
    re_match_str = "^submit\\." + username + "-" + slot_num_str + "\\.[1-9][0-9]{9,}\\.txz$"
    if not re.match(re_match_str, file.filename):
        flash("Filename for slot " + slot_num_str + " must match this regular expression: " + re_match_str)
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # save the file in the slot
    #
    upload_file = user_dir + "/" + slot_num_str  + "/" + file.filename
    file.save(upload_file)
    if not update_slot(username, slot_num, upload_file):
        flash("ERROR: in: " + me + ": update_slot() failed: <<" + \
              return_last_errmsg() + ">>")
        return render_template('submit.html',
                               flask_login = flask_login,
                               username = username,
                               etable = slots,
                               date=str(close_datetime).replace('+00:00', ''))

    # report on the successful upload
    #
    flash("Uploaded file: " + file.filename)

    # both login and user setup are successful
    #
    return render_template('submit.html',
                           flask_login = flask_login,
                           username = username,
                           etable = get_all_json_slots(username),
                           date=str(close_datetime).replace('+00:00', ''))
#
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements


@app.route('/logout')
def logout():
    """
    Logout.
    """
    flask_login.logout_user()
    return redirect(url_for('login'))


# Run the app on a given port
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=TCP_PORT)
