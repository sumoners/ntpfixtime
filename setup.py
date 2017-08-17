#!/usr/bin/env python

import sys
from setuptools import setup

requires = ['six', 'ntplib', 'python-dateutil>=2.0']

setup(
    name='ntpfixtime',
    version='0.0.5',
    description='Fix your localtime to use the right ntp time',
    author='Jaison Erick',
    author_email='jaisonreis@mail.com',
    url='https://github.com/sumoners/ntpfixtime',
    packages=['ntpfixtime'],
    install_requires=requires,
    include_package_data=True,
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.3',
    ],
)
