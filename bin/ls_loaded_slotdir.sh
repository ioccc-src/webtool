#!/usr/bin/env bash
#
# ls_loaded_slotdir.sh - list slot directories with submit files
#
# We list, relative to topdir, those user/USERNAME/SLOT directories
# that have a submit.*.txz file in them.
#
# IMPORTANT: You MUST generate the secret key once and then
#	     copy/paste the value into your application or store it as an
#	     environment variable. Do NOT regenerate the secret key within
#	     the application, or you will get a new value for each instance
#	     of the application, which can cause issues when you deploy to
#	     production since each instance of the application has a
#	     different SECRET_KEY value.
#
# Copyright (c) 2025 by Landon Curt Noll.  All Rights Reserved.
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
#
# Share and enjoy! :-)


# setup
#
export VERSION="1.0.0 2025-01-17"
NAME=$(basename "$0")
export NAME
export V_FLAG=0
#
export TOPDIR="/var/ioccc"
if [[ ! -d $TOPDIR ]]; then
    # not on submit server, assume testing in .
    TOPDIR="."
fi


# usage
#
export USAGE="usage: $0 [-h] [-v level] [-V] [-t topdir]

	-h		print help message and exit
	-v level	set verbosity level (def level: 0)
	-V		print version string and exit

	-t topdir	app directory path (def: $TOPDIR)

Exit codes:
     0         all OK
     1	       some internal tool is missing or exited non-zero
     2         -h and help string printed or -V and version string printed
     3         command line error
     4	       cannot find topdir
     5	       cannot topdir/users
 >= 10         internal error

$NAME version: $VERSION"


# parse command line
#
while getopts :hv:V flag; do
  case "$flag" in
    h) echo "$USAGE" 1>&2
	exit 2
	;;
    v) V_FLAG="$OPTARG"
	;;
    V) echo "$VERSION"
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
#
# remove the options
#
shift $(( OPTIND - 1 ));
#
if [[ $V_FLAG -ge 5 ]]; then
    echo "$0: debug[5]: file argument count: $#" 1>&2
fi
if [[ $# -ge 1 ]]; then
    echo "$0: ERROR: expected 0 args, found: $#" 1>&2
    exit 3
fi


# move to the top of the tree
#
export CD_FAILED=""
cd "$TOPDIR" || CD_FAILED="true"
if [[ -n $CD_FAILED ]]; then
    echo "$0: ERROR: cd $TOPDIR failed" 1>&2
    exit 4
fi
if [[ ! -d users ]]; then
    echo "$0: ERROR: $TOPDIR/users not a directory" 1>&2
    exit 5
fi


# report slot directories with submit files under them
#
find users -mindepth 3 -maxdepth 3 -type f -name 'submit.*.txz' 2>/dev/null | sed -e 's;/submit\.[^/]*\.txz$;;' | sort -u


# All Done!!! All Done!!! -- Jessica Noll, Age 2
#
exit 0
