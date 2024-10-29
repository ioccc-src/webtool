# IOCCC submit tool

This is the mechanism to upload submissions to an open IOCCC

**IMPORTANT NOTE:**

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

## ioccc_passwd.py user management

While the docker image is running, access the console and
go to the `/app` directory.

The usage message of the `ioccc_passwd.py` is as follows:

```
    usage: ioccc_passwd.py [-h] [-a USER] [-u USER] [-d USER] [-p PW] [-c] [-g SECS] [-n] [-A]
                           [-U] [-s DateTime] [-S DateTime]

    Manage IOCCC submit server password file and state file

    options:
      -h, --help            show this help message and exit
      -a, --add USER        add a new user
      -u, --update USER     update a user or add if not a user
      -d, --delete USER     delete an exist user
      -p, --password PW     specify the password (def: generate random password)
      -c, --change          force a password change at next login
      -g, --grace SECS      grace time in seconds from to change the password(def: 259200 seconds):
      -n, --nologin         disable login (def: login not explicitly disabled)
      -A, --admin           user is an admin (def: not an admin)
      -U, --UUID            generate a new UUID username and password
      -s, --start DateTime  set IOCCC start date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format
      -S, --stop DateTime   set IOCCC stop date in YYYY-MM-DD HH:MM:SS.micros+hh:mm format

    ioccc_passwd.py version: 1.2 2024-10-28
```

For example:

### Add a new user

```sh
    python3 ./ioccc_passwd.py -a username
```

The command will output the password in plain-text.

One may add `-p password` to set the password, otherwise a random password is generated.


### Remove an old user

```sh
    python3 ./ioccc_passwd.py -d username
```


### Add a random UUID user and require them to change their password

```sh
    python3 ./ioccc_passwd.py -U -c
```


### Set the contest open and close dates

```sh
    python3 -s '2024-05-04 03:02:01.09876+00:00' -S '2025-12-31 23:59:59.999999+00:00'
```


### To test tools outside of the docker container

To setup a test outside of the docker container, create and
activate a python environment:

```sh
    rm -rf venv __pycache__ && python3 -m venv venv
    . ./venv/bin/activate
    python3 -m pip install -r etc/requirements.txt
```

Then run:

```sh
    python3 -i ./ioccc.py
```

While that is running, open a browser at (this works under macOS):

```
    open http://127.0.0.1:8191
```

.. or do whatever the equivalent on your to enter this URL into a browser:

```
    http://127.0.0.1:8191
```

**IMPORTANT NOTE:** You may find problems running `ioccc.py` due
to various things such as the tcp port being unavailable, certain
files not being ready, or the development server having issues.
Testing outside of a docker container is **NOT supported and may
fail**!

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
    PYTHONPATH=$PWD/venv/lib/python3.13 pylint ./ioccc_common.py
    PYTHONPATH=$PWD/venv/lib/python3.13 pylint ./ioccc.py
    PYTHONPATH=$PWD/venv/lib/python3.13 pylint ./ioccc_passwd.py
```

FYI: Under macOS we installed pylint via pipx:

```sh
    sudo pipx --global install pylint
```

In case you don't have pipx, we installed pipx via HomeBrew on macOS:

```sh
    brew install pipx
```


## Disclaimer

This is concept code, originally written by Eliot Lear (@elear) in late 2021.
As concept code, YOU should be WARNED that this code may NOT work (for you).

The IOCCC plans to deploy a hosted docker container to allow IOCCC registered
contestants to submit files created by the mkiocccentry tool.
That IOCCC submission container will deploy something based on,
but NOT identical, to this submit-tool.


## Requirements

This code requires cryptography and uwsgi, both of which can bloat
a container.  What really bloats the container right now, however,
is a requirement for python3.9 or later (Ubuntu containers run with
earlier versions by default).
