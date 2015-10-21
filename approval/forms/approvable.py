# coding: utf-8
""" Form mixins for approvable models """
from approval.models.approval import ApprovedModel


class ApprovableForm():
    """ ModelForm mixin """

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if instance and isinstance(instance, ApprovedModel):
            instance._copy_from_sandbox()
        super().__init__(*args, **kwargs)
