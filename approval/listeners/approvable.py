# coding: utf-8
from __future__ import absolute_import
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from approval.models.approval import ApprovedModel, ApprovalModel
from approval.util.signals import pre_approval, post_approval


@receiver(pre_save)
def pre_save_approvable(sender, instance, **kwargs):
    """
    Manage data in the approvable item before it is saved
    :type instance: django.db.models.Model | approval.models.ApprovedModel
    """
    if instance.pk is not None and isinstance(instance, ApprovedModel) and not getattr(instance, '_approval_done', False):
        # Find the user making the change by finding a _request attribute in the instance
        if hasattr(instance, 'request'):
            user = instance.request.user
        else:
            user = None
        try:
            approval = instance.approval
        except:
            approval = instance._meta.get_field('approval').related_model.objects.create(source=instance)
        # Copy changed fields to the approval sandbox
        instance._copy_to_sandbox(save=True)
        # Revert the fields to their last state before the actual save
        untouched = instance._meta.model.objects.get(pk=instance.pk)
        field_names = approval.get_sandbox_fields()
        for field in untouched._meta.get_fields():
            try:
                if field.name in field_names:
                    setattr(instance, field.name, getattr(untouched, field.name))
            except TypeError:
                pass
        # Auto-approve: run basic and custom auto-approval process
        pre_approval.send(None, instance=instance, status=approval.approved)
        approval._auto_process(user=user)
        approval.auto_process(user=user)
        approval.save()


@receiver(post_save, sender=ApprovedModel)
def post_save_approvable(sender, instance, **kwargs):
    """ Manage data in the approvable item after it has been saved """
    if isinstance(instance, ApprovedModel):
        post_approval.send(None, instance=instance, status=instance.approval.approved)
