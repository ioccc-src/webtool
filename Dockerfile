#
# The base image that the build will extend
#
FROM alpine:latest

# Docker container labels
#
LABEL org.ioccc.image.name="ioccc-submit"
LABEL org.ioccc.image.description="IOCCC Submit Server"
LABEL org.ioccc.image.version="0.5.1 2024-11-02"
LABEL org.ioccc.image.author="IOCCC Judges"
LABEL org.ioccc.image.contact="https://www.ioccc.org/judges.html"

# Create, if needed the /app tree in the image
#
RUN mkdir -p /app

# Copy everying from . into /app except for things mentioned in .dockerignore
#
COPY . /app

# Set permissions for /app
#
RUN chmod 0755 /app
RUN chown root:root /app

# Specifies the "working directory" in the image where files will
# be copied and commands will be executed.
#
WORKDIR /app

# Create etc sub-directory
#
RUN mkdir -p etc
RUN chmod 0755 etc
RUN chown root:root etc

# Copy files from the host and put them into the container image
#
COPY ./etc/requirements.txt etc/requirements.txt
RUN chmod 0444 etc/requirements.txt
RUN chown root:root etc/requirements.txt

# Setup the python environment needed by this image
#
RUN apk add tzdata aspell aspell-en
RUN apk add python3 py3-cryptography py3-pip py3-werkzeug py3-flask py3-authlib
RUN apk add py3-flask-login
RUN apk add uwsgi uwsgi-http uwsgi-cgi uwsgi-python3
RUN python3 -m pip install --break-system-packages -r etc/requirements.txt

# Be sure we have /usr/share/dict/words available
#
# NOTE: You must have either /usr/share/dict/words installed
#	or have the aspell(1) command installed.
#
RUN <<EOT
    if [[ ! -d /usr/share/dict ]]; then
        mkdir -p /usr/share/dict
        chmod 0755 /usr/share/dict
        chown root:root /usr/share/dict
    fi
    if [[ ! -f /usr/share/dict/words ]]; then
        aspell dump master | tr -c "[A-Za-z'\n]" "'" > /usr/share/dict/words
        chmod 0444 /usr/share/dict/words
        chown root:root /usr/share/dict/words
    fi
EOT

# Set permissions for a number of top level files
#
RUN chmod 0444 .dockerignore .gitignore Dockerfile LICENSE README.md uwsgi.ini
RUN chown root:root .dockerignore .gitignore Dockerfile LICENSE README.md uwsgi.ini
RUN chmod 0555 ioccc.py ioccc_common.py ioccc_passwd.py
RUN chown root:root ioccc.py ioccc_common.py ioccc_passwd.py

# Set permissions for etc/init.iocccpasswd.json
#
RUN chmod 0444 etc/init.iocccpasswd.json
RUN chown root:root etc/init.iocccpasswd.json

# Clone etc/iocccpasswd.json from etc/init.iocccpasswd.json if missing or empty
#
RUN <<EOT
    if [[ ! -s etc/iocccpasswd.json ]]; then
	cp -f etc/init.iocccpasswd.json etc/iocccpasswd.json
    fi
EOT

# Set etc/iocccpasswd.json permissions
#
RUN chmod 0664 etc/iocccpasswd.json
RUN chown uwsgi:uwsgi etc/iocccpasswd.json

# Clone an empty the etc/iocccpasswd.lock if missing
#
RUN <<EOT
    if [[ ! -f etc/iocccpasswd.lock ]]; then
        touch etc/iocccpasswd.lock
    fi
EOT

# Set etc/iocccpasswd.lock permissions
#
RUN chmod 0664 etc/iocccpasswd.lock
RUN chown uwsgi:uwsgi etc/iocccpasswd.lock

# Set permissions for etc/init.state.json
#
RUN chmod 0444 etc/init.state.json
RUN chown root:root etc/init.state.json

# Create etc/state.json from etc/init.state.json if missing or empty
#
RUN <<EOT
    if [[ ! -s etc/state.json ]]; then
	cp -f etc/init.state.json etc/state.json
    fi
EOT

# Set permissions for etc/state.json
#
RUN chmod 0664 etc/state.json
RUN chown uwsgi:uwsgi etc/state.json

# Create an empty the etc/state.lock if missing
#
RUN <<EOT
    if [[ ! -f etc/state.lock ]]; then
        touch etc/state.lock
    fi
EOT

# Set etc/state.lock permissions
#
RUN chmod 0664 etc/state.lock
RUN chown uwsgi:uwsgi etc/state.lock

# Generate etc/.secret if not found or if empty
#
RUN <<EOT
    if [[ ! -s etc/.secret ]]; then
        /bin/sh ./genflaskkey
    fi
EOT

# Set permissions for etc/.secret
#
RUN chmod 0440 etc/.secret
RUN chown uwsgi:uwsgi etc/.secret

# Set permission for static
#
RUN chmod 0555 static
RUN chmod 0444 static/*
RUN chown -R root:root static

# Set permission for templates
#
RUN chmod 0555 templates
RUN chmod 0444 templates/*
RUN chown -R root:root templates

# Create the IOCCC users directory with permissions
#
RUN mkdir -p users
RUN chmod 2770 users
RUN chown -R uwsgi:uwsgi users

# Indicate the TCP port that the docker image would like to make available
#
EXPOSE 8191/tcp

# Set the default user for all subsequent instructions
#
USER uwsgi:uwsgi

# What to run as an docker executable
#
ENTRYPOINT [ "uwsgi" ]

# Default args given to the ENTRYPOINT
#
CMD [ "--http-socket", ":8191", \
      "--plugin", "python", \
      "--uid", "uwsgi", \
      "--gid", "uwsgi", \
      "uwsgi.ini" ]
