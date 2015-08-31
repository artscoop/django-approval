# coding: utf-8
from __future__ import absolute_import
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver


@receiver(pre_save)
def pre_save_approvable(sender, instance, **kwargs):
    """ Manage data in the approvable item before it is saved """
    pass  # the dutchie to the left hand side


@receiver(post_save)
def post_save_approvable(sender, instance, **kwargs):
    """ Manage data in the approvable item after it has been saved """
    pass  # the dutchie
