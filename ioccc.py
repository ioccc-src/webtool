import re
import json
import hashlib
from os import makedirs,umask
from flask import Flask,Response,url_for,render_template,flash,redirect,request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from iocccpasswd import adduser,deluser

application = Flask(__name__)
# BTW: max uncompressed tar 4e6 bytes
#      so we set the max bip2 compressed tar is the larest prime < 4e6 bytes
application.config['MAX_CONTENT_LENGTH']=3999971
# XXX - flask requires application.secret_key to be set, change before delpoyment
application.secret_key="CHANGE_THIS_STRING_DURING_DEPLOYMENT"
auth = HTTPBasicAuth()

with application.test_request_context('/'):
    url_for('static',filename='style.css')
    url_for('static',filename='script.js')
    url_for('static',filename='ioccc.png')

# ioccc_dir="/var/lib/ioccc"
ioccc_dir="/app"
ioccc_root="/"
pwfile= ioccc_dir + "/iocccpasswd"
statefile= ioccc_dir + "/state"
admfile = ioccc_dir + "/admins"



def write_entries(entry_file,entries):
    try:
        entries_fp=open(entry_file,mode="w",encoding="utf-8")
        entries_fp.write(json.dumps(entries))
        entries_fp.close()
    except IOError as e:
        print(str(e))
        return None
    return True

def get_entries(user):
    user_dir=ioccc_dir + "/users/" + user
    entries_file=user_dir + "/entries.json"
    umask(0o022)
    try:
        makedirs(user_dir,exist_ok=True)
    except OSError as e:
        print(str(e))
        return None
    try:
        entries_fp=open(entries_file,"r",encoding="utf-8")
        entries=json.load(entries_fp)
    except IOError:
        entries = {
            0: "No entry"
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
    entries=get_entries(username)
    user_dir=ioccc_dir + "/users/" + username
    entries_file=user_dir + "/entries.json"
    if not entries:
        return None
    try:
        file_fp=open(filename,"rb")
    except IOError as e:
        print(str(e))
        return None
    result=hashlib.md5(file_fp.read())
    entries[entry_no]=result.hexdigest()
    print("entry_no = " + entry_no + " hash = " + entries[entry_no])
    if not write_entries(entries_file,entries):
        return None
    return True


def readpwfile(pwfile):
    try:
        with open(pwfile,'r',encoding="utf-8") as pw:
            return json.load(pw)
    except FileNotFoundError:
        return []

def setcontest(state):
    try:
        with open(statefile,'w',encoding='utf-8') as sf:
            sf.write(f' [ "{state}" ]')
            sf.close()
    except e as OSError:
        print("couldn't write statefile: " + str(e))

@auth.verify_password
def verify_password(username, password):
    users = readpwfile(pwfile)
    if username in users and \
            check_password_hash(users.get(username), password):
        return username


@application.route('/',methods=["GET"])
@auth.login_required
def index():
    username=auth.current_user()
    entries=get_entries(username)
    if not entries:
        return Response(response="Configuration error",status=400)
    return render_template("index.html",user=username,etable=entries)

@application.route('/admin',methods=["GET"])
@auth.login_required
def admin():
    users = readpwfile(pwfile)
    username=auth.current_user()
    admins=readpwfile(admfile)
    if not username in admins:
        return Response(response="Permission denied.",status=404)
    if not users:
        return Response(response="Configuration error",status=400)
    return render_template("admin.html",contestants=users,user=username)

@application.route('/update',methods=["POST"])
@auth.login_required
def upload():
    username=auth.current_user()
    entries=get_entries(username)
    user_dir=ioccc_dir + "/users/" + username

    if not 'entry_no' in request.form:
        flash("No entry selected")
        return redirect(ioccc_root)
    entry_no=request.form['entry_no']
    entryfile= user_dir + "/" + "entry-" + entry_no
    if 'file' not in request.files:
        flash('No file part')
        return redirect(ioccc_root)
    file=request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(ioccc_root)
    file.save(entryfile)
    if not update_entries(username,entry_no,entryfile):
        flash('Failure updating entries')
    return redirect(ioccc_root)

@application.route('/admin-update',methods=["POST"])
@auth.login_required
def admin_update():
    users=readpwfile(pwfile)
    username=auth.current_user()
    admins=readpwfile(admfile)
    if not username in admins:
        return Response(response="Permission denied.",status=404)
    if "openclose" in request.form:
        if request.form['openclose'] == "open":
            setcontest("open")
        elif request.form['openclose'] == "closed":
            setcontest("closed")
    if "newuser" in request.form:
        newuser=request.form['newuser']
        if not newuser == "":
            if not re.match("[a-zA-Z0-9.@_\-+]+",newuser):
                flash('bad username for new user.')
                return redirect("/admin")
            if newuser in users:
                flash('username already in use.')
                return redirect('/admin')
            ret=adduser(newuser)
            if ret:
                (user,pw) = ret
                flash(f"user: {user} password: {pw}")
    for key in request.form:
        if request.form[key] in admins:
            flash(request.form[key] + ' is an admin and cannot be deleted.')
            return redirect('/admin')
        if re.match('^contest.*',key):
            deluser(request.form[key],ioccc_dir)
    return redirect("/admin")


if __name__ == '__main__':
    application.run(host='0.0.0.0')
