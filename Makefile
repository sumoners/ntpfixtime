SHELL := /bin/bash

init:
	python setup.py develop
	pip install -r requirements.txt

publish:
	python setup.py sdist bdist_wheel upload
