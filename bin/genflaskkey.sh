#!/usr/bin/env bash
#
# genflaskkey.sh - generate the Flask secret key
#
# The secret does not have to be super string.  It just needs to be long
# enough to not be easily guessable.  We want at least 48 characters in the file.
#
# IMPORTANT: You MUST generate the secret key once and then
#	     copy/paste the value into your application or store it as an
#	     environment variable. Do NOT regenerate the secret key within
#	     the application, or you will get a new value for each instance
#	     of the application, which can cause issues when you deploy to
#	     production since each instance of the application has a
#	     different SECRET_KEY value.
#
# Copyright (c) 2024-2025 by Landon Curt Noll.  All Rights Reserved.
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
export VERSION="2.0.1 2025-01-17"
NAME=$(basename "$0")
export NAME
export V_FLAG=0
#
OPENSSL_TOOL=$(type -P openssl)
PWGEN_TOOL=$(type -P pwgen)
UUIDGEN_TOOL=$(type -P uuidgen)
BASE64_TOOL=$(type -P base64)
export PWGEN_TOOL OPENSSL_TOOL UUIDGEN_TOOL BASE64_TOOL
export GEN_TYPE=""
export FORCE_WRITE=""
export TOPDIR="/var/ioccc"
if [[ ! -d $TOPDIR ]]; then
    # not on submit server, assume testing in .
    TOPDIR="."
fi
export SECRET_FILE="$TOPDIR/etc/.secret"


# usage
#
export USAGE="usage: $0 [-h] [-v level] [-V] [-t topdir] [-F] [-T type] [outfile]

	-h		print help message and exit
	-v level	set verbosity level (def level: 0)
	-V		print version string and exit

	-t topdir	app directory path (def: $TOPDIR)

	-F		force outfile to be written (def: do not write if it exists)
	-T type		type of generator (def: search for a tool in the following order)

			openssl - use openssl tool: (found at: $PWGEN_TOOL)
			pwgen - use pwgen tool: (found at: $PWGEN_TOOL)
			uuidgen - use uuidgen tool: (found at: $UUIDGEN_TOOL)
			base64 - use bash RANDOM AND base64 tool: (found at: $BASE64_TOOL)
			bash - use bash RANDOM

	[outfile]	write secret to outfile (def: $SECRET_FILE)

Exit codes:
     0         all OK
     1	       some internal tool is missing or exited non-zero
     2         -h and help string printed or -V and version string printed
     3         command line error
 >= 10         internal error

$NAME version: $VERSION"


# parse command line
#
while getopts :hv:Vt:FT: flag; do
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
    F) FORCE_WRITE="true"
	;;
    T) case "$OPTARG" in
	openssl) GEN_TYPE="$OPTARG" ;;
	pwgen) GEN_TYPE="$OPTARG" ;;
	uuidgen) GEN_TYPE="$OPTARG" ;;
	base64) GEN_TYPE="$OPTARG" ;;
	bash) GEN_TYPE="$OPTARG" ;;
	*) echo "$0: ERROR: unknown -t type: $OPTARG" 1>&2
	   echo 1>&2
	   echo "$USAGE" 1>&2
	   exit 3
	   ;;
       esac
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
#
# verify arg count and parse args
#
case "$#" in
0) ;;
1) SECRET_FILE="$1" ;;
*) echo "$0: ERROR: expected 0 or 1 args, found: $#" 1>&2
   echo "$USAGE" 1>&2
   exit 3
   ;;
esac


# unless -F, exit 0 if secret file exists as a non-empty file
#
if [[ -z $FORCE_WRITE && -s $SECRET_FILE ]]; then
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: nothing to do: -F given and secret file already exists: $SECRET_FILE" 1>&2
    fi
    if [[ $V_FLAG -ge 1 ]]; then
	SECRET_FILE_LS=$(ls -l "$SECRET_FILE")
	echo "$0: debug[1]: $SECRET_FILE_LS" 1>&2
    fi
    if [[ $V_FLAG -ge 3 ]]; then
	SECRET_FILE_CONTENTS=$(< "$SECRET_FILE")
	echo "$0: debug[3]: secret: $SECRET_FILE_CONTENTS" 1>&2
    fi
    exit 0
fi


# verify we have the tool we need
#
case "$GEN_TYPE" in
openssl)
    if [[ -z $OPENSSL_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not not found along \$PATH" 1>&2
	exit 1
    fi
    if [[ ! -x $OPENSSL_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not executable: $OPENSSL_TOOL" 1>&2
	exit 1
    fi
    ;;
pwgen)
    if [[ -z $PWGEN_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not not found along \$PATH" 1>&2
	exit 1
    fi
    if [[ ! -x $PWGEN_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not executable: $PWGEN_TOOL" 1>&2
	exit 1
    fi
    ;;
uuidgen)
    if [[ -z $UUIDGEN_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not not found along \$PATH" 1>&2
	exit 1
    fi
    if [[ ! -x $UUIDGEN_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not executable: $UUIDGEN_TOOL" 1>&2
	exit 1
    fi
    ;;
base64)
    if [[ -z $BASE64_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not not found along \$PATH" 1>&2
	exit 1
    fi
    if [[ ! -x $BASE64_TOOL ]]; then
	echo "$0: ERROR: $GEN_TYPE tool not executable: $BASE64_TOOL" 1>&2
	exit 1
    fi
    ;;
bash) # of course bash is executable, we are executing it in this script!  :-)
    ;;
*) # no set tool, search for a tool to use
    if [[ -n $OPENSSL_TOOL && -x $OPENSSL_TOOL ]]; then
	GEN_TYPE="openssl"
    elif [[ -n $PWGEN_TOOL && -x $PWGEN_TOOL ]]; then
	GEN_TYPE="pwgen"
    elif [[ -n $UUIDGEN_TOOL && -x $UUIDGEN_TOOL ]]; then
	GEN_TYPE="uuidgen"
    elif [[ -n $BASE64_TOOL && -x $BASE64_TOOL ]]; then
	GEN_TYPE="base64"
    else
	GEN_TYPE="bash"
    fi
    ;;
esac


# remove any existing secret
#
rm -f "$SECRET_FILE"
if [[ -e $SECRET_FILE ]]; then
    echo "$0: ERROR: failed remove $SECRET_FILE" 1>&1
    exit 1
fi


# Generate a secret using one of several ways.
#
case "$GEN_TYPE" in
openssl)

    # case: use openssl
    #
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: about to run: $OPENSSL_TOOL rand -base64 48" 1>&2
    fi
    "$OPENSSL_TOOL" rand -base64 48
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: $OPENSSL_TOOL rand -base64 48 failed, error code: $status" 1>&1
	exit 1
    fi
    ;;

pwgen)

    # case: use pwgen
    #
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: about to run: $PWGEN_TOOL 32 1" 1>&2
    fi
    "$PWGEN_TOOL" 48 1
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: $PWGEN_TOOL 48 1 failed, error code: $status" 1>&1
	exit 1
    fi
    ;;

uuidgen)

    # case: use uuidgen
    #
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: about to run: $UUIDGEN_TOOL" 1>&2
    fi
    VALUE1="$($UUIDGEN_TOOL)"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: $UUIDGEN_TOOL for VALUE1 failed, error code: $status" 1>&1
	exit 1
    fi
    VALUE2="$($UUIDGEN_TOOL)"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: $UUIDGEN_TOOL for VALU2 failed, error code: $status" 1>&1
	exit 1
    fi
    echo "$VALUE1.$VALUE2" | tr -d -
    ;;

base64)

    # case: use bash RANDOM and base64
    #
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: about to run: echo ... | $BASE64_TOOL" 1>&2
    fi
    echo "${RANDOM}.${RANDOM}+${RANDOM}-${RANDOM},${RANDOM}_${RANDOM}%${RANDOM}@${RANDOM}" | "$BASE64_TOOL"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: $BASE64_TOOL failed, error code: $status" 1>&1
	exit 1
    fi
    ;;

bash)

    # case: use bash RANDOM
    #
    if [[ $V_FLAG -ge 1 ]]; then
	echo "$0: debug[1]: about to run: echo ..." 1>&2
    fi
    echo "${RANDOM}.${RANDOM}+${RANDOM}-${RANDOM},${RANDOM}_${RANDOM}%${RANDOM}@${RANDOM}"
    ;;

*)

    echo "$0: ERROR: invalid GEN_TYPE: $GEN_TYPE" 1>&2
    exit 10
    ;;

esac > "$SECRET_FILE"


# firewall - secret must be non-empty
#
if [[ ! -s $SECRET_FILE ]]; then
    echo "$0: ERROR: failed to create $SECRET_FILE" 1>&1
    exit 5
fi


# make the secret read only
#
chmod 0440 "$SECRET_FILE"
status="$?"
if [[ $status -ne 0 ]]; then
    echo "$0: ERROR: chmod 0400 $SECRET_FILE failed, error code: $status" 1>&1
    exit 4
fi
if [[ $V_FLAG -ge 1 ]]; then
    SECRET_FILE_LS=$(ls -l "$SECRET_FILE")
    echo "$0: debug[1]: $SECRET_FILE_LS" 1>&2
fi
if [[ $V_FLAG -ge 3 ]]; then
    SECRET_FILE_CONTENTS=$(< "$SECRET_FILE")
    echo "$0: debug[3]: secret: $SECRET_FILE_CONTENTS" 1>&2
fi


# All Done!!! All Done!!! -- Jessica Noll, Age 2
#
exit 0
