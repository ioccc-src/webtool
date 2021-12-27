# Initial IOCCC Upload page

This is the mechanism to upload IOCCC entries.

## Disclaimer

This is concept code, originally written by Eliot Lear (@elear) in late 2021.
As concept code, YOU should be WARNED that this code may NOT work (for you).

The IOCCC plans to deploy a hosted docker container to allow IOCCC registered
contestants to submit files created by the mkiocccentry tool.
That IOCCC submission container will deploy something based on,
but NOT identical, to this submit-tool.

## Installation

% git clone {this distribution} /usr/lib/ioccc
% pip install flask flask_httpauth hashlib werkzeug

Create /var/lib/ioccc and make sure that it is writable to you web
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
