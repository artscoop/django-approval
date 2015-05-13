# coding: utf-8
from __future__ import absolute_import
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings


class Registry(models.Model):
    """ Model to retain to be approved edits on monitored objects """
    MODERATION = ((None, _(u"Pending")), (False, _(u"Refused")), (True, _(u"Approved")))
    # Fields
    content_type = models.ForeignKey('contenttypes.ContentType', verbose_name=_(u"Content type"))
    object_id = models.IntegerField(verbose_name=_(u"Object id"))
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')
    created = models.DateTimeField(default=timezone.now, verbose_name=_(u"Creation"))
    updated = models.DateTimeField(auto_now=True, verbose_name=pgettext_lazy('registry_entry', u"Updated"))
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL)
    moderated = models.NullBooleanField(default=None, choices=MODERATION, verbose_name=pgettext_lazy('registry_entry', u"Moderated"))
    moderation_date = models.DateTimeField(null=True, verbose_name=pgettext_lazy('registry_entry', u"Moderated at"))
    moderation_info = models.TextField(blank=True, verbose_name=_(u"Reason"))
    draft = models.BooleanField(default=True, verbose_name=_(u"Draft"))

    # Metaconfiguration
    class Meta:
        verbose_name = _(u"Moderation entry")
        verbose_name_plural = _(u"Moderation registry")
        app_label = 'approval'
