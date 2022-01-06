#!python
"""
Routines to implement IOCCC registration functions.
"""
import re
import json
import hashlib
from os import makedirs,umask
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from flask import Flask,Response,url_for,render_template,flash,redirect,request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from iocccpasswd import adduser,deluser

application = Flask(__name__)
# BTW: max uncompressed tar 4e6 bytes
#      so we set the max bip2 compressed tar is the larest prime < 4e6 bytes
application.config['MAX_CONTENT_LENGTH']=3999971
# XXX - flask requires application.secret_key to be set, change before delpoyment
application.secret_key="CHANGE_ME"
auth = HTTPBasicAuth()

with application.test_request_context('/'):
    url_for('static',filename='style.css')
    url_for('static',filename='script.js')
    url_for('static',filename='ioccc.png')

# ioccc_dir="/var/lib/ioccc"
IOCCC_DIR="/app"
IOCCC_ROOT="/"
PW_FILE= IOCCC_DIR + "/iocccpasswd"
STATE_FILE= IOCCC_DIR + "/state"
ADM_FILE = IOCCC_DIR + "/admins"


def write_entries(entry_file,entries):
    """
    Write out an index of entries for the user.
    """
    try:
        with open(entry_file,mode="w",encoding="utf-8") as entries_fp:
            entries_fp.write(json.dumps(entries))
            entries_fp.close()
    except IOError as excpt:
        print(str(excpt))
        return None
    return True

def get_entries(user):
    """
    read in the entry list for a given user.
    """
    user_dir=IOCCC_DIR + "/users/" + user
    entries_file=user_dir + "/entries.json"
    umask(0o022)
    try:
        makedirs(user_dir,exist_ok=True)
    except OSError as excpt:
        print(str(excpt))
        return None
    try:
        with open(entries_file,"r",encoding="utf-8") as entries_fp:
            entries=json.load(entries_fp)
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
        }
        if not write_entries(entries_file,entries):
            return None
    return entries

def update_entries(username,entry_no,filename):
    """
    Update a given entry for a given user.
    """
    entries=get_entries(username)
    user_dir=IOCCC_DIR + "/users/" + username
    entries_file=user_dir + "/entries.json"
    if not entries:
        return None
    try:
        with open(filename,"rb") as file_fp:
            result=hashlib.md5(file_fp.read())
    except IOError as excpt:
        print(str(excpt))
        return None
    entries[entry_no]=result.hexdigest()
    print("entry_no = " + entry_no + " hash = " + entries[entry_no])
    if not write_entries(entries_file,entries):
        return None
    return True


def readjfile(pwfile):
    """
    read a password (or really any JSON) file.
    """
    try:
        with open(pwfile,'r',encoding="utf-8") as pw_fp:
            return json.load(pw_fp)
    except FileNotFoundError:
        return []

def set_state(opdate,cldate):
    """
    Set contest dates.
    """
    try:
        with open(STATE_FILE,'w',encoding='utf-8') as sf_fp:
            sf_fp.write(f'{{ "opendate" : "{opdate}", "closedate" : "{cldate}" }}')
            sf_fp.close()
    except OSError as excpt:
        print("couldn't write STATE_FILE: " + str(excpt))

def check_state():
    """
    See if the contest is opened.
    """
    st_info=readjfile(STATE_FILE)
    if st_info:
        the_time=datetime.fromisoformat(st_info['opendate'])
        opdate=datetime(the_time.year,the_time.month,the_time.day,tzinfo=ZoneInfo("GMT"))
        the_time=datetime.fromisoformat(st_info['closedate'])
        cldate=datetime(the_time.year,the_time.month,the_time.day,tzinfo=ZoneInfo("GMT"))
    else:
        opdate=datetime(2019,1,1,tzinfo=ZoneInfo("GMT"))
        cldate=datetime(2025,12,31,tzinfo=ZoneInfo("GMT"))
    now=datetime.now(timezone.utc)
    return opdate,cldate,now

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

@application.route('/',methods=["GET"])
@auth.login_required
def index():
    """
    Basic User Interface.
    """
    username=auth.current_user()
    entries=get_entries(username)
    if not entries:
        return Response(response="Configuration error",status=400)
    opdate,cldate,now=check_state()
    if now < opdate or now > cldate:
        return render_template("closed.html")
    return render_template("index.html",user=username,etable=entries,date=str(cldate))

@application.route('/admin',methods=["GET"])
@auth.login_required
def admin():
    """
    Present administrative page.
    """
    users = readjfile(PW_FILE)
    username=auth.current_user()
    admins=readjfile(ADM_FILE)
    if not username in admins:
        return Response(response="Permission denied.",status=404)
    if not users:
        return Response(response="Configuration error",status=400)
    st_info=readjfile(STATE_FILE)
    if st_info:
        opdate=st_info['opendate']
        cldate=st_info['closedate']
    else:
        opdate=str(date.today())
        cldate=opdate
    return render_template("admin.html",contestants=users,user=username,
                           opdate=opdate,cldate=cldate)

@application.route('/update',methods=["POST"])
@auth.login_required
def upload():
    """
    Upload Entries
    """
    username=auth.current_user()
    user_dir=IOCCC_DIR + "/users/" + username

    opdate,cldate,now=check_state()
    if now < opdate or now > cldate:
        flash("Contest Closed.")
        return redirect(IOCCC_ROOT)
    if not 'entry_no' in request.form:
        flash("No entry selected")
        return redirect(IOCCC_ROOT)
    entry_no=request.form['entry_no']
    entryfile= user_dir + "/" + "entry-" + entry_no
    if 'file' not in request.files:
        flash('No file part')
        return redirect(IOCCC_ROOT)
    file=request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(IOCCC_ROOT)
    file.save(entryfile)
    if not update_entries(username,entry_no,entryfile):
        flash('Failure updating entries')
    return redirect(IOCCC_ROOT)

@application.route('/admin-update',methods=["POST"])
@auth.login_required
def admin_update():
    """
    Backend admin update process.
    """
    users=readjfile(PW_FILE)
    username=auth.current_user()
    admins=readjfile(ADM_FILE)
    if not username in admins:
        return Response(response="Permission denied.",status=404)
    st_info=readjfile(STATE_FILE)
    if st_info:
        opdate=st_info['opendate']
        cldate=st_info['closedate']
    else:
        opdate=str(date.today())
        cldate=opdate
    if "opendate" in request.form and not request.form['opendate'] == '':
        opdate=request.form['opendate']
    if "closedate" in request.form and not request.form['closedate'] == '':
        cldate=request.form['closedate']
    set_state(opdate,cldate)
    if "newuser" in request.form:
        newuser=request.form['newuser']
        if not newuser == "":
            if not re.match("[a-zA-Z0-9.@_+-]+",newuser):
                flash('bad username for new user.')
                return redirect("/admin")
            if newuser in users:
                flash('username already in use.')
                return redirect('/admin')
            ret=adduser(newuser,PW_FILE)
            if ret:
                (user,password) = ret
                flash(f"user: {user} password: {password}")
    for key in request.form:
        if request.form[key] in admins:
            flash(request.form[key] + ' is an admin and cannot be deleted.')
            return redirect('/admin')
        if re.match('^contest.*',key):
            deluser(request.form[key],IOCCC_DIR,PW_FILE)
    return redirect("/admin")

@application.route('/register',methods=["GET"])
def register():
    opdate,cldate,now=check_state()
    return render_template("register.html",date=cldate)

@application.route('/reg',methods=["POST"])
def reg():
    if not ("firstname" in request.form and "lastname" in request.form 
            and "email" in request.form and "rules" in request.form ):
        flash("Form not complete")
        return(redirect(ioccc_root + "/register"))
    email=request.form['email']
    if (len(request.form['firstname']) < 1 or len(request.form['lastname']) < 1
        or not re.match("[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}$",email)):
        flash("Form not properly complete.")
        return(redirect(ioccc_root + "/register"))
    if (not request.form['rules']):
        flash("Rules not agreed.")
        return(redirect(ioccc_root + "/register"))
    return render_template("re-confirm.html")

if __name__ == '__main__':
    application.run(host='0.0.0.0')

