# Initial IOTCC Upload page

This is the mechanism to upload IOTCC entries.

## Installation

% git clone {this distribution} /usr/lib/ioccc
% pip install flask flask_httpauth hashlib werkzeug

Create /var/lib/ioccc and make sure that it is writeable to you web
server.  Generate a password file with iocccpasswd.py.  Be sure to
save the passwords.

Enable werkzeug.  Apache has appropriate machinery.  Be sure to
install and enable mod-wsgi.

Add these lines in an appropriate apache config:

   WSGIScriptAlias /ioccc /usr/lib/ioccc/ioccc.py
   WSGIPassAuthorization On

## Using

Files are uploaded to the users' directories in /var/lib/ioccc.  They
can update their entries at any time prior to you disabling the page.


