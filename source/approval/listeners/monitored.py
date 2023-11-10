import logging
from typing import Type

from django.db import models
from django.utils.translation import pgettext_lazy

from ..models.monitored import MonitoredModel
from django.db.models.signals import post_save, pre_save
from django.dispatch.dispatcher import receiver

logger = logging.getLogger("approval")


@receiver(pre_save)
def before_save(sender: Type[models.Model], instance: MonitoredModel, **kwargs):
    """
    Manage data in the approvable item before it is saved.

    For already created objects, update the sandbox with current object status,
    and then revert the changes in the object before saving. Then try automatic
    validation on the object.

    Args:
        sender: Class of the instance to process.
        instance: Instance to process.
    """
    if issubclass(sender, MonitoredModel) and not getattr(instance, "_ignore_approval", False):
        if instance.pk is not None:  # Sandbox updated instances only
            logger.debug(pgettext_lazy("approval", "Pre-save signal handled on updated {cls}").format(cls=sender))
            users = instance._get_authors()
            instance.approval._update_sandbox()
            instance._revert()
            instance.approval._auto_process_approval(authors=users, update=True)


@receiver(post_save)
def after_save(sender: Type[models.Model], instance: models.Model, **kwargs):
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
    if issubclass(sender, MonitoredModel) and not getattr(instance, "_ignore_approval", False):
        if kwargs.get("created", False):
            logger.debug(pgettext_lazy("approval", "Post-save signal handled on new {cls}").format(cls=sender))
            users = instance._get_authors()
            instance.approval._update_sandbox()
            instance.approval._update_source(default=True, save=True)
            instance.approval._auto_process_approval(authors=users, update=False)
