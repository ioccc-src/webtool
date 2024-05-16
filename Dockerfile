#
# The base image that the build will extend
#
FROM alpine:latest

# Docker container labels
#
LABEL VERSION="0.3.4 2024-05-15"
#
LABEL org.ioccc.image.name="ioccc-submit"
LABEL org.ioccc.image.description="IOCCC Submit Server"
LABEL org.ioccc.image.version="$VERSION"
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
RUN chmod 0555 /app
RUN chown root:root /app

# Specifies the "working directory" in the image where files will
# be copied and commands will be executed.
#
WORKDIR /app

# Create etc sub-directory
#
RUN mkdir -p etc
RUN chmod 0555 etc
RUN chown root:root etc

# Copy files from the host and put them into the container image
#
COPY ./etc/requirements.txt etc/requirements.txt

# Setup the pythin enviroment needed by this image
#
RUN apk add tzdata
RUN apk add python3 py3-cryptography py3-pip py3-werkzeug py3-flask py3-authlib
RUN apk add uwsgi uwsgi-http uwsgi-cgi uwsgi-python3
RUN python3 -m pip install --break-system-packages -r etc/requirements.txt

# Set permissions in top level files
#
RUN chmod 0444 .dockerignore .gitignore Dockerfile LICENSE README.md ioccc.py iocccpasswd.py uwsgi.ini
RUN chown root:root .dockerignore .gitignore Dockerfile LICENSE README.md ioccc.py iocccpasswd.py uwsgi.ini

# Set permissions for etc/admins
#
RUN chmod 0444 etc/admins
RUN chown root:root etc/admins

# Set permissions for etc/iocccpasswd
#
RUN chmod 0660 etc/iocccpasswd
RUN chown uwsgi:uwsgi etc/iocccpasswd

# Set permissions for etc/requirements.txt
#
RUN chmod 0440 etc/requirements.txt
RUN chown root:root etc/requirements.txt

# Set permission for static
#
RUN chmod 0555 static
RUN chmod 0444 static/*

# Set permission for templates
#
RUN chmod 0555 templates
RUN chmod 0444 templates/*

# Create the IOCCC users directory with permissions
#
RUN mkdir -p users
RUN chmod 2770 users
RUN chown -R uwsgi:uwsgi users

# Indicates a port the image would like to expose
#
EXPOSE 8191/tcp

# Sets the default user for all subsequent instructions
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
