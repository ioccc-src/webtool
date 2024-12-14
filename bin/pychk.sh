#!/usr/bin/env bash
#
# pychk.sh - check the pylint status of python code under bin
#
# usage:
#
#   bin/pychk.sh
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


# setup variables referenced in the usage message
#
export VERSION="1.2 2024-12-13"
NAME=$(basename "$0")
export NAME
export TOPDIR="."


# usage
#
export USAGE="usage: $0 [-t appdir]

	-h		    print help message and exit

	-t appdir	app directory path (def: $TOPDIR)

Exit codes:
     0         all OK
     2         -h and help string printed or -V and version string printed
     3         command line error
     4         bash version is too old
     6         invalid topdir
 >= 10         internal error

$NAME version: $VERSION"


# parse command line
#
while getopts :ht: flag; do
  case "$flag" in
    h) echo "$USAGE" 1>&2
        exit 2
        ;;
    t) TOPDIR="$OPTARG"
        ;;
    \?) echo "$0: ERROR: invalid option: -$OPTARG" 1>&2
        echo 1>&2
        echo "$USAGE" 1>&2
        exit 3
        ;;
    :) echo "$0: ERROR: option -$OPTARG requires an argument" 1>&2
        echo 1>&2
        echo "$USAGE" 1>&2
        exit 3
        ;;
    *) echo "$0: ERROR: unexpected value from getopts: $flag" 1>&2
        echo 1>&2
        echo "$USAGE" 1>&2
        exit 3
        ;;
  esac
done


# remove the options
#
shift $(( OPTIND - 1 ));
#
if [[ $# -ne 0 ]]; then
    echo "$0: ERROR: expected 0 args, found: $#" 1>&2
    echo 1>&2
    echo "$USAGE" 1>&2
    exit 3
fi


# cd to topdir
#
if [[ -z $TOPDIR ]]; then
    echo "$0: ERROR: topdir is empty: $TOPDIR" 1>&2
    exit 6
fi
if [[ ! -e $TOPDIR ]]; then
    echo "$0: ERROR: topdir does not exist: $TOPDIR" 1>&2
    exit 6
fi
if [[ ! -d $TOPDIR ]]; then
    echo "$0: ERROR: cannot cd to a non-directory: $TOPDIR" 1>&2
    exit 6
fi
export CD_FAILED
cd "$TOPDIR" || CD_FAILED="true"
if [[ -n $CD_FAILED ]]; then
    echo "$0: ERROR: cd $TOPDIR failed" 1>&2
    exit 6
fi


# pylint iocccsubmit module files
#
for i in iocccsubmit/ioccc_common.py iocccsubmit/ioccc.py iocccsubmit/__init__.py ; do

    # announce
    #
    echo "=-=-= $TOPDIR/$i =-=-="

    # pylint file
    #
    python3 -m pylint "$i"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: python3 -m pylint $i failed, error: $status" 1>&2
	exit 1
    fi

done

# pylint critical bin files
#
for i in bin/ioccc_date.py bin/ioccc_passwd.py bin/set_slot_status.py ; do

    # announce
    #
    echo "=-=-= $TOPDIR/$i =-=-="

    # pylint file
    #
    python3 -m pylint "$i"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: python3 -m pylint $i failed, error: $status" 1>&2
	exit 1
    fi
done


# All Done!!! All Done!!! -- Jessica Noll, Age 2
#
exit 0
