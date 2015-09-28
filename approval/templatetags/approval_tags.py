# coding: utf-8
from django import template


register = template.Library()


@register.filter(name="is_approval_pending")
def is_approval_pending(value):
    if hasattr(value, 'approval'):
        if value.approval.approved:
            return True
    return False
