#
# The base image that the build will extend
#
FROM alpine:latest

# Docker container labels
#
LABEL VERSION="0.3 2024-05-12"
#
LABEL org.ioccc.image.name="ioccc-submit"
LABEL org.ioccc.image.description="IOCCC Submit Server"
LABEL org.ioccc.image.version="$VERSION"
LABEL org.ioccc.image.author="IOCCC Judges"
LABEL org.ioccc.image.contact="https://www.ioccc.org/judges.html"

# Create, if needed the /app tree in the image
#
RUN mkdir -p /app

# Copy files from the host and put them into the container image
#
COPY ./requirements.txt /app/requirements.txt

# Specifies the "working directory" in the image where files will
# be copied and commands will be executed.
#
WORKDIR /app

# Setup the pythin enviroment needed by this image
#
RUN apk add tzdata
RUN apk add python3 py3-cryptography py3-pip py3-werkzeug py3-flask py3-authlib
RUN apk add uwsgi uwsgi-http uwsgi-cgi uwsgi-python3
RUN python3 -m pip install --break-system-packages -r requirements.txt

# Copy everying from . into /app except for things mentioned in .dockerignore
#
COPY . /app

# Set permissions for iocccpasswd
#
RUN chmod 0660 iocccpasswd
RUN chown uwsgi:uwsgi iocccpasswd

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
