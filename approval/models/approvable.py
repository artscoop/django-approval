# coding: utf-8
from __future__ import absolute_import
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from jsonfield.fields import JSONField
from django.conf import settings


class ApprovableModel(models.Model):
    """ Model mixin to enable moderation of edits to an object """
    # Constants
    MODERATION = ((None, _("Pending")), (False, _("Refused")), (True, _("Approved")))

    # Fields
    approval_sandbox = JSONField(default={}, blank=False, verbose_name=_("Data"))
    approved = models.NullBooleanField(default=None, choices=MODERATION, verbose_name=pgettext_lazy('approval_entry', "Moderated"))
    approval_moderator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, verbose_name=_("Moderated by"))
    approval_date = models.DateTimeField(null=True, verbose_name=pgettext_lazy('registry_entry', "Moderated at"))
    approval_info = models.TextField(blank=True, verbose_name=_("Reason"))
    approval_draft = models.BooleanField(default=True, verbose_name=_("Draft"))

    # Getter
    def is_sandbox_valid(self):
        """ Return whether sandbox data is valid or not """
        for field in self.approval_sandbox.get('fields', {}):
            if not hasattr(self, field):
                return False
        return True

    def has_sandbox_diff(self):
        """ Is the object different in the sandbox from the public view ? """
        checked_fields = [field for field in self.approval_sandbox.get('fields', {}) if hasattr(self, field)]
        for field in checked_fields:
            if self.approval_sandbox['fields'][field] != getattr(self, field):
                return True
        return False

    # Setter
    def update_object(self, force=True):
        """
        Update the target object with the current sandbox data
        :param force: update the object even if one or several sandboxed fields do not match the current schema
        :type force: bool
        """
        original = dict()
        for field in self.approval_sandbox.get('fields', {}):
            original[field] = getattr(self, field)
            setattr(self, field, self.approval_sandbox['fields'][field])
        try:
            self.clean_fields()  # will fail with ValidationError if there is a problem
            self.save()
        except ValidationError as exc:
            if force:
                for key in exc.message_dict:
                    if hasattr(self, key):
                        setattr(self, key, original[key])
                self.save()
            else:
                raise

    def approve(self, request=None):
        if request is None or request.user.has_perm('approval.can_moderate_entries'):
            self.approval_date = timezone.now()
            self.approval_moderator = getattr(request, 'user', None)
            self.approval_info = pgettext_lazy('approval_entry', "You may proceed.")

    def deny(self, request=None, reason=None):
        if request is None or request.user.has_perm('approval.can_moderate_entries'):
            self.approval_moderator = getattr(request, 'user', None)
            self.approval_info = reason or pgettext_lazy('approval_entry', "You may not pass!")

    # Metadata
    class Meta:
        abstract = True
        approval_fields = []
        auto_approve_staff = True
        auto_approve_empty_fields = True
