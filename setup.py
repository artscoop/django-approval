#!/usr/bin/env python
# coding: utf-8
from distutils.core import setup

from setuptools import find_packages

setup(
    name='django-approval',
    version='0.10.20161218',
    packages=find_packages('.'),
    include_package_data=True,
    url='',
    author='S Kossouho',
    author_email='artscoop93@gmail.com',
    description='Approval mechanisms for model instances in Django 1.8+',
    requires=['django', 'django_picklefield', 'unidecode', 'django_annoying'],
    classifiers=["License :: OSI Approved :: MIT License",
                 "Framework :: Django",
                 "Development Status :: 4 - Beta",
                 "Programming Language :: Python :: 3"
                 ]

)
