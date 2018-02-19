all: test dist
.PHONY: all upload info dist

PACKAGE_NAME := $(shell python setup.py --name)
PACKAGE_VERSION := $(shell python setup.py --version)
PYTHON_PATH := $(shell which python)
PLATFORM := $(shell uname -s | awk '{print tolower($$0)}')
DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYTHON_VERSION := $(shell python3 -c "import sys; print('py%s%s' % sys.version_info[0:2] + ('-conda' if 'conda' in sys.version or 'Continuum' in sys.version else ''))")
PREFIX=
ifndef GIT_BRANCH
GIT_BRANCH=$(shell git branch | sed -n '/\* /s///p')
endif

info:
	@echo "INFO:	Building $(PACKAGE_NAME):$(PACKAGE_VERSION) on $(GIT_BRANCH) branch"
	@echo "INFO:	Python $(PYTHON_VERSION) from '$(PREFIX)' [$(CONDA)]"

clean:
	@find . -name "*.pyc" -delete
	@rm -rf .tox dist/* docs/build/*

test:
	@tox

uninstall:
	$(PREFIX)pip uninstall -y $(PACKAGE_NAME)

dist:
	@rm -rf dist/*
	$(PREFIX)python setup.py sdist bdist_wheel

upload: dist
	twine upload dist/*
