# coding: utf-8
from django import template
from django.db import models

register = template.Library()


@register.filter(name="approval_pending")
def is_approval_pending(value: models.Model) -> bool:
    """Return whether the instance is has an approval pending."""
    if hasattr(value, "approval"):
        if value.approval.approved is None:
            return True
    return False


@register.filter(name="approval_denied")
def is_approval_denied(value: models.Model) -> bool:
    """Return whether the instance edits were rejected."""
    if hasattr(value, "approval"):
        if value.approval.approved is False:
            return True
    return False
