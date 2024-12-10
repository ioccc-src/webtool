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
CMP= cmp
CP= cp
ID= id
INSTALL= install
MKDIR= mkdir
PYTHON= python3
RM= rm
SED= sed
SHELL= bash

######################
# target information #
######################

# V=@:  do not echo debug statements (quiet mode)
# V=@   echo debug statements (debug / verbose mode)
#
V=@:
#V=@

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
	${V} echo DEBUG =-= $@ start =-=
	${RM} -f $@ tmp.requirements.txt.tmp
	${SED} -e 's/^/    /' < etc/requirements.txt > tmp.requirements.txt.tmp
	${SED} -e 's/@@VERSION@@/${VERSION}/' \
	       -e '/^install_requires =/ {' -e 'r tmp.requirements.txt.tmp' -e '}' \
		  < setup.cfg.template > $@
	${RM} -f tmp.requirements.txt.tmp
	${V} echo DEBUG =-= $@ end =-=

venv: etc/requirements.txt setup.cfg
	${V} echo DEBUG =-= $@ start =-=
	${RM} -rf venv __pycache__
	${PYTHON} -m venv venv
	# was: pip install --upgrade ...
	source ./venv/bin/activate && \
	    ${PYTHON} -m pip install --upgrade pip && \
	    ${PYTHON} -m pip install --upgrade setuptools && \
	    ${PYTHON} -m pip install --upgrade wheel && \
	    ${PYTHON} -m pip install --upgrade build && \
	    ${PYTHON} -m pip install -r etc/requirements.txt
	${V} echo DEBUG =-= $@ end =-=

build/lib/submittool: venv src/submittool
	${V} echo DEBUG =-= $@ start =-=
	# was: python3 setup.py build
	source ./venv/bin/activate && \
	    ${PYTHON} -c 'import setuptools; setuptools.setup()' sdist
	${V} echo DEBUG =-= $@ end =-=

dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl: venv src/submittool build/lib/submittool
	${V} echo DEBUG =-= $@ start =-=
	# was: python3 setup.py bdist_wheel
	source ./venv/bin/activate && \
	    ${PYTHON} -m build --sdist --wheel
	${V} echo DEBUG =-= $@ end =-=

src/submittool: src/submittool/__init__.py src/submittool/ioccc.py src/submittool/ioccc_common.py
	${V} echo DEBUG =-= $@ start =-=
	${V} echo DEBUG =-= $@ end =-=

src/submittool/__init__.py: bin/__init__.py
	${V} echo DEBUG =-= $@ start =-=
	@${MKDIR} -p -v src/submittool
	@if ! ${CMP} -s $? $@; then \
	    ${CP} -f -v $? $@; \
	fi
	${V} echo DEBUG =-= $@ end =-=

src/submittool/ioccc.py: bin/ioccc.py
	${V} echo DEBUG =-= $@ start =-=
	@${MKDIR} -p -v src/submittool
	@if ! ${CMP} -s $? $@; then \
	    ${CP} -f -v $? $@; \
	fi
	${V} echo DEBUG =-= $@ end =-=

src/submittool/ioccc_common.py: bin/ioccc_common.py
	${V} echo DEBUG =-= $@ start =-=
	@${MKDIR} -p -v src/submittool
	@if ! ${CMP} -s $? $@; then \
	    ${CP} -f -v $? $@; \
	fi
	${V} echo DEBUG =-= $@ end =-=

#################
# utility rules #
#################

wheel: dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl
	${V} echo DEBUG =-= $@ start =-=
	${V} echo DEBUG =-= $@ end =-=

revenv:
	${V} echo DEBUG =-= $@ start =-=
	${RM} -rf venv __pycache__
	${PYTHON} -m venv venv
	# was: pip3 install --upgrade ...
	source ./venv/bin/activate && \
	    ${PYTHON} -m pip install --upgrade pip && \
	    ${PYTHON} -m pip install --upgrade setuptools && \
	    ${PYTHON} -m pip install --upgrade wheel && \
	    ${PYTHON} -m pip install --upgrade build && \
	    ${PYTHON} -m pip install -r etc/requirements.txt
	${V} echo DEBUG =-= $@ end =-=

venv_install: dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl
	${V} echo DEBUG =-= $@ start =-=
	# was: python3 setup.py install
	source ./venv/bin/activate && \
	    ${PYTHON} -m pip install .
	${V} echo DEBUG =-= $@ end =-=

###################################
# standard Makefile utility rules #
###################################

configure: setup.cfg
	${V} echo DEBUG =-= $@ start =-=
	${V} echo DEBUG =-= $@ end =-=

clean:
	${V} echo DEBUG =-= $@ start =-=
	${RM} -f tmp.requirements.txt.tmp
	${V} echo DEBUG =-= $@ end =-=

clobber: clean
	${V} echo DEBUG =-= $@ start =-=
	${RM} -rf venv __pycache__ src
	${RM} -rf dist build src/ioccc_submit_tool.egg-info
	${RM} -f setup.cfg
	${V} echo DEBUG =-= $@ end =-=

# remove active working elements including users
#
nuke: clobber
	${V} echo DEBUG =-= $@ start =-=
	${RM} -rf users
	${V} echo DEBUG =-= $@ end =-=

install: dist/ioccc_submit_tool-${VERSION}-py3-none-any.whl
	${V} echo DEBUG =-= $@ start =-=
	@if [[ $$(${ID} -u) != 0 ]]; then echo "ERROR: must be root to $@"; exit 1; fi
	# was: python3 setup.py install
	${PYTHON} -m pip install .
	@echo TBD
	${V} echo DEBUG =-= $@ end =-=
