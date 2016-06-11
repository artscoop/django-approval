# coding: utf-8
""" Form mixins for approvable models """
from approval.models import ApprovedModel


class ApprovableForm():
    """ ModelForm mixin """

    def __init__(self, *args, **kwargs):
        """
        Form initializer for ApprovedModel

        The form is initialized with the instance data fetched from the sandbox
        """
        instance = kwargs.get('instance', None)
        if instance and isinstance(instance, ApprovedModel):
            instance.approval._update_source()
        super().__init__(*args, **kwargs)
