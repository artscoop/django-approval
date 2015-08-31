#!/usr/bin/env python
# coding: utf-8
from distutils.core import setup

from setuptools import find_packages


setup(
    name='approval',
    version='0.1.20150610',
    packages=find_packages('.'),
    include_package_data=True,
    url='',
    author='Steve Kossouho',
    author_email='steve.kossouho@gmail.com',
    description='Approval mechanisms for model instances in Django 1.8+',
    requires=['django', 'jsonfield', 'unidecode'],
    classifiers=["License :: OSI Approved :: BSD License",
                 "Framework :: Django",
                 "Development Status :: 4 - Beta",
                 ]

)
