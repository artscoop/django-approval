# coding: utf-8
from __future__ import absolute_import
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from approval.models.approval import ApprovedModel


@receiver(pre_save, sender=ApprovedModel)
def pre_save_approvable(sender, instance, **kwargs):
    """
    Manage data in the approvable item before it is saved
    :type instance: django.db.models.Model | approval.models.ApprovedModel
    """
    if instance.pk is not None:
        approval = getattr(instance, 'approval')
        fields = approval._meta.approval_fields
        # Copy changed fields to the approval sandbox
        instance._copy_to_sandbox(save=True)
        # Revert the fields to their last state
        instance = instance._meta.model.objects.get(pk=instance.pk)
        # Auto-approve: run basic and custom auto-approval process
        approval._auto_process()
        approval.auto_process()
        approval.save()


@receiver(post_save, sender=ApprovedModel)
def post_save_approvable(sender, instance, **kwargs):
    """ Manage data in the approvable item after it has been saved """
    pass  # the dutchie
