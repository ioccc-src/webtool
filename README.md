# IOCCC submit tool

This is the mechanism to upload submissions to an open
[International Obfuscated C Code Contest](https://www.ioccc.org/index.html)
(IOCCC).


# IMPORTANT NOTE

<div id="setup">
You **MUST setup the python environment** before you run any of the commands in test mode.
</div>

All of examples assume you have **cd-ed into the top directory**
where you cloned the [submit tool repo](https://github.com/ioccc-src/submit-tool).

First, make sure to clean out the cache and then build the python virtual environment:

```sh
make clobber all install
```

Now, in each tab/terminal window/console you need to do something (like running
the server and then in another tab/terminal window/console, creating a new user
and password), you should run the following:


```sh
source venv/bin/activate
```

**IMPORTANT**: all of the below examples in this document assume that you have
executed the above commands.

**NOTE**: if you see something like this, (this was observed in macOS Sequoia 15.2):

```
WARNING: You are using pip version 21.2.4; however, version 24.3.1 is available.
You should consider upgrading via the '/Library/Developer/CommandLineTools/usr/bin/python3 -m pip install --upgrade pip' command.
```

you could try running the command, but if you see something like (this was
also observed in macOS 15.2):

```
Defaulting to user installation because normal site-packages is not writeable
Requirement already satisfied: pip in /Users/cody/Library/Python/3.9/lib/python/site-packages (24.3.1)
```

it should be okay (**NOTE**: do **NOT** run the command as root!).

**NOTE**: to tell if the environment is activated, look for the text `(venv)`
before your prompt (the `PS1` variable).


# iocccsubmit/ioccc.py - the submit tool

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

To run the **IOCCC submit tool** server interactively on the command line:

```sh
./iocccsubmit/ioccc.py -l stdout -L info -i 127.0.0.1 -p 8191
```

**NOTE**: If the `./iocccsubmit/ioccc.py` is not executable, try: `python3 ./iocccsubmit/ioccc.py`.

The initial output will look something like (timestamps, text colour, and PIN will vary):

```sh
$ ./iocccsubmit/ioccc.py -l stdout -L info -i 127.0.0.1 -p 8191
 * Serving Flask app 'ioccc'
 * Debug mode: on
2024-12-20 22:41:54.863: werkzeug: INFO: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:8191
2024-12-20 22:41:54.864: werkzeug: INFO: Press CTRL+C to quit
2024-12-20 22:41:54.864: werkzeug: INFO:  * Restarting with stat
2024-12-20 22:41:55.054: werkzeug: WARNING:  * Debugger is active!
2024-12-20 22:41:55.060: werkzeug: INFO:  * Debugger PIN: 108-721-038
```

.. where the last blank line is not a command line but rather the server running.

**NOTE**: it does not at this time work putting it in the background (i.e.
`./iocccsubmit/ioccc.py &`).

**NOTE**: in macOS you might see an alert asking you if you wish to allow the
program to bind and listen to the addresses and port. If you wish to proceed you
will need to allow it.

While `iocccsubmit/ioccc.py` is running, open a browser at (this works under macOS):

```
open http://127.0.0.1:8191
```

.. or do whatever the equivalent on your system to enter this URL into a
browser, (alternatively you can copy and paste it into your browser):

```
http://127.0.0.1:8191
```

In your browser, it should look something like:

<img src="static/login-example.jpg"
 alt="IOCCC submit server index page"
 width=662 height=658>

At the console (where the server is running), you should see something like:

```
2024-12-20 22:48:53.589: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:48:53] "GET / HTTP/1.1" 200 -
2024-12-20 22:48:53.612: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:48:53] "GET /static/ioccc.css HTTP/1.1" 200 -
2024-12-20 22:48:53.613: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:48:53] "GET /static/ioccc.js HTTP/1.1" 200 -
2024-12-20 22:48:53.616: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:48:53] "GET /static/ioccc.png HTTP/1.1" 200 -
```

After logging in, should see something like:

```
2024-12-20 22:49:10.521: ioccc: INFO: login: success: username: -your-username-here-
2024-12-20 22:49:10.528: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:49:10] "POST / HTTP/1.1" 200 -
2024-12-20 22:49:10.536: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:49:10] "GET /static/ioccc.css HTTP/1.1" 304 -
2024-12-20 22:49:10.537: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:49:10] "GET /static/ioccc.js HTTP/1.1" 304 -
2024-12-20 22:49:10.537: werkzeug: INFO: 127.0.0.1 - - [20/Dec/2024 22:49:10] "GET /static/ioccc.png HTTP/1.1" 304 -
```

When needed, to deactivate the above python environment from the submit server
top level directory, make sure the server is no longer running and then execute:

```sh
deactivate
rm -rf __pycache__ venv
```


## iocccsubmit/ioccc.py - usage message

The usage message of the `./iocccsubmit/ioccc.py` is as follows:

```
usage: ioccc.py [-h] [-i ip] [-l logtype] [-L dbglvl] [-p port] [-t appdir]

IOCCC submit server tool

options:
  -h, --help           show this help message and exit
  -i, --ip ip          IP address to connect (def: 127.0.0.1)
  -l, --log logtype    log via: stdout stderr syslog none (def: syslog)
  -L, --level dbglvl   set log level: dbg debug info warn warning error crit critical (def: info)
  -p, --port port      open port (def: 8191)
  -t, --topdir appdir  application directory path: tree under appdir must be setup correctly

ioccc.py version: 2.1.1 2024-12-20
```

For command line interactive debugging try:

```sh
./iocccsubmit/ioccc.py -l stdout -L info -i 127.0.0.1 -p 8191
```

For more verbose interactive debugging:

```sh
./iocccsubmit/ioccc.py -l stdout -L debug -i 127.0.0.1 -p 8191
```

**NOTE**: An unknown `-l logtype` results in the default `-l syslog` being used.

**NOTE**: An unknown `-L dbglvl` results in the default `-L info` being used.

**NOTE**: When logging with syslog, the _local5_ facility is used.

**NOTE**: Use of `-t appdir` will likely fail unless you have the directory tree under `appdir` setup properly.


# bin/pychk.sh - use of pylint

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

```sh
./bin/pychk.sh
```

FYI: Under macOS we installed `pylint` via `pipx`:

```sh
sudo pipx --global install pylint
```

In case you don't have `pipx`, you can install [Homebrew](https://brew.sh) in
macOS and then install `pylint` by running:

```sh
brew install pipx
```


# bin/ioccc_passwd.py - IOCCC user management

The usage message of the `./bin/ioccc_passwd.py` is as follows:

```
usage: ioccc_passwd.py [-h] [-t appdir] [-a USER] [-u USER] [-d USER] [-p PW]
                       [-c] [-C] [-g SECS] [-n] [-A] [-U]

Manage IOCCC submit server password file and state file

options:
  -h, --help           show this help message and exit
  -t, --topdir appdir  app directory path
  -a, --add USER       add a new user
  -u, --update USER    update a user or add if not a user
  -d, --delete USER    delete an exist user
  -p, --password PW    specify the password (def: generate random password)
  -c, --change         force a password change at next login
  -C, --nochange       clear the requirement to change password
  -g, --grace SECS     grace seconds to change the password (def: 259200)
  -n, --nologin        disable login (def: login not explicitly disabled)
  -A, --admin          user is an admin (def: not an admin)
  -U, --UUID           generate a new UUID username and password

ioccc_passwd.py version: 2.1.0 2024-12-20
```



## Add a new user

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

An example in how to add a new user:

```sh
./bin/ioccc_passwd.py -a username
```

The command will output the password in plain-text.

One may add `-p password` to set the password, otherwise a random password is generated.


## Remove an old user

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

For example, to add a user called `username`:

```sh
./bin/ioccc_passwd.py -d username
```


## Add a random UUID user and require them to change their password

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

To generate a username with a random UUID, a temporary random password,
and a requirement to change that temporary password within the grace period:

```sh
./bin/ioccc_passwd.py -U -c
```

The tool will output the username and temporary random that has just been
added to the `etc/iocccpasswd.json` IOCCC password file.


# bin/ioccc_date.py - manage IOCCC open and close dates

The `bin/ioccc_date.py` tool is used to query or set the IOCCC
open and close dates.


## Set the staring and/or ending dates of the IOCCC

The starting and ending dates of the IOCCC control when `./iocccsubmit/ioccc.py` allows
for submission uploads.

The usage message of the `./bin/ioccc_date.py` is as follows:

```
usage: ioccc_date.py [-h] [-t appdir] [-s DateTime] [-S DateTime]

Manage IOCCC submit server password file and state file

options:
  -h, --help            show this help message and exit
  -t, --topdir appdir   app directory path
  -s, --start DateTime  set IOCCC start date in YYYY-MM-DD
                        HH:MM:SS.micros+hh:mm format
  -S, --stop DateTime   set IOCCC stop date in YYYY-MM-DD
                        HH:MM:SS.micros+hh:mm format

ioccc_date.py version: 2.0.0 2024-12-16
```

**NOTE**: When neither `-s DateTime` nor `-S DateTime` is given, then the current
IOCCC start and end values are printed.


## Set both the start and the end dates of the IOCCC

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

Example of setting an open and close date:


```sh
./bin/ioccc_date.py -s "2024-05-25 21:27:28.901234+00:00" -S "2024-10-28 00:47:00.000000-08:00"
```



# bin/set_slot_status.py - modify a slot comment

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

To set / change the status comment of a user's slot:

```sh
./bin/set_slot_status.py 12345678-1234-4321-abcd-1234567890ab 0 'new slot status'
```

The usage message of the `./bin/ioccc_date.py` is as follows:

```
usage: set_slot_status.py [-h] [-t appdir] username slot_num status

Manage IOCCC submit server password file and state file

positional arguments:
  username             IOCCC submit server username
  slot_num             slot number from 0 to 9
  status               slot status string

options:
  -h, --help           show this help message and exit
  -t, --topdir appdir  app directory path

set_slot_status.py version: 2.0.0 2024-12-16
```


# Python Developer Help Welcome

Python 🐍 is not the native language of the [IOCCC
judges](https://www.ioccc.org/judges.html).  As such, this code may fall well
short of what someone fluent in python would write.

We welcome python developers submitting pull requests to improve this code ‼️

All that we ask is that your code contributions:

- be well commented, or at least better commented than our code
- pass pylint 10/10 with a minimum of disable lines
- work as good, if not better than our code
- code contributed under the same [BSD 3-Clause License](https://github.com/ioccc-src/submit-tool/blob/master/LICENSE)


## Disclaimer

This code is based on code originally written by Eliot Lear (@elear) in late
2021\.  The [IOCCC judges](https://www.ioccc.org/judges.html) heavily modified
Eliot's code, so any fault you find should be blamed on them 😉 (that is, the
IOCCC Judges :-) ). As such, YOU should be WARNED that this code might NOT work,
or at least might not work for you.

The IOCCC plans to deploy an apache web server to allow IOCCC
registered contestants to submit their `mkiocccentry` compressed xz tarball(s)
that have been created by the [mkiocccentry
tool](https://github.com/ioccc-src/mkiocccentry).

The [IOCCC judges](https://www.ioccc.org/judges.html) plan to work on
this code prior to the next IOCCC.
