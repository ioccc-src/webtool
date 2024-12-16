#!/usr/bin/env python3
#
# pylint: disable=invalid-overridden-method
# pylint: disable=too-many-statements
#
"""
The IOCCC submit tool

This code is used to upload submissions to an open IOCCC (International
Obfuscated C Code Contest) to the submit.ioccc.org server.

This code is based on code originally written by Eliot Lear (@elear) in late 2021.
The [IOCCC judges](https://www.ioccc.org/judges.html) heavily modified
Eliot's code, so any fault you find should be blamed on them 😉 (that is, the
IOCCC Judges :-) ).

NOTE: This flask-login was loosly modeled after:

    https://github.com/costa-rica/webApp01-Flask-Login/tree/github-main
    https://nrodrig1.medium.com/flask-login-no-flask-sqlalchemy-d62310bb43e3
"""

# system imports
#
import sys
# sys.path.insert(0,"/var/www/html/venv/lib/python3.9/site-packages")
# sys.path.insert(0,"/var/www/html/wsrc")
# sys.path.insert(0,"/var/www/html")
import inspect
import argparse
import os
import re
import datetime # DEBUG - remove when finished
import getpass # DEBUG - remove when finished
import threading # DEBUG - remove when finished
import glob # DEBUG - remove when finished
from pathlib import Path # DEBUG - remove when finished


# 3rd party imports
#
from flask import Flask, render_template, request, redirect, url_for, flash
import flask_login
from flask_login import current_user


# import the ioccc python utility code
#
# Sort the import list with: sort -d -u
#
from iocccsubmit.ioccc_common import \
    APPDIR, \
    MAX_PASSWORD_LENGTH, \
    MAX_TARBALL_LEN, \
    MIN_PASSWORD_LENGTH, \
    TCP_PORT, \
    change_startup_appdir, \
    contest_is_open, \
    get_all_json_slots, \
    initialize_user_tree, \
    is_proper_password, \
    lookup_username, \
    must_change_password, \
    return_last_errmsg, \
    return_secret, \
    return_slot_dir_path, \
    return_user_dir_path, \
    update_password, \
    update_slot, \
    user_allowed_to_login, \
    verify_hashed_password


# ioccc.py version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "1.6.2 2024-12-15"


# Configure the application
#
application = Flask(__name__,
            template_folder=APPDIR + '/templates',
            root_path=APPDIR)
application.config['MAX_CONTENT_LENGTH'] = MAX_TARBALL_LEN
application.config['FLASH_APP'] = "iocccsubmit"
application.debug = True
application.config['FLASK_ENV'] = "development"
application.config['TEMPLATES_AUTO_RELOAD'] = True
application.secret_key = return_secret()

# set application file paths
#
with application.test_request_context('/'):
    url_for('static', filename='style.css')
    url_for('static', filename='script.js')
    url_for('static', filename='ioccc.png')


# Setup the login manager
#
login_manager = flask_login.LoginManager()
login_manager.init_app(application)


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


@application.route('/', methods = ['GET', 'POST'])
def login():
    """
    Process login request
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: starting: {me}')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: getpass.getuser() returns: {getpass.getuser()}')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: os.geteuid() returns: {os.geteuid() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: os.getuid() returns: {os.getuid() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: os.getpid() returns: {os.getpid() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: os.getppid() returns: {os.getppid() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: threading.get_ident() returns: {threading.get_ident() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: os.getcwd() returns: {os.getcwd() }')    # DEBUG - remove when finished
    debug_now = datetime.datetime.now()   # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    ls_output = str(glob.glob("*"))         # DEBUG - remove when finished
    flash(f'{debug_now}: file in current directory: {ls_output}')    # DEBUG - remove when finished
    try:    # DEBUG - remove when finished
        Path("/var/www/html/etc/RMME.foo3").touch(mode=0o664, exist_ok=True) # DEBUG - remove when finished
        flash("touched /var/www/html/etc/RMME.foo3") # DEBUG - remove when finished
    # DEBUG - remove when finished
    except OSError as exception:    # DEBUG - remove when finished
        # pylint: disable-next=line-too-long    # DEBUG - remove when finished
        flash("ERROR: in " + me + ": failed touch (mode=0o664, exist_ok=True): " + "/var/www/html/etc/RMME.foo3" + \
                      " exception: " + str(exception))   # DEBUG - remove when finished

    # case: process / POST
    #
    if request.method == 'POST':
        debug_now = datetime.datetime.now()  # DEBUG - remove when finished
        # pylint: disable-next=line-too-long    # DEBUG - remove when finished
        flash(f'{debug_now}: request.method: POST: {me}')    # DEBUG - remove when finished
        form_dict = request.form.to_dict()
        username = form_dict.get('username')
        debug_now = datetime.datetime.now()  # DEBUG - remove when finished
        # pylint: disable-next=line-too-long    # DEBUG - remove when finished
        flash(f'{debug_now}: username: {username}: {me}')    # DEBUG - remove when finished

        # If the user is allowed to login
        #
        user = User(username)
        if user.id:  # DEBUG - remove when finished
            debug_now = datetime.datetime.now()  # DEBUG - remove when finished
            # pylint: disable-next=line-too-long    # DEBUG - remove when finished
            flash(f'{debug_now}: have user.id: {me}')    # DEBUG - remove when finished
            if user_allowed_to_login(user.user_dict):  # DEBUG - remove when finished
                debug_now = datetime.datetime.now()  # DEBUG - remove when finished
                # pylint: disable-next=line-too-long    # DEBUG - remove when finished
                flash(f'{debug_now}: allowed to login: username: {username}: {me}')    # DEBUG - remove when finished
            else:  # DEBUG - remove when finished
                debug_now = datetime.datetime.now()  # DEBUG - remove when finished
                # pylint: disable-next=line-too-long    # DEBUG - remove when finished
                flash(f'{debug_now}: NOT allowed to login: username: {username}: {me}')    # DEBUG - remove when finished
                debug_now = datetime.datetime.now()  # DEBUG - remove when finished
                # pylint: disable-next=line-too-long    # DEBUG - remove when finished
                flash(f'{debug_now}: NOT allowed to login: last errormsg: <<{return_last_errmsg()}>>')
        else:  # DEBUG - remove when finished
            debug_now = datetime.datetime.now()  # DEBUG - remove when finished
            # pylint: disable-next=line-too-long    # DEBUG - remove when finished
            flash(f'{debug_now}: have NO user.id: {me}')    # DEBUG - remove when finished
            debug_now = datetime.datetime.now()  # DEBUG - remove when finished
            # pylint: disable-next=line-too-long    # DEBUG - remove when finished
            flash(f'{debug_now}: have NO user.id: last errormsg: <<{return_last_errmsg()}>>')
        if user.id and user_allowed_to_login(user.user_dict):

            # validate password
            #
            debug_now = datetime.datetime.now()  # DEBUG - remove when finished
            # pylint: disable-next=line-too-long    # DEBUG - remove when finished
            flash(f'{debug_now}: have user.id, allowed to login: username: {username}: {me}')    # DEBUG - remove when finished
            if verify_hashed_password(form_dict.get('password'),
                                      user.user_dict['pwhash']):
                user.authenticated = True
                flask_login.login_user(user)
            else:
                flash("invalid password")
                return render_template('login.html')

            # get the JSON slots for the user and verify we have slots
            #
            slots = initialize_user_tree(username)
            if not slots:
                flash("ERROR: in: " + me + ": initialize_user_tree() failed: <<" + \
                      return_last_errmsg() + ">>")
                flask_login.logout_user()
                return redirect(url_for('login'))

            # case: user is required to change password
            #
            if must_change_password(user.user_dict):
                flash("User is required to change their password")
                return redirect(url_for('passwd'))

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
            flash("The IOCCC is not open")
            return render_template('not-open.html',
                                   flask_login = flask_login,
                                   username = username,
                                   etable = slots)

    # case: process / GET
    #
    debug_now = datetime.datetime.now()  # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: request.method: GET: {me}')    # DEBUG - remove when finished
    return render_template('login.html')


# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
#
@application.route('/submit', methods = ['GET', 'POST'])
@flask_login.login_required
def submit():
    """
    Access the IOCCC Submission Page - Upload a file to a user's slot
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name
    debug_now = datetime.datetime.now()  # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: starting: {me}')    # DEBUG - remove when finished

    # get username
    #
    if not current_user.id:
        flash("ERROR: Login required")
        flask_login.logout_user()
        return redirect(url_for('login'))
    username = current_user.id
    # paranoia
    if not username:
        flash("ERROR: Login required")
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

    # case: user is required to change password
    #
    if must_change_password(current_user.user_dict):
        flash("User is required to change their password")
        return redirect(url_for('passwd'))

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
@application.route('/update', methods=["POST"])
@flask_login.login_required
def upload():
    """
    Upload slot file
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name
    debug_now = datetime.datetime.now()  # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: starting: {me}')    # DEBUG - remove when finished

    # get username
    #
    if not current_user.id:
        flash("ERROR: Login required")
        return redirect(url_for('login'))
    username = current_user.id
    # paranoia
    if not username:
        flash("ERROR: Login required")
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

    # case: user is required to change password
    #
    if must_change_password(current_user.user_dict):
        flash("User is required to change their password")
        return redirect(url_for('passwd'))

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


@application.route('/logout')
def logout():
    """
    Logout.
    """
    flask_login.logout_user()
    return redirect(url_for('login'))


# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-statements
#
@application.route('/passwd', methods = ['GET', 'POST'])
def passwd():
    """
    Change user password
    """

    # setup
    #
    me = inspect.currentframe().f_code.co_name
    debug_now = datetime.datetime.now()  # DEBUG - remove when finished
    # pylint: disable-next=line-too-long    # DEBUG - remove when finished
    flash(f'{debug_now}: starting: {me}')    # DEBUG - remove when finished

    # get username
    #
    if not current_user.id:
        flash("ERROR: Login required")
        return redirect(url_for('login'))
    username = current_user.id
    # paranoia
    if not username:
        flash("ERROR: Login required")
        return redirect(url_for('login'))

    # get the JSON for all slots for the user
    #
    slots = get_all_json_slots(username)
    if not slots:
        flash("ERROR: in: " + me + ": get_all_json_slots() failed: <<" + \
              return_last_errmsg() + ">>")
        return redirect(url_for('login'))

    # case: process /passwd POST
    #
    if request.method == 'POST':
        form_dict = request.form.to_dict()

        # If the user is allowed to login
        #
        user = User(username)
        if user.id:

            # get username
            #
            if not current_user.id:
                flash("ERROR: Login required")
                return redirect(url_for('login'))
            # paranoia
            if not username:
                flash("ERROR: Login required")
                return redirect(url_for('login'))

            # get form parameters
            #
            old_password = form_dict.get('old_password')
            if not old_password:
                flash("ERROR: You must enter your current password")
                return redirect(url_for('login'))
            new_password = form_dict.get('new_password')
            if not new_password:
                flash("ERROR: You must enter a new password")
                return redirect(url_for('login'))
            reenter_new_password = form_dict.get('reenter_new_password')
            if not reenter_new_password:
                flash("ERROR: You must re-enter the new password")
                return redirect(url_for('login'))

            # verify new and reentered passwords match
            #
            if new_password != reenter_new_password:
                flash("ERROR: New Password and Reentered Password are not the same")
                return redirect(url_for('passwd'))

            # disallow old and new passwords being substrings of each other
            #
            if new_password == old_password:
                flash("ERROR: New password cannot be the same as your current password")
                return redirect(url_for('passwd'))
            if new_password in old_password:
                flash("ERROR: New password must not contain your current password")
                return redirect(url_for('passwd'))
            if old_password in new_password:
                flash("ERROR: Your current password cannot contain your new password")
                return redirect(url_for('passwd'))

            # validate new password
            #
            if not is_proper_password(new_password):
                flash("ERROR: New Password is not a valid password")
                flash(return_last_errmsg())
                return redirect(url_for('passwd'))

            # change user password
            #
            # NOTE: This will also validate the old password
            #
            if not update_password(username, old_password, new_password):
                flash("ERROR: Password not changed")
                flash(return_last_errmsg())
                return redirect(url_for('passwd'))

            # user password change successful
            #
            flash("Password successfully changed")
            return redirect(url_for('logout'))

    # case: process /passwd GET
    #
    pw_change_by = current_user.user_dict['pw_change_by']
    return render_template('passwd.html',
                           flask_login = flask_login,
                           username = username,
                           pw_change_by = pw_change_by,
                           min_length = str(MIN_PASSWORD_LENGTH),
                           max_length = str(MAX_PASSWORD_LENGTH))
#
# pylint: enable=too-many-branches
# pylint: enable=too-many-return-statements
# pylint: enable=too-many-statements


# Run the application on a given port
#
if __name__ == '__main__':

    # setup
    #
    program = os.path.basename(__file__)

    # parse args
    #
    parser = argparse.ArgumentParser(
                description="IOCCC submit server tool",
                epilog=f'{program} version: {VERSION}')
    parser.add_argument('-t', '--topdir',
                        help="application directory path",
                        metavar='appdir',
                        nargs=1)
    args = parser.parse_args()

    # -t topdir - set the path to the top level application direcory
    #
    if args.topdir:
        if not change_startup_appdir(args.topdir[0]):
            print("ERROR: change_startup_appdir error: <<" + return_last_errmsg() + ">>")
            sys.exit(3)

# launch the application if we are not inside uwsgi.
#

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=TCP_PORT)
