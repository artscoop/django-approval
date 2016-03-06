# coding: utf-8
from django import template

register = template.Library()


@register.filter(name="approval_pending")
def is_approval_pending(value):
    if hasattr(value, 'approval'):
        if value.approval.approved is None:
            return True
    return False


@register.filter(name="approval_denied")
def is_approval_denied(value):
    if hasattr(value, 'approval'):
        if value.approval.approved is False:
            return True
    return False
