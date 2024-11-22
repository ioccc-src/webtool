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


# pylint critical bin files
#
for i in bin/ioccc_common.py bin/ioccc.py bin/ioccc_date.py bin/ioccc_passwd.py bin/set_slot_status.py; do

    # announce
    #
    echo "=-=-= $i =-=-="

    # pylint file
    #
    pylint --source-roots bin "$i"
    status="$?"
    if [[ $status -ne 0 ]]; then
	echo "$0: ERROR: pylint $$ failed, error: $status" 1>&2
	exit 1
    fi
done


# All Done!!! All Done!!! -- Jessica Noll, Age 2
#
exit 0
