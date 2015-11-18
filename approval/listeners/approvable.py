# coding: utf-8
from copy import deepcopy

from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from approval.models.approval import ApprovedModel
from approval.util.signals import pre_approval, post_approval


@receiver(pre_save)
def before_save(sender, instance, **kwargs):
    """
    Manage data in the approvable item before it is saved
    :type instance: django.db.models.Model | approval.models.ApprovedModel
    """
    if isinstance(instance, ApprovedModel):
        if instance.pk is not None:  # Sandbox updated instances only
            user = [instance.request.user] if hasattr(instance, 'request') else instance._get_authors()
            instance.approval._update_sandbox()
            instance._revert()
            instance.approval._auto_process(authors=user, update=True)

@receiver(post_save)
def after_save(sender, instance, raw, created, **kwargs):
    """
    Manage data in the approvable item after it has been saved
    """
    if isinstance(instance, ApprovedModel):
        if created:
            user = [instance.request.user] if hasattr(instance, 'request') else instance._get_authors()
            instance.approval._update_sandbox()
            instance.approval._update_source(default=True, save=True)
            instance.approval._auto_process(authors=user, update=False)
