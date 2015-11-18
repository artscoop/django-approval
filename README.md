# django-approval
Easy moderation of changes made to models. Django 1.8+ and Python 3.2+

## Installation
1. Download the application and run `python setup.py`
2. or install via pip using `pip install django-approval` 

## How to use
### Register an approval model
First, you need to create a model to track changes to your base model.

Warning : Monitored models should not be changed in a pre_save signal.
