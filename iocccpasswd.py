import json
import argparse
from os import listdir,remove, rmdir
from werkzeug.security import generate_password_hash
from passwordgenerator import pwgenerator

passwdfile='iocccpasswd'
ioccc_dir="/app"

def readpwfile(failonnotexist=True):
    try:
        with open(passwdfile,"r",encoding="utf-8") as fp:
            passjson=json.load(fp)
    except FileNotFoundError:
        if failonnotexist:
            print("file not found")
            exit(-1)
        return None
    except PermissionError:
        print("Permission Denied.")
        exit(-1)
    return passjson

def writepwfile(pw_json):
    try:
        with open(passwdfile,"w",encoding="utf-8") as fp:
            fp.write(json.dumps(pw_json))
            fp.close()
    except FileNotFoundError:
        print("file not found")
        exit(-1)
    except PermissionError:
        print("Permission Denied.")
        exit(-1)

    return True

def deluser(username,ioccc_dir):
    user_dir=ioccc_dir + "/users/" + username
    json=readpwfile(False)
    if not json:
        return None
    if username in json:
        del json[username]
        try:
            userfiles = listdir(user_dir)
        except OSError as e:
            userfiles= None
        if userfiles:
            for userfile in userfiles:
                try:
                    remove(user_dir + "/" + userfile)
                except OSError as e:
                    print("Unable to remove files: " + str(e))
                    return None
            try:
                rmdir(user_dir)
            except OSError as e:
                print("Unable to remove user dir: " + str(e))
        return(writepwfile(json))
    print(username + " not in passwd file")
    return None

def adduser(user):
    json=readpwfile(False)
    if not json:
        json={}
        if not writepwfile(json):
            print("failed to create passwd file")
            return None
    if user in json:
        print(user + " already in passwd file")
        return None
    pw=pwgenerator.generate()
    json[user]=generate_password_hash(pw)
    writepwfile(json)
    return user,pw

def main():
    parser=argparse.ArgumentParser(description="manage ioccc passwds")
    parser.add_argument('-a','--add',help="Add a user", nargs='+')
    parser.add_argument('-d','--delete',help="Delete a user", nargs='+')
    parser.add_argument('-p','--pwdfile',help="the file to access",nargs=1)
    args=parser.parse_args()

    if args.pwdfile:
        passwdfile=args.pwdfile[0]

    if args.add:
        for add in args.add:
            ret=adduser(add)
            if ret:
                (user,pw) = ret
                print(f"user: {user} password: {pw}")

    if args.delete:
        for remove in args.delete:
            deluser(remove,ioccc_dir)

    return

if __name__ == '__main__':
    main()
