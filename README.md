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

Each of the examples in this document assume that you have executed the following:

```sh
rm -rf venv __pycache__ && python3 -m venv venv
. ./venv/bin/activate
pip install --upgrade pip
python3 -m pip install -r ./etc/requirements.txt
```

**NOTE**: if you see something like under macOS (such as under macOS Sequoia 15.1.1):

```
WARNING: You are using pip version 21.2.4; however, version 24.3.1 is available.
You should consider upgrading via the '/Library/Developer/CommandLineTools/usr/bin/python3 -m pip install --upgrade pip' command.
```

you could try running the command, but if you see something like (this was
also observed in macOS 15.1):

```
Defaulting to user installation because normal site-packages is not writeable
Requirement already satisfied: pip in /Users/cody/Library/Python/3.9/lib/python/site-packages (24.3.1)
```

it should be okay (**NOTE**: do **NOT** run the command as root!).


# bin/ioccc.py - the submit tool

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

To run the **IOCCC submit tool** server:

```sh
./bin/ioccc.py
```

**NOTE**: If the `./bin/ioccc.py` is not executable, try: `python3 ./bin/ioccc.py`.

**NOTE**: at this time (Sat 07 Dec 2024 14:12:05 UTC), you will see a notice in
the output, with the warning in red:

```sh
$ ./bin/ioccc.py
 * Serving Flask app 'ioccc'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8191
 * Running on http://192.168.1.71:8191
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 920-182-908

```

.. where the last blank line is not a command line but rather it being in the
background (of course, you you could put it in the background with
`./bin/ioccc.py &`, if you wanted).

**NOTE**: in macOS you might see an alert asking you if you wish to allow the
program to bind and listen to the addresses and port. If you wish to proceed you
will need to allow it.

While `bin/ioccc.py` is running, open a browser at (this works under macOS):

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

At the console, you should see something like:

```
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.css HTTP/1.1" 304 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.js HTTP/1.1" 304 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.png HTTP/1.1" 304 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.css HTTP/1.1" 304 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.js HTTP/1.1" 304 -
127.0.0.1 - - [07/Dec/2024 06:22:47] "GET /static/ioccc.png HTTP/1.1" 304 -
```

To deactivate the above python environment from the submit server top level
directory, make sure the server is no longer running and then run:

```sh
deactivate
rm -rf __pycache__ venv
```


# bin/pychk.sh - use of pylint

**NOTE**: You must [setup python the environment](#setup) **BEFORE** running any of the command(s) below:

```sh
./bin/pychk.sh
```

FYI: Under macOS we installed `pylint` via `pipx`:

```sh
sudo pipx --global install pylint
```

In case you don't have `pipx`, we installed `pipx` via
[Homebrew](https://brew.sh) on macOS:

```sh
brew install pipx
```


# bin/ioccc_passwd.py - IOCCC user management

The usage message of the `./bin/ioccc_passwd.py` is as follows:

```
usage: ioccc_passwd.py [-h] [-t appdir] [-a USER] [-u USER] [-d USER] [-p PW]
                       [-c] [-g SECS] [-n] [-A] [-U]

Manage IOCCC submit server password file and state file

options:
  -h, --help           show this help message and exit
  -t, --topdir appdir  app directory path
  -a, --add USER       add a new user
  -u, --update USER    update a user or add if not a user
  -d, --delete USER    delete an exist user
  -p, --password PW    specify the password (def: generate random password)
  -c, --change         force a password change at next login
  -g, --grace SECS     grace seconds to change the password (def: 259200)
  -n, --nologin        disable login (def: login not explicitly disabled)
  -A, --admin          user is an admin (def: not an admin)
  -U, --UUID           generate a new UUID username and password

ioccc_passwd.py version: 1.6 2024-12-04
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

The starting and ending dates of the IOCCC control when `./bin/ioccc.py` allows
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

ioccc_date.py version: 1.1 2024-12-04
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

set_slot_status.py version: 1.1 2024-12-04
```


### Deprecated docker use

**NOTE**: The use of docker was initially used for testing purposes.
      At one time there was consideration for deploying via a
      docker container.  We have chosen instead to deploy this
      on a server under Apache.

**NOTE**: This use of docker is **NOT** supported ‼️

Given that docker use has been deprecated, consider
the following of historic and unsupported interest
using a macOS host with the docker app installed:

```sh
# launch/run the docker app

# to remove all stopped containers
#
docker container prune -f

# remove old ioccc-submit image
#
docker image rm ioccc-submit

# build new ioccc-submit image
#
docker build -t ioccc-submit:latest .

# update scout-cli and review results
#
curl -sSfL https://raw.githubusercontent.com/docker/scout-cli/main/install.sh | sh -s --

# optional: scan contaiers for issues
#
docker scout quickview

# optional: detail issue scan of ioccc-submit
#
docker scout cves local://ioccc-submit:latest

# run the ioccc-submit:latest in the backgroud
#
# NOTE: To run in foreground with diagnostic to the terminal,
#       execute the following instead of "docker run -it -d ...".
#
#    docker run -p 8191:8191 ioccc-submit:latest
#
docker run -it -d -p 8191:8191 ioccc-submit:latest
```

When the `docker` command is running, launch a browser and visit
the local submit tool URL: [http://127.0.0.1:8191](http://127.0.0.1:8191).

Login using a username and password referenced in the `NOTES/INFO/pw.txt` file.

To build and run as a single command under a python activated environment:

```sh
docker container prune -f ; \
docker image rm ioccc-submit ; \
docker build -t ioccc-submit:latest . && docker run -p 8191:8191 ioccc-submit:latest
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
