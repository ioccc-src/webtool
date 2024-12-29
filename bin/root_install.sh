#!/usr/bin/env bash
#
# root_install - perform actions that root needs setup and install
#
# usage:
#
#   sudo root_install.sh
#
# Copyright (c) 2024 by Landon Curt Noll.  All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby granted,
# provided that the above copyright, this permission notice and text
# this comment, and the disclaimer below appear in all of the following:
#
#       supporting documentation
#       source copies
#       source works derived from this source
#       binaries derived from this source or from derived source
#
# LANDON CURT NOLL DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO
# EVENT SHALL LANDON CURT NOLL BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF
# USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#
# chongo (Landon Curt Noll, http://www.isthe.com/chongo/index.html) /\oo/\


# firewall - run only with a bash that is version 5.1.8 or later
#
# The "/usr/bin/env bash" command must result in using a bash that
# is version 5.1.8 or later.
#
# We could relax this version and insist on version 4.2 or later.  Versions
# of bash between 4.2 and 5.1.7 might work.  However, to be safe, we will require
# bash version 5.1.8 or later.
#
# WHY 5.1.8 and not 4.2?  This safely is done because macOS Homebrew bash we
# often use is "version 5.2.26(1)-release" or later, and the RHEL Linux bash we
# use often use is "version 5.1.8(1)-release" or later.  These versions are what
# we initially tested.  We recommend you either upgrade bash or install a newer
# version of bash and adjust your $PATH so that "/usr/bin/env bash" finds a bash
# that is version 5.1.8 or later.
#
# NOTE: The macOS shipped, as of 2024 March 15, a version of bash is something like
#       bash "version 3.2.57(1)-release".  That macOS shipped version of bash
#       will NOT work.  For users of macOS we recommend you install Homebrew,
#       (see https://brew.sh), and then run "brew install bash" which will
#       typically install it into /opt/homebrew/bin/bash, and then arrange your $PATH
#       so that "/usr/bin/env bash" finds "/opt/homebrew/bin" (or whatever the
#       Homebrew bash is).
#
# NOTE: And while MacPorts might work, we noticed a number of subtle differences
#       with some of their ported tools to suggest you might be better off
#       with installing Homebrew (see https://brew.sh).  No disrespect is intended
#       to the MacPorts team as they do a commendable job.  Nevertheless we ran
#       into enough differences with MacPorts environments to suggest you
#       might find a better experience with this tool under Homebrew instead.
#
if [[ -z ${BASH_VERSINFO[0]} ||
         ${BASH_VERSINFO[0]} -lt 5 ||
         ${BASH_VERSINFO[0]} -eq 5 && ${BASH_VERSINFO[1]} -lt 1 ||
         ${BASH_VERSINFO[0]} -eq 5 && ${BASH_VERSINFO[1]} -eq 1 && ${BASH_VERSINFO[2]} -lt 8 ]]; then
    echo "$0: ERROR: bash version needs to be >= 5.1.8: $BASH_VERSION" 1>&2
    echo "$0: Warning: bash version >= 4.2 might work but 5.1.8 was the minimum we tested" 1>&2
    echo "$0: Notice: For macOS users: install Homebrew (see https://brew.sh), then run" \
         ""brew install bash" and then modify your \$PATH so that \"#!/usr/bin/env bash\"" \
         "finds the Homebrew installed (usually /opt/homebrew/bin/bash) version of bash" 1>&2
    exit 4
fi

# setup bash file matching
#
# We must declare arrays with -ag or -Ag, and we need loops to "export" modified variables.
# This requires a bash with a version 4.2 or later.  See the larger comment above about bash versions.
#
shopt -s nullglob       # enable expanded to nothing rather than remaining unexpanded
shopt -u failglob       # disable error message if no matches are found
shopt -u dotglob        # disable matching files starting with .
shopt -u nocaseglob     # disable strict case matching
shopt -u extglob        # enable extended globbing patterns
shopt -s globstar       # enable ** to match all files and zero or more directories and subdirectories


# setup variables
#
export VERSION="2.0.1 2024-12-20"
NAME=$(basename "$0")
export NAME
export SUBMIT_TOOL_DIR="/home/ioccc/submit-tool"


# must be root
#
MY_UID=$(id -u)
export MY_UID
if [[ $MY_UID -ne 0 ]]; then
    echo "$0: ERROR: must be root to run this code" 1>&2
    exit 1
fi


# submit-tool directory must exist
#
if [[ ! -d $SUBMIT_TOOL_DIR ]]; then
    echo "$0: ERROR: not a directory: $SUBMIT_TOOL_DIR" 1>&2
    exit 2
fi


# move to the top of the submit-tool tree
#
export CD_FAILED=""
cd "$SUBMIT_TOOL_DIR" || CD_FAILED="true"
if [[ -n $CD_FAILED ]]; then
    echo "$0: ERROR: cd $SUBMIT_TOOL_DIR failed" 1>&2
    exit 3
fi


# be sure etc exists and not saved.etc
#
if [[ ! -d etc ]]; then
    if [[ -d saved.etc ]]; then
	mv -v saved.etc etc
	status="$?"
	if [[ $status -ne 0 ]]; then
	    echo "$0: ERROR: mv -v saved.etc etc failed, error: $status" 1>&2
	    exit 4
	fi
    else
	echo "$0: ERROR: both $SUBMIT_TOOL_DIR/etc and $SUBMIT_TOOL_DIR/saved.etc are not a directory" 1>&2
	exit 5
    fi
fi
if [[ ! -d etc ]]; then
    echo "$0: ERROR: not a directory: $SUBMIT_TOOL_DIR/etc" 1>&2
    exit 6
fi
if [[ -d saved.etc ]]; then
    echo "$0: ERROR: is a directory: $SUBMIT_TOOL_DIR/saved.etc" 1>&2
    exit 7
fi


# install as root
#
make root_install
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: make root_install failed, error: $status" 1>&2
    exit 8
fi


# move etc out of the way, just to be safe
#
# We do not want etc to exist after installing it because we might forget to use
# the "-t /var/ioccc" in tools.
#
if [[ -d saved.etc ]]; then
    echo "$0: ERROR: is a directory: $SUBMIT_TOOL_DIR/saved.etc" 1>&2
    exit 9
fi
if [[ ! -d etc ]]; then
    echo "$0: ERROR: not a directory: $SUBMIT_TOOL_DIR/etc" 1>&2
    exit 10
fi
mv -v etc saved.etc
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: mv -v etc saved.etc failed, error: $status" 1>&2
    exit 11
fi
if [[ -d etc ]]; then
    echo "$0: ERROR: is a directory: $SUBMIT_TOOL_DIR/etc" 1>&2
    exit 12
fi
if [[ ! -d saved.etc ]]; then
    echo "$0: ERROR: not a directory: $SUBMIT_TOOL_DIR/saved.etc" 1>&2
    exit 13
fi


# restart apache
#
apachectl configtest
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: apachectl configtest failed, error: $status" 1>&2
    exit 14
fi
fkill -f httpd
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: fkill -f httpd failed, error: $status" 1>&2
    exit 15
fi
systemctl restart httpd
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: systemctl restart httpd failed, error: $status" 1>&2
    exit 16
fi
systemctl status httpd
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: systemctl status httpd failed, error: $status" 1>&2
    exit 17
fi
ps -fp $(pgrep -d, -x httpd)
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: ps -fp \$(pgrep -d, -x httpd) failed, error: $status" 1>&2
    exit 18
fi


# All Done!!! All Done!!! -- Jessica Noll, Age 2
#
exit 0
