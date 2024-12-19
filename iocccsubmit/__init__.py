#!/usr/bin/env python3
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


# import ioccc_common functions
#
# Sort the import list with: sort -d -u
#
from .ioccc_common import \
    ADM_FILE, \
    ADM_FILE_RELATIVE_PATH, \
    APPDIR, \
    DATETIME_FORMAT, \
    DEFAULT_GRACE_PERIOD, \
    DEFAULT_JSON_STATE_TEMPLATE, \
    EMPTY_JSON_SLOT_TEMPLATE, \
    HOST_NAME, \
    INIT_PW_FILE, \
    INIT_PW_FILE_RELATIVE_PATH, \
    INIT_STATE_FILE, \
    INIT_STATE_FILE_RELATIVE_PATH, \
    LOCK_TIMEOUT, \
    MAX_PASSWORD_LENGTH, \
    MAX_SUBMIT_SLOT, \
    MAX_TARBALL_LEN, \
    MIN_PASSWORD_LENGTH, \
    NO_COMMENT_VALUE, \
    PASSWORD_VERSION_VALUE, \
    POSIX_SAFE_RE, \
    PW_FILE, \
    PW_FILE_RELATIVE_PATH, \
    PW_LOCK, \
    PW_LOCK_RELATIVE_PATH, \
    PWNED_PW_TREE, \
    PW_WORDS, \
    PW_WORDS_RELATIVE_PATH, \
    SECRET_FILE, \
    SECRET_FILE_RELATIVE_PATH, \
    SHA1_HEXLEN, \
    SLOT_VERSION_VALUE, \
    STARTUP_CWD, \
    STATE_FILE, \
    STATE_FILE_LOCK, \
    STATE_FILE_LOCK_RELATIVE_PATH, \
    STATE_FILE_RELATIVE_PATH, \
    STATE_VERSION_VALUE, \
    TCP_PORT, \
    USERS_DIR, \
    USERS_DIR_RELATIVE_PATH, \
    VERSION_IOCCC_COMMON, \
    change_startup_appdir, \
    contest_is_open, \
    delete_username, \
    generate_password, \
    get_all_json_slots, \
    get_json_slot, \
    hash_password, \
    initialize_user_tree, \
    ioccc_file_lock, \
    ioccc_file_unlock, \
    is_proper_password, \
    is_pw_pwned, \
    load_pwfile, \
    lock_slot, \
    lookup_username, \
    must_change_password, \
    read_json_file, \
    read_state, \
    replace_pwfile, \
    return_last_errmsg, \
    return_secret, \
    return_slot_dir_path, \
    return_slot_json_filename, \
    return_user_dir_path, \
    unlock_slot, \
    update_password, \
    update_slot, \
    update_slot_status, \
    update_state, \
    update_username, \
    user_allowed_to_login, \
    username_login_allowed, \
    validate_user_dict, \
    verify_hashed_password, \
    verify_user_password, \
    write_slot_json


# final imports
#
from .ioccc import application
