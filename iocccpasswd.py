#!/usr/bin/env python3
"""
Functions to implement adding and deleting of IOCCC contestants.
"""

import json
import argparse
from os import listdir,remove, rmdir
from werkzeug.security import generate_password_hash
from passwordgenerator import pwgenerator

PWD_FILE='etc/iocccpasswd'
IOCCC_DIR="/app"

def readpwfile(pwfile,failonnotexist=True):
    """
    read the password file.  return json.
    """
    try:
        with open(pwfile,"r",encoding="utf-8") as pw_fp:
            passjson=json.load(pw_fp)
    except FileNotFoundError:
        if failonnotexist:
            print("file not found")
            exit(-1)
        return None
    except PermissionError:
        print("Permission Denied.")
        exit(-1)
    return passjson

def writepwfile(pwfile,pw_json):
    """
    Write out passwd file.
    """
    try:
        with open(pwfile,"w",encoding="utf-8") as pw_fp:
            pw_fp.write(json.dumps(pw_json, ensure_ascii=True, sort_keys=True, indent=4))
            pw_fp.write('\n')
            pw_fp.close()
    except FileNotFoundError:
        print("file not found")
        exit(-1)
    except PermissionError:
        print("Permission Denied.")
        exit(-1)

    return True

def deluser(username,ioccc_dir,pwfile):
    """
    delete a user.
    """
    user_dir=ioccc_dir + "/users/" + username
    pw_json=readpwfile(pwfile,False)
    if not pw_json:
        return None
    if username in pw_json:
        del pw_json[username]
        try:
            userfiles = listdir(user_dir)
        except OSError:
            userfiles= None
        if userfiles:
            for userfile in userfiles:
                try:
                    remove(user_dir + "/" + userfile)
                except OSError as e_code:
                    print("Unable to remove files: " + str(e_code))
                    return False
            try:
                rmdir(user_dir)
            except OSError as e_code:
                print("Unable to remove user dir: " + str(e_code))
        return writepwfile(pwfile,pw_json)
    print(username + " not in passwd file")
    return False

def adduser(user,pwfile):
    """
    Add a user.
    """
    pw_json=readpwfile(pwfile,False)
    if not pw_json:
        pw_json={}
        if not writepwfile(pwfile,pw_json):
            print("failed to create passwd file")
            return None
    if user in pw_json:
        print(user + " already in passwd file")
        return None
    pword=pwgenerator.generate()
    pw_json[user]=generate_password_hash(pword)
    writepwfile(pwfile,pw_json)
    return user,pword

def main():
    """
    Main routine when run as a program.
    """
    parser=argparse.ArgumentParser(description="manage ioccc passwds")
    parser.add_argument('-a','--add',help="Add a user", nargs='+')
    parser.add_argument('-d','--delete',help="Delete a user", nargs='+')
    parser.add_argument('-p','--pwdfile',help="the file to access",nargs=1)
    args=parser.parse_args()

    if args.pwdfile:
        passwdfile=args.pwdfile[0]
    else:
        passwdfile=PWD_FILE
    if args.add:
        for add in args.add:
            ret=adduser(add,passwdfile)
            if ret:
                (user,pword) = ret
                print(f"user: {user} password: {pword}")

    if args.delete:
        for rem_user in args.delete:
            deluser(rem_user,IOCCC_DIR,passwdfile)


if __name__ == '__main__':
    main()
