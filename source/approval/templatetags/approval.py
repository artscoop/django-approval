from typing import Optional

from django import template
from ..models import MonitoredModel

register = template.Library()


@register.filter(name="approval_pending")
def is_approval_pending(instance: MonitoredModel) -> Optional[bool]:
    """
    Get whether the instance has an approval pending.

    Returns:
        `True`: if the object has changes pending.
        `False`: if the object has nothing pending.
        `None`: if the object is not a `MonitoredModel` instance.
    """
    if isinstance(instance, MonitoredModel):
        if hasattr(instance, "approval"):
            if instance.approval.approved is None:
                return True
        return False
    return None


@register.filter(name="approval_denied")
def is_approval_denied(instance: MonitoredModel) -> Optional[bool]:
    """
    Get whether the instance approval was rejected.

    Returns:
        `True`: if the object has changes rejected.
        `False`: if the object is not in that case.
        `None`: if the object is not a `MonitoredModel` instance.
    """
    if isinstance(instance, MonitoredModel):
        if hasattr(instance, "approval"):
            if instance.approval.approved is False:
                return True
        return False
    return None
