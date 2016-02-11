#!/usr/bin/env python
# coding: utf-8
from distutils.core import setup

from setuptools import find_packages


setup(
    name='approval',
    version='0.3.20160211',
    packages=find_packages('.'),
    include_package_data=True,
    url='',
    author='Estelle Kossouho',
    author_email='artscoop93@gmail.com',
    description='Approval mechanisms for model instances in Django 1.8+',
    requires=['django', 'django-picklefield', 'unidecode', 'django-annoying'],
    classifiers=["License :: OSI Approved :: BSD License",
                 "Framework :: Django",
                 "Development Status :: 4 - Beta",
                 ]

)