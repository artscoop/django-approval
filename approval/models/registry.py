# coding: utf-8
from __future__ import absolute_import
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings
import picklefield


class RegistryManager(models.Manager):
    """ Manager for moderation registry """
    # Getter
    def get_queryset(self):
        return super(RegistryManager, self)


class Registry(models.Model):
    """ Model to retain to be approved edits on monitored objects """
    MODERATION = ((None, _(u"Pending")), (False, _(u"Refused")), (True, _(u"Approved")))
    # Fields
    uuid = models.UUIDField(verbose_name=_(u"UUID"))
    content_type = models.ForeignKey('contenttypes.ContentType', verbose_name=_(u"Content type"))
    object_id = models.IntegerField(verbose_name=_(u"Object id"))
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')
    sandbox = picklefield.PickledObjectField(verbose_name=_(u"Sandboxed data"))
    created = models.DateTimeField(default=timezone.now, verbose_name=_(u"Creation"))
    updated = models.DateTimeField(auto_now=True, verbose_name=pgettext_lazy('approval_entry', u"Updated"))
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, verbose_name=_(u"Moderated by"))
    moderated = models.NullBooleanField(default=None, choices=MODERATION, verbose_name=pgettext_lazy('approval_entry', u"Moderated"))
    moderation_date = models.DateTimeField(null=True, verbose_name=pgettext_lazy('registry_entry', u"Moderated at"))
    moderation_info = models.TextField(blank=True, verbose_name=_(u"Reason"))
    draft = models.BooleanField(default=True, verbose_name=_(u"Draft"))
    objects = RegistryManager()

    # Getter
    def is_valid(self):
        """ Is the moderation object valid ? """
        if self.content_object is not None:
            target = self.content_object
            for field in self.sandbox['fields']:
                if not hasattr(target, field):
                    return False
            return True
        return False

    def has_diff(self):
        """ Is the object different in the sandbox from the public view ? """
        if self.content_object is not None:
            checked_fields = [field for field in self.sandbox['fields'] if hasattr(self.content_object, 'field')]
            for field in checked_fields:
                if self.sandbox['data'][field] != getattr(self.content_object, field):
                    return True
            return False

    # Setter
    def update_object(self, force=True):
        """
        Update the target object with the current sandbox data
        :param force: update the object even if one or several sandboxed fields do not match the current schema
        :type force: bool
        """
        if self.content_object is not None:
            target = self.content_object
            original = dict()
            for field in self.sandbox['fields']:
                original[field] = getattr(target, field)
                setattr(target, field, self.sandbox['data'][field])
            try:
                target.clean_fields()  # will fail with ValidationError if there is a problem
                target.save()
            except ValidationError as exc:
                if force:
                    for key in exc.message_dict:
                        if hasattr(target, key):
                            setattr(target, key, original[key])
                    target.save()
                else:
                    raise

    def approve(self, request=None):
        if request is None or request.user.has_perm('approval.can_moderate_entries'):
            self.moderation_date = timezone.now()
            self.moderator = getattr(request, 'user', None)
            self.reason = pgettext_lazy('approval_entry', u"You may proceed.")

    def deny(self, request=None, reason=None):
        if request is None or request.user.has_perm('approval.can_moderate_entries'):
            self.moderator = getattr(request, 'user', None)
            self.reason = reason or pgettext_lazy('approval_entry', u"You may not pass!")


    # Metaconfiguration
    class Meta:
        verbose_name = _(u"Moderation entry")
        verbose_name_plural = _(u"Moderation registry")
        permissions = (('can_moderate_entries', u"Can moderate sandboxed entries"),)
        app_label = 'approval'
