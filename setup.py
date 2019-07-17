#!/usr/bin/env python
# coding: utf-8
from distutils.core import setup

from setuptools import find_packages

setup(
    name='django-approval',
    version='0.36',
    packages=find_packages('.'),
    include_package_data=True,
    url='',
    author='Steve Kossouho',
    author_email='artscoop93@gmail.com',
    description='Approval mechanisms for model instances in Django',
    requires=[
        'django',
        'unidecode',
    ],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Framework :: Django",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ]
)
