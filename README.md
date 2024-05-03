# IOCCC submit tool

This is the mechanism to upload IOCCC entries.


## To use:

On a macOS host with the docker app, cd to the top of the repo
directory and then:

```sh
    rm -rf venv && python3 -m venv venv

    . ./venv/bin/activate

    python3 -m pip install -r requirements.txt

    docker run -p 5001:5001 testimg:latest
```

When the ru `docker` command is running, launch a browser and visit:
[submit tool](http://127.0.0.1:5001)

Login using a username and password referenced in the `iocccpasswd` file.


## iocccpasswd.py user management

While the docker image is running, access the console and
go to the `/app` directory.

The usage message of the `iocccpasswd.py` is as follows:

```
    usage: iocccpasswd.py [-h] [-a ADD [ADD ...]] [-d DELETE [DELETE ...]] [-p PWDFILE]

    manage ioccc passwds

    optional arguments:
      -h, --help            show this help message and exit
      -a ADD [ADD ...], --add ADD [ADD ...]
			    Add a user
      -d DELETE [DELETE ...], --delete DELETE [DELETE ...]
			    Delete a user
      -p PWDFILE, --pwdfile PWDFILE
			    the file to access
```


### Add a new user

```sh
    python3 ./iocccpasswd.py -a username [username ..]
```

The command will output the password in plain-text.

One may add `-p pwd.filename` to the command line to form and/or
modify a file other than `iocccpasswd`.


### Remove an old user


```sh
    python3 ./iocccpasswd.py -d username [username ..]
```

One may add `-p pwd.filename` to the command line to form and/or
modify a file other than `iocccpasswd`.


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
