#!/usr/bin/env python3
#
# ioccc.wsgi - IOCCC submit tool server
#
# pylint: disable=unused-import

"""
ioccc.wsgi - IOCCC submit tool server application

This code is executed by the Apache wsgi module via configuration
in the /etc/httpd/conf/wsgi.conf file on the submit server.
"""


# import the ioccc server and common utility code
#
from iocccsubmit import application, setup_logger


# ioccc.wsgi version
#
# NOTE: Use string of the form: "x.y[.z] YYYY-MM-DD"
#
VERSION_IOCCC_WSGI = "2.2.0 2024-12-22"


# setup logging as syslog at INFO level
#
setup_logger("syslog", "info")


# application = create_app(__name__)
