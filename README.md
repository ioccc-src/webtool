# IOCCC submit tool

This is the mechanism to upload submissions to an open
[International Obfuscated C Code Contest](https://www.ioccc.org/index.html) (IOCCC)


# Python Developer Help Wanted

Python 🐍 is not the native language of the [IOCCC judges](https://www.ioccc.org/judges.html).
As such, this code may fall well short of what someone fluent in python would write.

We welcome python developers submitting pull requests to improve this code ‼️

All that we ask is that your code contributions:

- be well commented, or at least better commented than our code
- pass pylint 10/10 with a minimum of disable lines
- work as good, if not better than our code
- code contributed under the same [BSD 3-Clause License](https://github.com/ioccc-src/submit-tool/blob/master/LICENSE)


## IMPORTANT NOTE:

The examples below assume you have cd-ed into the top directory for the repo.


## To use:

On a macOS host with the docker app installed:

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


### To test tools outside of the docker container

To setup a test outside of the docker container, create and
activate a python environment:

```sh
    rm -rf venv __pycache__ && python3 -m venv venv
    . ./venv/bin/activate
    pip install --upgrade pip
    python3 -m pip install -r ./etc/requirements.txt
```

Then run:

```sh
    python3 -i ./bin/ioccc.py
```

While that is running, open a browser at (this works under macOS):

```
    open http://127.0.0.1:8191
```

.. or do whatever the equivalent on your to enter this URL into a browser,
(alternatively you can copy and paste it into your browser):

```
    http://127.0.0.1:8191
```

**IMPORTANT NOTE:** You may find problems running `ioccc.py` due
to various things such as the tcp port being unavailable, certain
files not being ready, or the development server having issues.
Testing outside of a docker container is **NOT SUPPORTED AND MIGHT
FAIL**!

To deactivate the above python environment:

```sh
    deactivate
    rm -rf __pycache__ venv
```


## pylint

To use pylint on the code:

```sh
    rm -rf venv __pycache__ && python3 -m venv venv
    . ./venv/bin/activate
    ./bin/pychk.sh
```

FYI: Under macOS we installed pylint via pipx:

```sh
    sudo pipx --global install pylint
```

In case you don't have pipx, we installed pipx via Homebrew on macOS:

```sh
    brew install pipx
```


## bin/ioccc_passwd.py user management

While the docker image is running, access the console and
go to the `/app` directory.

The usage message of the `./bin/ioccc_passwd.py` is as follows:

```
    usage: ioccc_passwd.py [-h] [-a USER] [-u USER] [-d USER] [-p PW] [-c]
                           [-g SECS] [-n] [-A] [-U]

    Manage IOCCC submit server password file and state file

    options:
      -h, --help         show this help message and exit
      -a, --add USER     add a new user
      -u, --update USER  update a user or add if not a user
      -d, --delete USER  delete an exist user
      -p, --password PW  specify the password (def: generate random password)
      -c, --change       force a password change at next login
      -g, --grace SECS   grace seconds to change the password (def: 259200)
      -n, --nologin      disable login (def: login not explicitly disabled)
      -A, --admin        user is an admin (def: not an admin)
      -U, --UUID         generate a new UUID username and password

    ioccc_passwd.py version: 1.3.1 2024-11-03
```

For example:


### Add a new user

```sh
    ./bin/ioccc_passwd.py -a username
```

The command will output the password in plain-text.

One may add `-p password` to set the password, otherwise a random password is generated.


### Remove an old user

```sh
    ./bin/ioccc_passwd.py -d username
```


### Add a random UUID user and require them to change their password

```sh
    ./bin/ioccc_passwd.py -U -c
```


### Set the contest open and close dates

```sh
    ./bin/ioccc_passwd.py -s '2024-05-04 03:02:01.09876+00:00' -S '2025-12-31 23:59:59.999999+00:00'
```


## Set the staring and/or ending dates of the IOCCC

The starting and ending dates of the IOCCC control when `./bin/ioccc.py` allows
for submission uploads.

While the docker image is running, access the console and
go to the `/app` directory.

The usage message of the `./bin/ioccc_date.py` is as follows:

```
    usage: ioccc_date.py [-h] [-s DateTime] [-S DateTime]

    Manage IOCCC submit server password file and state file

    options:
      -h, --help            show this help message and exit
      -s, --start DateTime  set IOCCC start date in YYYY-MM-DD
                            HH:MM:SS.micros+hh:mm format
      -S, --stop DateTime   set IOCCC stop date in YYYY-MM-DD
                            HH:MM:SS.micros+hh:mm format

    ioccc_date.py version: 1.0 2024-11-15
```

When neither `-s DateTime` nor `-S DateTime` is given, then the current
IOCCC start and end values are printed.


### Set both the start and the end dates of the IOCCC

```sh
    ./bin/ioccc_date.py -s "2024-05-25 21:27:28.901234+00:00" -S "2024-10-28 00:47:00.000000-08:00"
```



## Set slot comment

To set / change the status comment of a user's slot:

```sh
    ./bin/set_slot_status.py 12345678-1234-4321-abcd-1234567890ab 0 'new slot status'
```

The usage message of the `./bin/ioccc_date.py` is as follows:

```
    usage: set_slot_status.py [-h] username slot_num status

    Manage IOCCC submit server password file and state file

    positional arguments:
      username    IOCCC submit server username
      slot_num    slot number from 0 to 9
      status      slot status string

    options:
      -h, --help  show this help message and exit

    set_slot_status.py version: 1.0 2024-11-03
```


## Disclaimer


This code is based on code originally written by Eliot Lear (@elear) in late
2021.  The [IOCCC judges](https://www.ioccc.org/judges.html) heavily modified
Eliot's code, so any fault you find should be blamed on them 😉 (that is, the
IOCCC Judges :-) ). As such, YOU should be WARNED that this code might NOT work,
or at least might not for you.

The IOCCC plans to deploy a hosted docker container to allow IOCCC
registered contestants to submit files that have been created by the
[mkiocccentry tool](https://github.com/ioccc-src/mkiocccentry).

The [IOCCC judges](https://www.ioccc.org/judges.html) plan to work on
this code prior to the next IOCCC.
