#!/usr/bin/env make
#
# submit-tool - IOCCC submit server tool
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
#
# Share and enjoy! :-)

#############
# utilities #
#############

CHMOD= chmod
CP= cp
INSTALL= install
PIP = pip3
PYTHON= python3
RM= rm
SED= sed
SHELL= bash

######################
# target information #
######################

# ioccc-submit-tool package version
#
VERSION= 0.1.7

DESTDIR= /usr/local/bin

TARGETS= venv-install

######################################
# all - default rule - must be first #
######################################

all: ${TARGETS}

setup.cfg: template.setup.cfg
	${RM} -f $@
	${SED} -e 's/@@VERSION@@/${VERSION}/' < $? > $@

venv: requirements.txt setup.cfg revenv

revenv: requirements.txt setup.cfg
	${RM} -rf venv __pycache__
	${PYTHON} -m venv venv
	source ./venv/bin/activate && \
	    ${PIP} install --upgrade pip && \
	    ${PIP} install setuptools && \
	    ${PYTHON} -m pip install -r requirements.txt

build/lib/submittool: venv setup.py setup.cfg pyproject.toml
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py build

bdist_wheel: build/lib/submittool
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py bdist_wheel

venv-install: bdist_wheel
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py install

#################################################
# .PHONY list of rules that do not create files #
#################################################

.PHONY: all configure clean clobber install \
	revenv bdist_wheel venv-install

###################################
# standard Makefile utility rules #
###################################

configure: setup.cfg

clean:
	@echo rule to clean or empty rule if nothing is built

clobber: clean
	${RM} -rf venv __pycache__
	${RM} -rf dist build src/ioccc_submit_tool.egg-info
	${RM} -f setup.cfg

install: all
	@echo TBD
