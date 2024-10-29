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
import hashlib
import uuid
import inspect


# import from modules
#
from typing import Dict, Optional


# 3rd party imports
#
from flask import Flask, render_template, request, redirect, url_for
import flask_login


# import the ioccc python utility code
#
# NOTE: This in turn imports a lot of other stuff, and sets global constants.
#
from ioccc_common import *


# Submit tool server version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION = "0.6 2024-10-25"


# Configure the app
#
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_TARBALL_LEN
app.config['FLASH_APP'] = "ioccc-submit-tool"
app.config['FLASK_DEBUG'] = True
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
    # FALLBACK: generate on the fly for testing
    #
    # IMPORTANT: This will not work for production as different
    #            instances of this app will have different secrets.
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


# Our mock database.
#
users = {'user': {'password': 'test'}}


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
    if request.method == 'POST':
        form_dict = request.form.to_dict()
        username = form_dict.get('username')

        user = User(username)
        if user.id:
            if verify_hashed_password(form_dict.get('password'),
                                    user.user_dict['pwhash']):
                user.authenticated  = True
                flask_login.login_user(user)
                return redirect('/page')

    return render_template('login.html')


@app.route('/page', methods=['GET','POST'])
@flask_login.login_required
def page():
    """
    Access User page
    """
    if request.method == 'POST':
        form_dict = request.form.to_dict()
        print('formDcit::', form_dict)
        if form_dict.get('page'):
            return redirect(url_for('page'))
        if form_dict.get('protected_page_1'):
            return redirect(url_for('protected_page_1'))
        if form_dict.get('protected_page_2'):
            return redirect(url_for('protected_page_2'))
        if form_dict.get('logout'):
            return redirect(url_for('logout'))
        if form_dict.get('login'):
            return redirect(url_for('login'))
    return render_template('page.html')


@app.route('/protected_page_1', methods = ['GET', 'POST'])
@flask_login.login_required
def protected_page_1():
    """
    Access the protected page #1.
    """
    page_name = 'Protected page 1'
    other_protected_page = 'Protected page 2'
    if request.method == 'POST':
        form_dict = request.form.to_dict()

        if form_dict.get('page'):
            return redirect(url_for('page'))
        if form_dict.get('protected_page_1'):
            return redirect(url_for('protected_page_1'))
        if form_dict.get('protected_page_2'):
            return redirect(url_for('protected_page_2'))
        if form_dict.get('logout'):
            return redirect(url_for('logout'))

    return render_template('protected_page.html', flask_login = flask_login,
        page_name = page_name, other_protected_page = other_protected_page)


@app.route('/protected_page_2', methods = ['GET', 'POST'])
@flask_login.login_required
def protected_page_2():
    """
    Access the protected page 2.
    """
    page_name = 'Protected __page__ 2'
    other_protected_page = 'Protected page 1'
    if request.method == 'POST':
        form_dict = request.form.to_dict()
        if form_dict.get('page'):
            return redirect(url_for('page'))
        if form_dict.get('protected_page_1'):
            return redirect(url_for('protected_page_1'))
        if form_dict.get('protected_page_2'):
            return redirect(url_for('protected_page_2'))
        if form_dict.get('logout'):
            return redirect(url_for('logout'))


    return render_template('protected_page.html', flask_login = flask_login,
        page_name = page_name, other_protected_page = other_protected_page)


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
