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
MKDIR= mkdir
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

TARGETS= dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl

######################################
# all - default rule - must be first #
######################################

all: ${TARGETS}

#################################################
# .PHONY list of rules that do not create files #
#################################################

.PHONY: all configure clean clobber nuke install \
	revenv wheel venv_install

###############
# build rules #
###############

setup.cfg: setup.cfg.template etc/requirements.txt
	${RM} -f $@ tmp.requirements.txt.tmp
	${SED} -e 's/^/    /' < etc/requirements.txt > tmp.requirements.txt.tmp
	${SED} -e 's/@@VERSION@@/${VERSION}/' \
	       -e '/^install_requires =/ {' -e 'r tmp.requirements.txt.tmp' -e '}' \
		  < setup.cfg.template > $@
	${RM} -f tmp.requirements.txt.tmp

venv: etc/requirements.txt setup.cfg
	${RM} -rf venv __pycache__
	${PYTHON} -m venv venv
	source ./venv/bin/activate && \
	    ${PIP} install --upgrade pip && \
	    ${PIP} install --upgrade setuptools && \
	    ${PIP} install --upgrade wheel && \
	    ${PYTHON} -m pip install -r etc/requirements.txt

build/lib/submittool: venv \
	build/lib/submittool/__init__.py \
	build/lib/submittool/ioccc.py \
	build/lib/submittool/ioccc_common.py

build/lib/submittool/__init__.py: venv src/submittool/__init__.py \
	setup.py setup.cfg pyproject.toml src/submittool
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py build

build/lib/submittool/ioccc.py: venv src/submittool/ioccc.py \
	setup.py setup.cfg pyproject.toml src/submittool
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py build

build/lib/submittool/ioccc_common.py: venv src/submittool/ioccc_common.py \
	setup.py setup.cfg pyproject.toml src/submittool
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py build

dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl: build/lib/submittool
	source ./venv/bin/activate && \
	    ${PIP} install --upgrade pip && \
	    ${PIP} install --upgrade setuptools && \
	    ${PIP} install --upgrade wheel && \
	    ${PYTHON} setup.py bdist_wheel

src/submittool: src/submittool/__init__.py src/submittool/ioccc.py src/submittool/ioccc_common.py

src/submittool/__init__.py: bin/__init__.py
	@${MKDIR} -p -v src/submittool
	${CP} -f $? $@

src/submittool/ioccc.py: bin/ioccc.py
	@${MKDIR} -p -v src/submittool
	${CP} -f $? $@

src/submittool/ioccc_common.py: bin/ioccc_common.py
	@${MKDIR} -p -v src/submittool
	${CP} -f $? $@

#################
# utility rules #
#################

wheel: dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl

revenv:
	${RM} -rf venv __pycache__
	${PYTHON} -m venv venv
	source ./venv/bin/activate && \
	    ${PIP} install --upgrade pip && \
	    ${PIP} install --upgrade setuptools && \
	    ${PIP} install --upgrade wheel && \
	    ${PYTHON} -m pip install -r etc/requirements.txt

venv_install: dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl
	source ./venv/bin/activate && \
	    ${PYTHON} setup.py install

###################################
# standard Makefile utility rules #
###################################

configure: setup.cfg

clean:
	${RM} -f tmp.requirements.txt.tmp

clobber: clean
	${RM} -rf venv __pycache__ src
	${RM} -rf dist build src/ioccc_submit_tool.egg-info
	${RM} -f setup.cfg

# remove active working elements including users
#
nuke: clobber
	${RM} -rf users

install: all
	@echo TBD
