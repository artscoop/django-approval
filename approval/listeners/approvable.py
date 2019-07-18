# coding: utf-8

from approval.models.approval import ApprovedModel
from django.db.models.signals import post_save, pre_save
from django.dispatch.dispatcher import receiver


@receiver(pre_save)
def before_save(sender, instance, **kwargs):
    """
    Manage data in the approvable item before it is saved

    For already created objects, update the sandbox with current object status,
    and then revert the changes in the object before saving. Then try automatic
    validation on the object.

    :param sender: Generally, the sender is the class of the object to process.
    :param kwargs: Extra arguments (ignored)
    :type instance: django.db.models.Model | approval.models.ApprovedModel
    """
    if isinstance(instance, ApprovedModel) and not getattr(
        instance, "_ignore_approval", False
    ):
        if instance.pk is not None:  # Sandbox updated instances only
            users = (
                [instance.request.user]
                if hasattr(instance, "request")
                else instance._get_authors()
            )
            instance.approval._update_sandbox()
            instance._revert()
            instance.approval._auto_process_approval(authors=users, update=True)


@receiver(post_save)
def after_save(sender, instance, raw, created, **kwargs):
    """
    Manage data in the approvable item after it has been saved for the first time

    For new objects, copy the status to the sandbox, and then
    set some fields in the original object to reflect approval defaults
    (generally, it means setting content to invisible or unpublished)

    :param sender: Generally, the class of the saved object
    :param instance: Instance of the saved object
    :param raw: --
    :param created: Is the instance new in the database ?
    """
    if isinstance(instance, ApprovedModel) and not getattr(
        instance, "_ignore_approval", False
    ):
        if created:
            users = (
                [instance.request.user]
                if hasattr(instance, "request")
                else instance._get_authors()
            )
            instance.approval._update_sandbox()
            instance.approval._update_source(default=True, save=True)
            instance.approval._auto_process_approval(authors=[users], update=False)
